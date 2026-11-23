"""Local playback, playlist persistence and desktop metadata regression checks."""

import json
import io
import os
from pathlib import Path
import shutil
import sys
import subprocess
import tempfile
import time
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import wave

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'config/hypr/scripts/terminal'))
from music_player_engine import Player, Track, normalize, read_library
from music_player_mpris import MediaService, PLAYER
from music_player import TerminalPlayer, clip, run_modes


@unittest.skipUnless(shutil.which('mpv') and shutil.which('ffprobe'), 'mpv and ffprobe are required')
class LocalPlayerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='test-serena-player-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.tracks = []
        for name in ['First', 'Có Hẹn', 'Last']:
            path = self.root / (name + '.wav')
            with wave.open(str(path), 'wb') as stream:
                stream.setparams((1, 2, 8000, 0, 'NONE', 'not compressed'))
                stream.writeframes(bytes(8000 * 2 * 12))
            self.tracks.append(Track(path, name, 'Artist', 'Album', 12))
        self.player = Player(self.tracks, self.root / 'session.json', 'null')
        self.addCleanup(self.player.close)

    def wait_for(self, condition):
        deadline = time.monotonic() + 4
        while time.monotonic() < deadline:
            if condition():
                return
            time.sleep(.03)
        self.fail('Playback condition was not reached')

    def test_pause_resume_seek_and_stop_with_real_audio_engine(self):
        p = self.player
        p.play(str(self.tracks[0].path))
        self.wait_for(lambda: not p.loading and p.position > .05)
        p.pause()
        self.wait_for(lambda: p.status == 'Paused')
        time.sleep(.15)
        before = p.position
        time.sleep(.15)
        self.assertAlmostEqual(p.position, before, delta=.05)
        p.seek(5, absolute=True)
        self.wait_for(lambda: abs(p.position - 5) < .15)
        p.resume()
        self.wait_for(lambda: p.status == 'Playing' and p.position > 5.05)
        p.stop()
        self.assertEqual(p.status, 'Stopped')

    def test_shuffle_keeps_current_audio_and_restore_keeps_selection(self):
        p = self.player
        current = str(self.tracks[1].path)
        p.play(current)
        p.position = 4
        p.shuffle()
        self.assertEqual(p.current, current)
        self.assertEqual(p.order[0], current)
        self.assertCountEqual(p.order, [str(t.path) for t in self.tracks])
        self.assertEqual(p.position, 4)
        p.shuffle(False)
        self.assertEqual(p.order, [str(t.path) for t in self.tracks])
        self.assertEqual(p.current, current)

    def test_remove_only_affects_playlist_and_rescan_restores_files(self):
        p = self.player
        removed = str(self.tracks[1].path)
        p.remove(removed)
        self.assertNotIn(removed, p.order)
        self.assertTrue(Path(removed).is_file())
        p.close()
        state = json.loads((self.root / 'session.json').read_text())
        self.assertIn(removed, state['excluded'])
        restored = Player(self.tracks, self.root / 'session.json', 'null')
        self.addCleanup(restored.close)
        self.assertNotIn(removed, restored.order)
        restored.reload(self.tracks)
        self.assertIn(removed, restored.order)

    def test_eof_obeys_repeat_mode(self):
        p = self.player
        last = str(self.tracks[-1].path)
        p.play(last)
        p.loop = 'None'
        p.handle_event({'event': 'end-file', 'reason': 'eof'})
        self.assertEqual(p.status, 'Stopped')
        p.loop = 'All'
        p.play(last)
        p.handle_event({'event': 'end-file', 'reason': 'eof'})
        self.assertEqual(p.current, str(self.tracks[0].path))
        p.loop = 'Track'
        p.play(last)
        p.handle_event({'event': 'end-file', 'reason': 'eof'})
        self.assertEqual(p.current, last)
        self.assertEqual(p.status, 'Playing')

    def test_media_metadata_identifies_the_exact_local_file(self):
        p = self.player
        p.play(str(self.tracks[1].path))
        media = MediaService.__new__(MediaService)
        media.player = p
        metadata = media.properties(PLAYER)['Metadata'].unpack()
        self.assertEqual(metadata['xesam:title'], 'Có Hẹn')
        self.assertEqual(metadata['xesam:artist'], ['Artist'])
        self.assertEqual(metadata['xesam:url'], self.tracks[1].path.as_uri())
        self.assertEqual(metadata['mpris:trackid'], self.tracks[1].track_id)
        self.assertEqual(metadata['mpris:length'], 12_000_000)

    def test_close_releases_process_and_socket_directory(self):
        process = self.player.process
        socket_dir = Path(self.player.directory.name)
        self.player.close()
        self.assertIsNotNone(process.poll())
        self.assertFalse(socket_dir.exists())
        self.player.close()

    def test_saved_playlist_order_and_metadata_cache(self):
        (self.root / 'Liked Songs.m3u8').write_text('#EXTM3U\nLast.wav\nFirst.wav\n../outside.wav\n')
        cache = self.root / 'cache.json'
        tracks = read_library(self.root, cache)
        self.assertEqual([t.path.name for t in tracks], ['Last.wav', 'First.wav', 'Có Hẹn.wav'])
        with patch('music_player_engine.subprocess.run', side_effect=AssertionError('Cache should avoid probing')):
            self.assertEqual(read_library(self.root, cache), tracks)


class TextTests(unittest.TestCase):
    def test_accent_insensitive_search_and_terminal_cell_clipping(self):
        self.assertEqual(normalize('Đường Tôi Chở Em Về'), 'duong toi cho em ve')
        self.assertEqual(clip('A界B', 3), 'A界')
        self.assertNotIn('\x1b', clip('Song\x1b', 20))

    def test_both_launchers_allow_titles_to_follow_the_active_music_mode(self):
        scripts = Path(__file__).resolve().parents[1] / 'config/hypr/scripts/terminal'
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            kitty = directory / 'kitty'
            kitty.write_text('#!/usr/bin/python3\nimport json,sys\nprint(json.dumps(sys.argv[1:]))\n')
            kitty.chmod(0o755)
            pgrep = directory / 'pgrep'
            pgrep.write_text('#!/bin/sh\nexit 1\n')
            pgrep.chmod(0o755)
            env = dict(os.environ, PATH=str(directory) + os.pathsep + os.defpath)
            for name in ['open_music_player.sh', 'toggle_music.sh']:
                with self.subTest(launcher=name):
                    result = subprocess.run(['bash', str(scripts / name)], env=env,
                                            stdin=subprocess.DEVNULL, capture_output=True,
                                            text=True, check=True, timeout=5)
                    args = json.loads(result.stdout)
                    self.assertEqual(args[:2], ['--class', 'music-vis'])
                    self.assertNotIn('--title', args)
                    self.assertNotIn('-T', args)


class ModeTests(unittest.TestCase):
    def test_repeated_switches_reuse_playback_and_keep_library_selection(self):
        player = SimpleNamespace(exit_requested=False, position=37, current='same-file')
        visits = []
        browser = SimpleNamespace(mode_requested=None, selected='chosen-file')

        def library(screen):
            visits.append('library')
            self.assertEqual(player.current, 'same-file')
            self.assertEqual(browser.selected, 'chosen-file')
            browser.mode_requested = 'visualizer'
            if visits.count('library') == 3:
                player.exit_requested = True

        def visualizer(shared):
            self.assertIs(shared, player)
            visits.append('visualizer')
            shared.position += 1
            return 'library'

        browser.run = library
        with patch('music_player.curses.wrapper', side_effect=lambda fn: fn(None)), \
             patch('music_player.sys.stdout', io.StringIO()) as output:
            run_modes(player, browser, visualizer, 'library')
            self.assertEqual(output.getvalue().count('\x1b[?2026l'), 3)
        self.assertEqual(visits, ['library', 'visualizer', 'library', 'visualizer', 'library'])
        self.assertEqual(player.position, 39)

    def test_tab_leaves_library_even_while_searching_without_quitting_audio(self):
        player = SimpleNamespace(current='song', order=['song'], exit_requested=False)
        browser = TerminalPlayer(player, Path('/tmp'), Path('/tmp/not-used.json'))
        browser.typing = True
        browser.query = 'song'
        with patch('music_player.subprocess.Popen') as spawn:
            browser.key('\t', None)
            spawn.assert_not_called()
        self.assertEqual(browser.mode_requested, 'visualizer')
        self.assertFalse(player.exit_requested)
        self.assertEqual(browser.query, 'song')

    def visualizer(self, player):
        import music
        with patch.object(music.threading.Thread, 'start'), \
             patch.object(music, 'HyprlandVisibilityWatcher'):
            return music.LyricsApp(local_player=player)

    def test_visualizer_tab_keeps_audio_and_q_quits_both_views(self):
        player = SimpleNamespace(exit_requested=False)
        app = self.visualizer(player)
        app.handle_key('\t')
        self.assertEqual(app.mode_requested, 'library')
        self.assertFalse(app.running)
        self.assertFalse(player.exit_requested)
        app.handle_key('q')
        self.assertTrue(player.exit_requested)

    def test_local_clock_accepts_seeks_without_external_player_polling(self):
        import music
        player = SimpleNamespace(lock=threading.RLock(),
            track=Track(Path('/tmp/song.m4a'), 'Song', 'Singer', 'Album', 120),
            position=70, duration=120, status='Playing', exit_requested=False)
        app = self.visualizer(player)
        with patch.object(music.subprocess, 'check_output', side_effect=AssertionError('No external polling')), \
             patch.object(app, 'load_lyrics_async'), \
             patch.object(music, 'load_sync_offset', return_value=0):
            app.update_mpris()
            self.assertEqual(app.position, 70)
            player.position = 5
            app.update_mpris()
            self.assertEqual(app.position, 5)
            self.assertIsNone(app.pending_rewind)

    def test_visualizer_resets_synchronized_output_at_terminal_boundaries(self):
        import music
        with patch.object(music.sys, 'stdin') as stdin, \
             patch.object(music.sys, 'stdout', io.StringIO()) as output:
            stdin.isatty.return_value = False
            try:
                music.init_terminal()
                self.assertTrue(output.getvalue().startswith('\x1b[?2026l'))
                output.seek(0)
                output.truncate()
                music.cleanup_terminal()
                self.assertTrue(output.getvalue().startswith('\x1b[?2026l'))
            finally:
                music.terminal_active = False


if __name__ == '__main__':
    unittest.main()
