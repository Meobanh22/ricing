#!/usr/bin/env python3
# music_player_engine.py — Local mpv playback, playlist state and MPRIS controls.

import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import random
import socket
import subprocess
import tempfile
import threading
import time
import unicodedata
from dataclasses import dataclass

AUDIO_SUFFIXES = {'.m4a', '.mp3', '.flac', '.ogg', '.opus', '.wav', '.aac', '.mka'}


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def normalize(text):
    return ''.join(c for c in unicodedata.normalize('NFKD', text.casefold().replace('đ', 'd'))
                   if not unicodedata.combining(c))


@dataclass(frozen=True)
class Track:
    path: Path
    title: str
    artist: str = ''
    album: str = ''
    duration: float = 0

    @property
    def track_id(self):
        return '/org/serena/track/' + hashlib.sha1(os.fsencode(self.path)).hexdigest()


def read_library(folder, cache_path):
    folder = folder.resolve()
    try:
        cached = json.loads(cache_path.read_text())
    except (OSError, ValueError):
        cached = {}
    paths = sorted((p.resolve() for p in folder.rglob('*')
                    if p.is_file() and p.suffix.lower() in AUDIO_SUFFIXES
                    and p.resolve().is_relative_to(folder)), key=lambda p: normalize(p.name))
    paths = list(dict.fromkeys(paths))
    fresh = {}

    def read(path):
        stat = path.stat()
        signature = [stat.st_mtime_ns, stat.st_size]
        entry = cached.get(str(path), {})
        if entry.get('signature') != signature:
            try:
                result = subprocess.run(
                    ['ffprobe', '-v', 'error', '-show_entries',
                     'format=duration:format_tags=title,artist,album', '-of', 'json', str(path)],
                    capture_output=True, text=True, timeout=8, check=True)
                data = json.loads(result.stdout)['format']
                tags = {k.lower(): v for k, v in data.get('tags', {}).items()}
                entry = {'signature': signature, 'title': tags.get('title') or path.stem,
                         'artist': tags.get('artist', ''), 'album': tags.get('album', ''),
                         'duration': float(data.get('duration', 0))}
            except (OSError, ValueError, KeyError, subprocess.SubprocessError):
                entry = {'signature': signature, 'title': path.stem, 'artist': '',
                         'album': '', 'duration': 0}
        return path, entry

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for path, entry in pool.map(read, paths):
            fresh[str(path)] = entry
    atomic_json(cache_path, fresh)
    ordered = []
    playlist = folder / 'Liked Songs.m3u8'
    if playlist.is_file():
        for line in playlist.read_text(encoding='utf-8-sig').splitlines():
            if line and not line.startswith('#'):
                path = (folder / line).resolve()
                if str(path) in fresh and path not in ordered:
                    ordered.append(path)
    ordered.extend(p for p in paths if p not in ordered)
    return [Track(p, **{k: v for k, v in fresh[str(p)].items() if k != 'signature'})
            for p in ordered]


class Player:
    def __init__(self, tracks, state_path, audio_output=None):
        self.lock = threading.RLock()
        self.state_path = state_path
        self.library = {str(t.path): t for t in tracks}
        self.original_order = list(self.library)
        try:
            saved = json.loads(state_path.read_text())
        except (OSError, ValueError):
            saved = {}
        self.excluded = set(saved.get('excluded', [])) & self.library.keys()
        self.order = list(dict.fromkeys(p for p in saved.get('order', []) if p in self.library and p not in self.excluded))
        self.order.extend(p for p in self.original_order if p not in self.order and p not in self.excluded)
        self.current = saved.get('current') if saved.get('current') in self.order else None
        self.position = max(0, float(saved.get('position', 0))) if self.current else 0
        self.duration = self.track.duration if self.track else 0
        self.volume = max(0, min(100, float(saved.get('volume', 100))))
        self.loop = saved.get('loop', 'All')
        if self.loop not in ('None', 'All', 'Track'):
            self.loop = 'All'
        self.shuffled = bool(saved.get('shuffled', False))
        self.status = 'Stopped'
        self.notice = ''
        self.exit_requested = False
        self.listeners = []
        self.closed = False
        self.pending_seek = 0
        self.loading = False
        self.wanted_pause = False
        self.failed_paths = set()
        self.directory = tempfile.TemporaryDirectory(prefix='serena-player-')
        self.socket_path = str(Path(self.directory.name) / 'mpv.sock')
        self.send_lock = threading.Lock()
        self.connection = None
        self.process = None
        try:
            args = ['mpv', '--no-config', '--no-terminal', '--input-terminal=no',
                    '--idle=yes', '--vid=no', '--audio-display=no', '--ytdl=no',
                    '--keep-open=no', '--ao=' + (audio_output or 'pipewire,pulse'),
                    '--audio-client-name=Serena Player', '--volume=' + str(self.volume),
                    '--input-ipc-server=' + self.socket_path]
            self.process = subprocess.Popen(args, stdin=subprocess.DEVNULL,
                                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                if self.process.poll() is not None:
                    raise RuntimeError('mpv could not start')
                try:
                    self.connection = socket.socket(socket.AF_UNIX)
                    self.connection.connect(self.socket_path)
                    break
                except OSError:
                    self.connection.close()
                    self.connection = None
                    time.sleep(.04)
            if self.connection is None:
                raise RuntimeError('mpv did not create its control socket')
            self.reader = threading.Thread(target=self.read_events, daemon=True)
            self.reader.start()
            for index, name in enumerate(('time-pos', 'duration', 'pause', 'volume', 'idle-active')):
                self.command('observe_property', index, name)
        except Exception:
            self.close(save=False)
            raise

    @property
    def track(self):
        return self.library.get(self.current)

    def notify(self, seeked=False):
        for listener in tuple(self.listeners):
            listener(seeked)

    def command(self, *args):
        if self.closed or self.connection is None:
            return
        try:
            with self.send_lock:
                self.connection.sendall((json.dumps({'command': args}) + '\n').encode())
        except OSError:
            if not self.closed:
                self.notice = 'Playback connection lost'
                self.status = 'Stopped'

    def read_events(self):
        try:
            with self.connection.makefile('rb') as stream:
                for line in stream:
                    try:
                        self.handle_event(json.loads(line))
                    except (ValueError, KeyError, TypeError):
                        continue
        except OSError:
            pass
        finally:
            if not self.closed:
                self.status = 'Stopped'
                self.notice = 'Playback engine stopped'
                self.notify()

    def handle_event(self, event):
        with self.lock:
            kind = event.get('event')
            if kind == 'property-change':
                name, value = event.get('name'), event.get('data')
                if name == 'time-pos':
                    if value is not None:
                        self.position = max(0, float(value))
                    return
                if name == 'duration':
                    if value is not None:
                        self.duration = max(0, float(value))
                elif name == 'pause':
                    if self.status != 'Stopped':
                        self.status = 'Paused' if value else 'Playing'
                elif name == 'volume' and value is not None:
                    self.volume = float(value)
                elif name == 'idle-active' and value and not self.loading:
                    self.status = 'Stopped'
                else:
                    return
                self.notify()
            elif kind == 'file-loaded':
                self.loading = False
                self.status = 'Paused' if self.wanted_pause else 'Playing'
                if self.pending_seek:
                    self.command('seek', self.pending_seek, 'absolute+exact')
                    self.pending_seek = 0
                self.failed_paths.clear()
                self.notify()
            elif kind == 'end-file':
                if event.get('reason') == 'eof':
                    if self.loop == 'Track' and self.track:
                        self.play(self.current)
                    else:
                        self.next(automatic=True)
                elif event.get('reason') == 'error':
                    self.failed_paths.add(self.current)
                    self.notice = 'Cannot play: ' + (self.track.title if self.track else 'file')
                    remaining = [p for p in self.order if p not in self.failed_paths]
                    if remaining:
                        self.play(remaining[0])
                    else:
                        self.stop()
            elif kind == 'playback-restart':
                self.notify(seeked=True)

    def play(self, path, start=0):
        with self.lock:
            path = str(path)
            if path not in self.order or not Path(path).is_file():
                self.notice = 'This file is no longer available. Press R to rescan.'
                return
            self.current = path
            self.position = max(0, start)
            self.duration = self.track.duration
            self.pending_seek = self.position
            self.loading = True
            self.wanted_pause = False
            self.status = 'Playing'
            self.command('set_property', 'pause', False)
            self.command('loadfile', path, 'replace')
            self.notify()

    def pause(self):
        with self.lock:
            if self.status == 'Playing':
                self.wanted_pause = True
                self.status = 'Paused'
                self.command('set_property', 'pause', True)
                self.notify()

    def resume(self):
        with self.lock:
            if self.status == 'Stopped':
                if self.order:
                    self.play(self.current or self.order[0], self.position)
            else:
                self.wanted_pause = False
                self.status = 'Playing'
                self.command('set_property', 'pause', False)
                self.notify()

    def toggle(self):
        self.pause() if self.status == 'Playing' else self.resume()

    def stop(self):
        with self.lock:
            self.status = 'Stopped'
            self.loading = False
            self.command('stop')
            self.notify()

    def next(self, automatic=False):
        with self.lock:
            if not self.order:
                return self.stop()
            index = self.order.index(self.current) + 1 if self.current in self.order else 0
            if index >= len(self.order):
                if self.loop != 'All':
                    return self.stop()
                index = 0
            self.play(self.order[index])

    def previous(self):
        with self.lock:
            if self.position > 3 and self.current in self.order:
                return self.seek(0, absolute=True)
            index = self.order.index(self.current) - 1 if self.current in self.order else 0
            if index < 0:
                index = len(self.order) - 1 if self.loop == 'All' else 0
            if self.order:
                self.play(self.order[index])

    def seek(self, seconds, absolute=False):
        with self.lock:
            if self.status == 'Stopped':
                return
            target = seconds if absolute else self.position + seconds
            self.position = max(0, min(self.duration, target)) if self.duration else max(0, target)
            self.command('seek', self.position, 'absolute+exact')
            self.notify(seeked=True)

    def set_volume(self, volume):
        with self.lock:
            self.volume = max(0, min(100, volume))
            self.command('set_property', 'volume', self.volume)
            self.notify()

    def shuffle(self, enabled=True):
        with self.lock:
            if enabled:
                remaining = [p for p in self.order if p != self.current]
                random.shuffle(remaining)
                self.order = ([self.current] if self.current in self.order else []) + remaining
            else:
                self.order = [p for p in self.original_order if p not in self.excluded]
            self.shuffled = enabled
            self.notify()

    def remove(self, path):
        with self.lock:
            if path not in self.order:
                return
            index = self.order.index(path)
            self.order.remove(path)
            self.excluded.add(path)
            if path == self.current:
                if self.order:
                    self.play(self.order[min(index, len(self.order) - 1)])
                else:
                    self.stop()
                    self.current = None
            self.notice = 'Removed from playlist. File kept; R restores all songs.'
            self.notify()

    def reload(self, tracks):
        with self.lock:
            self.library = {str(t.path): t for t in tracks}
            self.original_order = list(self.library)
            self.order = list(self.original_order)
            self.excluded.clear()
            self.shuffled = False
            if self.current not in self.library:
                self.stop()
                self.current = None
            self.notify()

    def close(self, save=True):
        if self.closed:
            return
        if save:
            with self.lock:
                atomic_json(self.state_path, {'order': self.order, 'excluded': list(self.excluded),
                            'current': self.current, 'position': self.position, 'volume': self.volume,
                            'loop': self.loop, 'shuffled': self.shuffled})
        self.closed = True
        if self.connection is not None:
            try:
                with self.send_lock:
                    self.connection.sendall(b'{"command":["quit"]}\n')
                self.connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self.connection.close()
        if self.process is not None:
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.terminate()
                try:
                    self.process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait()
        self.directory.cleanup()
