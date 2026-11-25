#!/usr/bin/env python3
# music_player.py — Terminal library and playback controls for local music.

import argparse
import curses
import fcntl
import locale
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import threading
import unicodedata

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'system'))
from music_player_engine import Player, normalize, read_library
from music_player_mpris import MediaService
from palette import PALETTE


def clock(seconds):
    seconds = max(0, int(seconds))
    return f'{seconds // 60}:{seconds % 60:02}'


def clip(text, width):
    out = []
    used = 0
    for char in str(text):
        if unicodedata.category(char) in ('Cc', 'Cs'):
            continue
        size = 0 if unicodedata.combining(char) else (2 if unicodedata.east_asian_width(char) in ('W', 'F') else 1)
        if used + size > width:
            break
        used += size
        out.append(char)
    return ''.join(out)


class TerminalPlayer:
    def __init__(self, player, folder, cache_path):
        self.player = player
        self.folder = folder
        self.cache_path = cache_path
        self.query = ''
        self.typing = False
        self.selected = player.current or (player.order[0] if player.order else None)
        self.top = 0
        self.help = False
        self.refreshing = False
        self.mode_requested = None

    def colors(self):
        curses.start_color()
        roles = ['dark_wine', 'cream_white', 'soft_pink', 'muted_pink', 'vivid_red', 'light_wine']
        slots = {}
        for i, role in enumerate(roles):
            rgb = tuple(int(PALETTE[role][n:n + 2], 16) for n in (1, 3, 5))
            index = 16 + i
            if curses.can_change_color() and curses.COLORS > index:
                curses.init_color(index, *(round(v / 255 * 1000) for v in rgb))
            elif curses.COLORS >= 256:
                index = 16 + 36 * round(rgb[0] / 51) + 6 * round(rgb[1] / 51) + round(rgb[2] / 51)
            else:
                index = {'dark_wine': curses.COLOR_BLACK, 'cream_white': curses.COLOR_WHITE,
                         'soft_pink': curses.COLOR_WHITE, 'muted_pink': curses.COLOR_WHITE,
                         'vivid_red': curses.COLOR_RED, 'light_wine': curses.COLOR_BLACK}[role]
            slots[role] = index
        for i, (fg, bg) in enumerate([('cream_white', 'dark_wine'), ('soft_pink', 'dark_wine'),
                                    ('muted_pink', 'dark_wine'), ('vivid_red', 'dark_wine'),
                                    ('cream_white', 'light_wine')], 1):
            curses.init_pair(i, slots[fg], slots[bg])

    def visible(self):
        query = normalize(self.query)
        with self.player.lock:
            return [p for p in self.player.order if not query or query in normalize(
                    self.player.library[p].title + ' ' + self.player.library[p].artist)]

    def move(self, amount):
        tracks = self.visible()
        if tracks:
            i = tracks.index(self.selected) if self.selected in tracks else 0
            self.selected = tracks[max(0, min(len(tracks) - 1, i + amount))]

    def refresh(self):
        if self.refreshing:
            return
        self.refreshing = True
        self.player.notice = 'Reading local library...'
        def work():
            try:
                self.player.reload(read_library(self.folder, self.cache_path))
                self.player.notice = 'Library refreshed; removed playlist entries restored.'
            except Exception as error:
                self.player.notice = 'Cannot refresh library: ' + str(error)
            finally:
                self.refreshing = False
        threading.Thread(target=work, daemon=True).start()

    def draw(self, screen):
        rows, cols = screen.getmaxyx()
        screen.erase()
        def put(y, x, text, pair=1, bold=False):
            if 0 <= y < rows and 0 <= x < cols:
                try:
                    screen.addstr(y, x, clip(text, max(0, cols - x - 1)),
                                  curses.color_pair(pair) | (curses.A_BOLD if bold else 0))
                except curses.error:
                    pass
        if rows < 12 or cols < 48:
            put(0, 1, 'Serena Music', 4, True)
            put(2, 1, 'Resize this window to browse music.', 2)
            put(4, 1, 'Space Play/Pause  |  q Quit', 3)
            screen.refresh()
            return
        p = self.player
        with p.lock:
            track = p.track
            position, duration = p.position, p.duration
            order = list(p.order)
            current = p.current
            put(0, 2, 'Serena Music', 4, True)
            mode = f'{len(order)} songs  |  {"Shuffled" if p.shuffled else "In order"}  |  Repeat {p.loop}  |  Vol {p.volume:.0f}%'
            if cols < 100:
                mode = f'{len(order)} songs · {"Shuffle" if p.shuffled else "Ordered"} · Repeat {p.loop} · {p.volume:.0f}%'
            if cols < 68:
                mode = f'{len(order)} songs · {p.volume:.0f}%'
            put(0, max(18, cols - len(mode) - 2), mode, 3)
            put(1, 2, track.title if track else 'Choose a song and press Enter', 1, True)
            put(2, 2, f'{p.status}  ·  {track.artist}' if track else str(self.folder), 2)
            bar_width = max(5, cols - 22)
            fill = round(bar_width * min(1, position / duration)) if duration else 0
            put(3, 2, clock(position), 2)
            put(3, 10, '━' * fill, 4)
            put(3, 10 + fill, '─' * (bar_width - fill), 3)
            put(3, cols - 9, clock(duration), 2)
            put(4, 1, '─' * (cols - 2), 3)
            artist_x = int(cols * .64) if cols >= 90 else None
            put(5, 2, '    TITLE', 3)
            if artist_x:
                put(5, artist_x, 'ARTIST', 3)
            visible = self.visible()
            if self.selected not in visible:
                self.selected = visible[0] if visible else None
            index = visible.index(self.selected) if self.selected in visible else 0
            count = rows - 10
            self.top = min(self.top, index)
            self.top = max(0, max(self.top, index - count + 1))
            for offset, path in enumerate(visible[self.top:self.top + count]):
                y = 6 + offset
                item = p.library[path]
                selected = path == self.selected
                pair = 5 if selected else 1
                if selected:
                    put(y, 1, ' ' * (cols - 2), pair)
                number = order.index(path) + 1
                put(y, 2, ('▶' if path == current else ' ') + f'{number:3} ', pair, path == current)
                width = artist_x - 10 if artist_x else cols - 18
                title = item.title.split(' - From ', 1)[0]
                shown = clip(title, width)
                if shown != title:
                    shown = clip(title, width - 1) + '…'
                put(y, 8, shown, pair, path == current)
                if artist_x:
                    put(y, artist_x, clip(item.artist, cols - artist_x - 10), pair if selected else 2)
                put(y, cols - 8, clock(item.duration), pair if selected else 3)
            if not visible:
                put(7, 3, 'No matches. Press Esc to clear search.' if self.query else 'No audio files found. Press R to rescan.', 2)
            if self.typing or self.query:
                put(rows - 4, 2, '/ ' + self.query + ('▏' if self.typing else '') + f'   ({len(visible)} matches)', 2)
            elif p.notice:
                put(rows - 4, 2, p.notice, 2)
            put(rows - 3, 1, '─' * (cols - 2), 3)
            put(rows - 2, 2, '↑/↓ Select  Enter Play  Space Pause  ←/→ Seek  n/p Next/Prev  / Search', 2)
            put(rows - 1, 2, 'Tab Lyrics  s Shuffle  u In order  r Repeat  +/- Volume  ? Help  q Quit', 3)
        if self.help:
            lines = ['KEYBOARD', 'Enter       Play selected song from the start',
                     'Space       Pause / resume', 'Left/Right  Seek backward / forward 5 seconds',
                     'n / p       Next / previous song', 's           Shuffle again; keep current song playing',
                     'u           Restore original playlist order', 'r           Repeat all / one / off',
                     '/           Search titles and artists (accents optional)',
                     'Esc         Clear search / close help', '+ / -       Volume up / down',
                     'Delete      Remove from playlist; keep the audio file',
                     'R           Rescan files and restore removed entries',
                     'Tab / v     Switch to lyrics and spectrum in this window',
                     'Lyrics mode: +/- Sync, 0 Reset, d Focus, h/l Seek',
                     'q           Quit music and stop playback']
            for y in range(1, rows - 3):
                put(y, 1, ' ' * (cols - 2))
            for y, text in enumerate(lines[:rows - 5], 2):
                put(y, 3, text, 4 if y == 2 else 2, y == 2)
        screen.refresh()

    def key(self, key, screen):
        p = self.player
        if key == '\t':
            self.mode_requested = 'visualizer'
            self.typing = False
        elif key == '\x1b':
            self.query = ''; self.typing = False; self.help = False
        elif key == curses.KEY_RESIZE:
            pass
        elif self.help:
            self.help = False
        elif key == curses.KEY_MOUSE:
            try:
                _, x, y, _, buttons = curses.getmouse()
            except curses.error:
                return
            if buttons & curses.BUTTON4_PRESSED:
                self.move(-3)
            elif buttons & getattr(curses, 'BUTTON5_PRESSED', 0):
                self.move(3)
            elif buttons & (curses.BUTTON1_CLICKED | curses.BUTTON1_DOUBLE_CLICKED):
                tracks = self.visible()
                index = self.top + y - 6
                if 6 <= y < screen.getmaxyx()[0] - 4 and 0 <= index < len(tracks):
                    self.selected = tracks[index]
                    if buttons & curses.BUTTON1_DOUBLE_CLICKED:
                        p.play(self.selected)
                elif y == 3:
                    p.seek(max(0, min(1, (x - 10) / max(5, screen.getmaxyx()[1] - 22))) * p.duration, absolute=True)
        elif key in (curses.KEY_UP, curses.KEY_DOWN, curses.KEY_PPAGE, curses.KEY_NPAGE):
            self.move({curses.KEY_UP: -1, curses.KEY_DOWN: 1,
                       curses.KEY_PPAGE: -10, curses.KEY_NPAGE: 10}[key])
        elif key in ('\n', '\r', curses.KEY_ENTER):
            self.typing = False
            if self.selected:
                p.play(self.selected)
        elif self.typing:
            if key in (curses.KEY_BACKSPACE, '\x7f', '\b'):
                self.query = self.query[:-1]
            elif isinstance(key, str) and key.isprintable():
                self.query += key
        elif key == '/':
            self.typing = True; self.query = ''
        elif key == 'q':
            p.exit_requested = True
        elif key == ' ':
            p.toggle()
        elif key in ('j', 'k'):
            self.move(1 if key == 'j' else -1)
        elif key in (curses.KEY_HOME, curses.KEY_END):
            tracks = self.visible()
            if tracks:
                self.selected = tracks[0 if key == curses.KEY_HOME else -1]
        elif key in (curses.KEY_LEFT, curses.KEY_RIGHT):
            p.seek(-5 if key == curses.KEY_LEFT else 5)
        elif key in ('n', 'p'):
            (p.next if key == 'n' else p.previous)()
            self.selected = p.current
        elif key in ('s', 'u'):
            p.shuffle(key == 's')
        elif key == 'r':
            with p.lock:
                p.loop = {'All': 'Track', 'Track': 'None', 'None': 'All'}[p.loop]
            p.notify()
        elif key in ('+', '=', '-'):
            p.set_volume(p.volume + (-5 if key == '-' else 5))
        elif key == curses.KEY_DC and self.selected:
            p.remove(self.selected)
        elif key == 'R':
            self.refresh()
        elif key == '?':
            self.help = True
        elif key == 'v':
            self.mode_requested = 'visualizer'

    def run(self, screen):
        self.mode_requested = None
        sys.stdout.write('\x1b[?2026l\x1b]2;Serena Music Library\x1b\\')
        sys.stdout.flush()
        curses.curs_set(0)
        self.colors()
        screen.bkgd(' ', curses.color_pair(1))
        screen.keypad(True)
        screen.timeout(100)
        curses.set_escdelay(25)
        curses.mouseinterval(150)
        curses.mousemask(curses.BUTTON1_CLICKED | curses.BUTTON1_DOUBLE_CLICKED |
                         curses.BUTTON4_PRESSED | getattr(curses, 'BUTTON5_PRESSED', 0))
        last_scene = None
        while not self.player.exit_requested and self.mode_requested is None:
            with self.player.lock:
                p = self.player
                scene = (screen.getmaxyx(), self.selected, self.query, self.typing, self.help,
                         tuple(p.order), p.current, p.status, round(p.position, 1),
                         p.duration, p.volume, p.loop, p.shuffled, p.notice)
            if scene != last_scene:
                self.draw(screen)
                last_scene = scene
            try:
                key = screen.get_wch()
            except curses.error:
                continue
            self.key(key, screen)


def run_modes(player, browser, visualizer, initial_mode):
    """Keep one playback engine alive while terminal views come and go."""
    mode = initial_mode
    while not player.exit_requested:
        if mode == 'library':
            curses.wrapper(browser.run)
            # Ncurses may leave a synchronized refresh pending on Kitty.
            # Complete it before the graphics renderer takes over this terminal.
            sys.stdout.write('\x1b[?2026l')
            sys.stdout.flush()
            mode = browser.mode_requested
        elif mode == 'visualizer':
            mode = visualizer(player)
        else:
            break


def main(visualizer=None):
    parser = argparse.ArgumentParser(description='Browse and play your local music library.')
    parser.add_argument('--library', type=Path, default=Path.home() / 'music')
    parser.add_argument('--headless', action='store_true', help='Run playback and desktop controls without the browser')
    parser.add_argument('--mode', choices=['library', 'visualizer'], default='library',
                        help='Initial view; Tab switches views without stopping playback')
    parser.add_argument('--play', type=Path, help='Start a file in the library')
    parser.add_argument('--state-dir', type=Path, help='Use a separate session directory')
    parser.add_argument('--audio-output', choices=['null'], help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not shutil.which('mpv') or not shutil.which('ffprobe'):
        parser.error('mpv and ffprobe are required')
    if not args.library.is_dir():
        parser.error('Music folder does not exist: ' + str(args.library))
    locale.setlocale(locale.LC_ALL, '')
    runtime = Path(os.environ.get('XDG_RUNTIME_DIR', tempfile_runtime()))
    runtime.mkdir(parents=True, exist_ok=True)
    lock_file = (runtime / 'serena-player.lock').open('a')
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        from music_player_mpris import raise_window
        raise_window()
        print('Serena Player is already running.')
        return
    state_dir = args.state_dir or Path(os.environ.get('XDG_STATE_HOME', Path.home() / '.local/state')) / 'serena-player'
    cache_path = state_dir / 'library-cache.json'
    player = None
    media = None
    try:
        tracks = read_library(args.library, cache_path)
        player = Player(tracks, state_dir / 'session.json', args.audio_output)
        media = MediaService(player)
        signal.signal(signal.SIGTERM, lambda *unused: setattr(player, 'exit_requested', True))
        if args.play:
            path = args.play.resolve()
            if str(path) not in player.order:
                parser.error('--play must point to a file in this library')
            player.play(path)
        if args.headless:
            while not player.exit_requested:
                threading.Event().wait(.2)
        else:
            if visualizer is None:
                from music import run_visualizer
                visualizer = run_visualizer
            run_modes(player, TerminalPlayer(player, args.library, cache_path), visualizer, args.mode)
    except KeyboardInterrupt:
        pass
    except (OSError, RuntimeError, curses.error) as error:
        print('Serena Player: ' + str(error), file=sys.stderr)
        return 1
    finally:
        if media:
            media.close()
        if player:
            player.close()
        lock_file.close()


def tempfile_runtime():
    return '/tmp/serena-player-' + str(os.getuid())


if __name__ == '__main__':
    sys.exit(main() or 0)
