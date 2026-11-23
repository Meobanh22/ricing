"""Regression checks for the terminal music spectrum."""

import importlib.util
import base64
import io
import json
import re
import tempfile
import unittest
import urllib.parse
from pathlib import Path
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "serena_music", ROOT / "config/hypr/scripts/terminal/music.py"
)
music = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(music)


def plain(text):
    return music.ANSI_STYLE.sub("", text)


class SpectrumTests(unittest.TestCase):
    def make_app(self):
        with patch.object(music.threading.Thread, "start"):
            app = music.LyricsApp()
        app.lyrics_canvas = None
        return app

    def test_graphics_frames_clear_stale_text_only_on_mode_or_size_changes(self):
        app = self.make_app()
        app.spectrum_canvas = Mock()
        app.spectrum_canvas.render.return_value = ''
        output = io.StringIO()
        with patch.object(music.shutil, 'get_terminal_size', return_value=(80, 24)) as size, \
             patch.object(music.sys, 'stdout', output):
            app.render()
            self.assertIn('\x1b[K', output.getvalue())
            output.seek(0)
            output.truncate()
            app.render()
            self.assertNotIn('\x1b[K', output.getvalue())
            size.return_value = (100, 30)
            output.seek(0)
            output.truncate()
            app.render()
            self.assertIn('\x1b[K', output.getvalue())
            app.spectrum_canvas = None
            output.seek(0)
            output.truncate()
            app.render()
            self.assertIn('\x1b[K', output.getvalue())

    def test_spectrum_fills_width_after_resize(self):
        app = self.make_app()
        app.bars = [100.0] * music.NUM_BARS
        for width in (1, 2, 3, 23, 40, 59, 60, 80, 86, 120, 192, 384, 385, 510, 513, 40):
            with self.subTest(width=width):
                with patch.object(music, "cava_raw_targets", [100.0] * music.NUM_BARS):
                    lines = app.render_spectrum(width, 9)
                self.assertEqual(len(lines), 9)
                self.assertTrue(all(len(plain(line)) == width for line in lines))
                bottom = plain(lines[-1])
                self.assertEqual(set(map(len, re.findall("█+", bottom))), {min(2, width)})
                left = len(bottom) - len(bottom.lstrip())
                right = len(bottom) - len(bottom.rstrip())
                self.assertLessEqual(abs(left - right), 1)
                self.assertLessEqual(left + right, 2)

    def test_lowest_eighth_of_bar_is_visible(self):
        app = self.make_app()
        app.bars = [12.5] * music.NUM_BARS
        with patch.object(music.time, "monotonic", return_value=app.last_frame_time), \
             patch.object(music, "SPECTRUM_GAIN", 1.0):
            line = plain(app.render_spectrum(2, 1)[0])
        self.assertEqual(line, "▁▁")

    def test_focus_mode_clears_kitty_once_and_restores_normal_rendering(self):
        from types import SimpleNamespace
        app = self.make_app()
        app.spectrum_canvas = None
        app.focus_mode = SimpleNamespace(active=True, ready=True, update=lambda *args: None)
        outputs = []
        for _ in range(2):
            output = io.StringIO()
            with patch.object(music.sys, 'stdout', output), patch.object(music.shutil, 'get_terminal_size', return_value=(80, 24)):
                app.render()
            outputs.append(output.getvalue())
        self.assertIn('\x1b[K', outputs[0])
        self.assertEqual(outputs[1], '')
        app.focus_mode.active = False
        with patch.object(music.sys, 'stdout', io.StringIO()):
            app.render()
        self.assertIsNone(app.focus_frame_size)

    def test_lyrics_do_not_change_spectrum_height_or_bar_levels(self):
        for size in ((80, 24), (192, 55), (24, 12), (40, 16), (12, 5), (1, 1)):
            for graphical in (False, True) if music.LyricsCanvas is not None else (False,):
                with self.subTest(size=size, graphical=graphical):
                    app = self.make_app()
                    app.scaled_lyrics = graphical
                    app.lyrics_canvas = music.LyricsCanvas(music.PALETTE) if graphical else None
                    frames = []
                    for state in ('missing', 'synced', 'plain', 'missing'):
                        app.is_synced = state == 'synced'
                        app.synced_lyrics = [(0, 'Current line'), (10, 'Next line')] if app.is_synced else []
                        app.plain_lyrics = ['Current line', 'Next line'] if state == 'plain' else []
                        app.lyrics_found = state in ('synced', 'plain')
                        app.length = 20
                        app.bars = [50.0] * music.NUM_BARS
                        with patch.object(music.shutil, 'get_terminal_size', return_value=size), \
                             patch.object(music.sys, 'stdout', io.StringIO()), \
                             patch.object(music, 'cava_raw_targets', [50.0] * music.NUM_BARS), \
                             patch.object(music.time, 'monotonic', return_value=app.last_frame_time), \
                             patch.object(app, 'render_spectrum', wraps=app.render_spectrum) as spectrum:
                            app.render()
                            height = spectrum.call_args.args[1]
                            # Compare the actual waveform for the same audio in every state.
                            frames.append(app.render_spectrum(size[0], height))
                    self.assertTrue(all(frame == frames[0] for frame in frames[1:]))

    def test_silence_has_no_artificial_floor(self):
        app = self.make_app()
        with patch.object(music, "cava_raw_targets", [0.0] * music.NUM_BARS):
            lines = app.render_spectrum(80, 10)
        self.assertTrue(all(not plain(line).strip() for line in lines))

    def test_smoothing_is_independent_of_frame_rate(self):
        slow, fast = self.make_app(), self.make_app()
        slow.last_frame_time = fast.last_frame_time = 0
        with patch.object(music, "cava_raw_targets", [100.0] * music.NUM_BARS):
            with patch.object(music.time, "monotonic", return_value=0.1):
                slow.render_spectrum(80, 10)
            for step in range(1, 11):
                with patch.object(music.time, "monotonic", return_value=step / 100):
                    fast.render_spectrum(80, 10)
        for left, right in zip(slow.bars, fast.bars):
            self.assertAlmostEqual(left, right)

    def test_gradient_uses_source_token_stops(self):
        tokens = json.loads((ROOT / "config/theme/tokens.json").read_text())
        stops = re.findall(r"(#[0-9a-fA-F]{6})\s+(\d+)%", tokens["gradient"])
        for color, percent in stops:
            self.assertEqual(music.gradient_color(int(percent) / 100), color.lower())

    def test_short_and_tall_bars_show_the_full_token_gradient(self):
        app = self.make_app()
        app.bars = [20.0, 40.0, 20.0]
        with patch.object(music.time, 'monotonic', return_value=app.last_frame_time):
            lines = app.render_spectrum(8, 10)
        colored_rows = []
        for line in lines:
            color = None
            cells = []
            for part in re.findall(r'\x1b\[[0-9;]*m|[^\x1b]+', line):
                if part.startswith('\x1b['):
                    color = part if part.startswith('\x1b[38;2;') else None
                else:
                    cells.extend((char, color) for char in part)
            colored_rows.append(cells)
        top_color = music.fg(music.GRADIENT_STOPS[0][1])
        bottom_color = music.fg(music.GRADIENT_STOPS[-1][1])
        for column in (0, 3, 6):
            filled = [(row[column][0], row[column][1]) for row in colored_rows if row[column][0] != ' ']
            self.assertGreater(len(filled), 1)
            self.assertEqual(filled[0][1], top_color)
            self.assertEqual(filled[-1][1], bottom_color)

    def test_downsampling_preserves_all_frequency_bins(self):
        values = [0, 0, 100, 0, 0]
        bars = music.resample_bars(values, 3)
        self.assertAlmostEqual(sum(bars) / 3, sum(values) / len(values))
        self.assertGreater(bars[1], bars[0])

    def test_biased_audio_stays_balanced_after_resize(self):
        app = self.make_app()
        biased = [5.0] * (music.NUM_BARS - 8) + [100.0] * 8
        now = app.last_frame_time
        with patch.object(music, "cava_raw_targets", biased):
            for width in (80, 86, 120, 192, 40, 2):
                now += 0.03
                with patch.object(music.time, "monotonic", return_value=now):
                    app.render_spectrum(width, 20)
                for left, right in zip(app.bars, reversed(app.bars)):
                    self.assertAlmostEqual(left, right)

    def test_mirrored_spectrum_keeps_bass_at_center_and_treble_at_edges(self):
        for count in (5, 6):
            with self.subTest(count=count):
                bass = music.mirrored_bars([100, 0, 0], count)
                treble = music.mirrored_bars([0, 0, 100], count)
                self.assertEqual(len(bass), count)
                self.assertEqual(bass, bass[::-1])
                self.assertEqual(treble, treble[::-1])
                self.assertEqual(max(bass), bass[count // 2])
                self.assertEqual(max(treble), treble[0])

    def test_center_reacts_to_music_when_low_frequency_bins_are_silent(self):
        app = self.make_app()
        now = app.last_frame_time
        heights = []
        for level in (20.0, 80.0, 10.0):
            values = [0.0] * (music.NUM_BARS // 2) + [level] * (music.NUM_BARS // 2)
            now += 0.1
            with patch.object(music, "cava_raw_targets", values), patch.object(music.time, "monotonic", return_value=now):
                app.render_spectrum(80, 20)
            heights.append(app.bars[len(app.bars) // 2])
        self.assertTrue(all(height > 0 for height in heights))
        self.assertGreater(heights[1], heights[0])
        self.assertLess(heights[2], heights[1])

    def test_frames_stay_inside_terminal_and_clear_old_bars(self):
        app = self.make_app()
        app.is_synced = True
        app.synced_lyrics = [(0, "A long lyric 日本語 e\u0301 " * 20)]
        app.scaled_lyrics = True
        for cols, rows in ((80, 24), (40, 12), (24, 12), (192, 55), (12, 5)):
            with self.subTest(size=(cols, rows)):
                output = io.StringIO()
                with patch.object(music.shutil, "get_terminal_size", return_value=(cols, rows)):
                    with patch.object(music.sys, "stdout", output):
                        app.render()
                frame = output.getvalue()
                self.assertNotIn("\n", frame)
                lines = re.findall(
                    r"\x1b\[(\d+);1H\x1b\[K(.*?)(?=\x1b\[\d+;1H|\x1b\[\?2026l)",
                    frame,
                )
                self.assertEqual(len(lines), rows)
                draws = re.findall(
                    r"\x1b\[(\d+);1H(.*?)(?=\x1b\[\d+;1H|\x1b\[\?2026l)",
                    frame,
                )
                for number, line in draws:
                    self.assertLessEqual(int(number), rows)
                    line = plain(line).removeprefix("\x1b[K")
                    cells = 0
                    for part in re.split(r"(\x1b\]66;s=\d;[^\x07]*\x07)", line):
                        scaled = re.fullmatch(r"\x1b\]66;s=(\d);([^\x07]*)\x07", part)
                        if scaled:
                            scale = int(scaled[1])
                            self.assertLessEqual(int(number) + scale - 1, rows)
                            cells += scale * music.text_width(scaled[2])
                        else:
                            cells += music.text_width(part)
                    self.assertLessEqual(cells, cols)


class KaraokeTests(unittest.TestCase):
    def make_app(self):
        with patch.object(music.threading.Thread, "start"):
            app = music.LyricsApp()
        app.lyrics_canvas = None
        return app

    def test_enhanced_lrc_keeps_word_times_out_of_visible_text(self):
        lines, cues = music.parse_lyrics("[00:10]<00:10.5>Chào <00:12>bạn<00:13>")
        self.assertEqual(lines, [(10.0, "Chào bạn")])
        self.assertEqual(cues[10.0], [(10.5, 0), (12.0, 5), (13.0, 8)])

    def test_repeated_lines_shift_word_times_and_offset_together(self):
        lines, cues = music.parse_lyrics("[offset:500]\n[00:10][00:20]<00:10>Hi <00:11>there")
        self.assertEqual(lines, [(10.5, "Hi there"), (20.5, "Hi there")])
        self.assertEqual(cues[20.5], [(20.5, 0), (21.5, 3)])

    def test_estimated_highlight_follows_position_in_both_directions(self):
        text = "One two three"
        self.assertEqual(music.karaoke_prefix(text, -1, 0, 6), 0)
        self.assertEqual(music.karaoke_prefix(text, 0, 0, 6), 0)
        self.assertEqual(music.karaoke_prefix(text, 2, 0, 6), 4)
        self.assertEqual(music.karaoke_prefix(text, 6, 0, 6), len(text))
        self.assertGreater(music.karaoke_prefix(text, 5, 0, 6), music.karaoke_prefix(text, 1, 0, 6))

    def test_actual_word_cues_take_priority_over_estimated_pacing(self):
        cues = [(10, 0), (18, 4), (20, 7)]
        self.assertEqual(music.karaoke_prefix("abc def", 12, 10, 20, cues), 1)
        self.assertEqual(music.karaoke_prefix("abc def", 18, 10, 20, cues), 4)
        self.assertEqual(music.karaoke_prefix("abc def", 20, 10, 20, cues), 7)

    def test_highlight_blends_within_a_character_without_changing_glyph_boundaries(self):
        frames = [music.karaoke_text("Chào", progress, 2) for progress in (0.1, 0.4, 0.7)]
        self.assertEqual(len(set(frames)), 3)
        for frame in frames:
            self.assertEqual(re.findall(r"\x1b\]66;s=2;([^\x07]*)\x07", frame), list("Chào"))
        progress = [music.karaoke_progress("abcd", time, 0, 4) for time in (0.1, 0.2, 0.3)]
        self.assertEqual(len(set(progress)), 3)
        self.assertTrue(all(0 < value < 1 for value in progress))

    def test_combining_marks_remain_attached_during_color_blending(self):
        frame = music.karaoke_text("e\u0301x", 0.5, 2)
        self.assertEqual(re.findall(r"\x1b\]66;s=2;([^\x07]*)\x07", frame), ["e\u0301", "x"])

    def test_line_transition_fades_briefly_around_the_boundary(self):
        self.assertEqual(music.line_visibility(5, 0, 10), 1)
        self.assertAlmostEqual(music.line_visibility(9.95, 0, 10), 0.5)
        self.assertEqual(music.line_visibility(10, 0, 10), 0)
        self.assertEqual(music.line_visibility(10, 10, 20), 0)
        self.assertAlmostEqual(music.line_visibility(10.08, 10, 20), 0.5)
        self.assertEqual(music.line_visibility(10.2, 10, 20), 1)

    def test_short_and_wrapped_lyrics_keep_the_same_spectrum_region(self):
        app = self.make_app()
        app.scaled_lyrics = True
        app.is_synced = True
        app.position = 2
        app.status = "Paused"
        heights = []
        for text in ("Short lyric", "A much longer lyric with enough words to wrap over multiple lines " * 3):
            app.synced_lyrics = [(0, text), (10, "Upcoming")]
            with patch.object(music.sys, "stdout", io.StringIO()), patch.object(music.shutil, "get_terminal_size", return_value=(80, 24)):
                with patch.object(app, "render_spectrum", return_value=[]) as spectrum:
                    app.render()
            heights.append(spectrum.call_args.args[1])
        self.assertEqual(heights[0], heights[1])

    def test_active_line_stays_uniform_without_word_progress(self):
        app = self.make_app()
        app.is_synced = True
        app.synced_lyrics = [(0, "A long sustained lyric"), (30, "Next")]
        app.status = "Paused"
        frames = []
        with patch.object(music.shutil, "get_terminal_size", return_value=(80, 24)):
            with patch.object(music, "karaoke_progress", side_effect=AssertionError("Word progress should be disabled")):
                for position in (5, 15, 25):
                    app.position = position
                    output = io.StringIO()
                    with patch.object(music.sys, "stdout", output), patch.object(app, "render_spectrum", return_value=[]):
                        app.render()
                    frames.append(output.getvalue())
        self.assertEqual(len(set(frames)), 1)

    @unittest.skipIf(music.yaml is None, "PyYAML is unavailable")
    def test_lyricsfile_word_times_and_rests_override_uniform_lrc_timing(self):
        record = {"hasWordSync": True, "syncedLyrics": "[00:10]One two\n[00:20]Next",
                  "lyricsfile": """version: '1.0'
lines:
  - text: One two
    start_ms: 10000
    end_ms: 16000
    words:
      - {text: One, start_ms: 10000, end_ms: 10500}
      - {text: two, start_ms: 15000, end_ms: 16000}
"""}
        lines, cues = music.parse_lyrics_record(record)
        self.assertEqual(lines, [(10, "One two")])
        self.assertEqual(int(music.karaoke_progress("One two", 12, 10, 20, cues[10])), 3)
        self.assertEqual(music.karaoke_progress("One two", 15, 10, 20, cues[10]), 4)
        self.assertEqual(music.karaoke_progress("One two", 16, 10, 20, cues[10]), 7)

    def test_invalid_lyricsfile_keeps_the_lrc_fallback(self):
        record = {"hasWordSync": True, "lyricsfile": "not: [valid", "syncedLyrics": "[00:01]Fallback"}
        lines, _ = music.parse_lyrics_record(record)
        self.assertEqual(lines, [(1, "Fallback")])

    def test_sync_adjustment_is_saved_for_the_video_without_playlist_parameters(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(music, "CACHE_DIR", folder):
            key = music.sync_key("Title", "Artist", "https://www.youtube.com/watch?v=VideoID&list=One")
            same = music.sync_key("Title", "Artist", "https://www.youtube.com/watch?v=VideoID&list=Two")
            self.assertEqual(key, same)
            app = self.make_app()
            app.sync_track_key = key
            app.handle_key("\x1b[D")
            self.assertEqual(music.load_sync_offset(same), -0.5)
            app.handle_key("0")
            self.assertEqual(music.load_sync_offset(same), 0)

    def test_small_mpris_corrections_do_not_step_the_highlight_backwards(self):
        app = self.make_app()
        with patch.object(music.time, "monotonic", return_value=100):
            app.sync_playback("Playing", 10, "track")
        with patch.object(music.time, "monotonic", return_value=100.4):
            before = app.get_interpolated_pos()
            app.sync_playback("Playing", 10.2, "track")
            self.assertEqual(app.get_interpolated_pos(), before)
        positions = [app.elapsed_position(100.4 + frame / 60) for frame in range(25)]
        self.assertTrue(all(left < right for left, right in zip(positions, positions[1:])))

    def test_pause_freezes_karaoke_clock(self):
        app = self.make_app()
        app.status = "Paused"
        app.position = 12
        app.last_sync_time = 100
        with patch.object(music.time, "monotonic", return_value=200):
            self.assertEqual(app.get_interpolated_pos(), 12)
        app.status = "Playing"
        with patch.object(music.time, "monotonic", return_value=101):
            self.assertEqual(app.get_interpolated_pos(), 13)

    def test_mpris_microseconds_are_converted_even_near_track_start(self):
        app = self.make_app()
        output = "Playing\t3000\t9000\tTitle\tArtist\tAlbum\n"
        with patch.object(music.subprocess, "check_output", return_value=output), patch.object(app, "load_lyrics_async"):
            app.update_mpris()
        self.assertEqual(app.position, 0.003)
        self.assertEqual(app.length, 0.009)

    def test_firefox_near_zero_position_reports_do_not_reset_elapsed_clock(self):
        app = self.make_app()
        for now, raw in ((100, 0.000022), (100.4, 0.000016), (100.8, 0.000025), (101.2, 0.0)):
            with patch.object(music.time, "monotonic", return_value=now):
                app.sync_playback("Playing", raw, "track")
                self.assertAlmostEqual(app.get_interpolated_pos(), now - 100 + 0.000022)
        self.assertTrue(app.position_is_estimated)

    def test_estimated_clock_pauses_and_resumes_without_counting_pause_time(self):
        app = self.make_app()
        for now, status in ((100, "Playing"), (102, "Paused"), (110, "Paused"), (120, "Playing")):
            with patch.object(music.time, "monotonic", return_value=now):
                app.sync_playback(status, 0, "track")
        with patch.object(music.time, "monotonic", return_value=121):
            self.assertEqual(app.get_interpolated_pos(), 3)

    def test_real_position_recovers_and_genuine_rewind_requires_confirmation(self):
        app = self.make_app()
        for now in (100, 101, 102):
            with patch.object(music.time, "monotonic", return_value=now):
                app.sync_playback("Playing", 0, "track")
        with patch.object(music.time, "monotonic", return_value=103):
            app.sync_playback("Playing", 30, "track")
            self.assertEqual(app.get_interpolated_pos(), 30)
        self.assertFalse(app.position_is_estimated)
        with patch.object(music.time, "monotonic", return_value=104):
            app.sync_playback("Playing", 0, "track")
            self.assertEqual(app.get_interpolated_pos(), 31)
        for now, position in ((104.4, 0.4), (104.8, 0.8), (105.2, 1.2)):
            with patch.object(music.time, "monotonic", return_value=now):
                app.sync_playback("Playing", position, "track")
        with patch.object(music.time, "monotonic", return_value=105.2):
            self.assertEqual(app.get_interpolated_pos(), 1.2)

    def test_zero_or_missing_reports_cannot_rewind_a_running_song(self):
        app = self.make_app()
        with patch.object(music.time, "monotonic", return_value=100):
            app.sync_playback("Playing", 90, "track")
        for step, reported in enumerate((0, 0.000025, 0, 0.000034, 0.000018), 1):
            now = 100 + step * 0.4
            with patch.object(music.time, "monotonic", return_value=now):
                app.sync_playback("Playing", reported, "track")
                self.assertAlmostEqual(app.get_interpolated_pos(), 90 + step * 0.4)

    def test_one_stale_nonzero_report_does_not_rewind_the_song(self):
        app = self.make_app()
        samples = ((100, 90), (100.4, 8), (100.8, 90.8))
        for now, reported in samples:
            with patch.object(music.time, "monotonic", return_value=now):
                app.sync_playback("Playing", reported, "track")
                self.assertAlmostEqual(app.get_interpolated_pos(), now - 100 + 90)

    def test_repeated_stale_position_does_not_confirm_a_rewind_while_playing(self):
        app = self.make_app()
        with patch.object(music.time, "monotonic", return_value=100):
            app.sync_playback("Playing", 90, "track")
        for step in range(1, 10):
            now = 100 + step * 0.4
            with patch.object(music.time, "monotonic", return_value=now):
                app.sync_playback("Playing", 8, "track")
                self.assertAlmostEqual(app.get_interpolated_pos(), now - 100 + 90)

    def test_temporary_missing_url_artist_or_title_does_not_restart_track(self):
        app = self.make_app()
        samples = [
            "Playing\t90000000\t200000000\tTitle\tArtist\tAlbum\thttps://www.youtube.com/watch?v=ID&list=One\n",
            "Playing\t0\t\tTitle\t\t\t\n",
            "Playing\t0\t\t\t\t\t\n",
            "Playing\t91200000\t200000000\t(3)Title\tArtist - Topic\tAlbum\thttps://www.youtube.com/watch?v=ID&list=Two\n",
        ]
        with patch.object(music.subprocess, "check_output", side_effect=samples), patch.object(app, "load_lyrics_async") as load:
            for step in range(len(samples)):
                now = 100 + step * 0.4
                with patch.object(music.time, "monotonic", return_value=now):
                    app.update_mpris()
                    self.assertAlmostEqual(app.get_interpolated_pos(), 90 + step * 0.4)
            self.assertEqual(load.call_count, 1)
        self.assertEqual(app.current_track_key, "url:ID")
        self.assertEqual(app.length, 200)

    def test_url_arriving_after_metadata_is_attached_without_restarting_clock(self):
        app = self.make_app()
        samples = ["Playing\t90000000\t200000000\tTitle\tArtist\tAlbum\t\n",
                   "Playing\t0\t200000000\tTitle\tArtist\tAlbum\thttps://www.youtube.com/watch?v=ID\n"]
        with patch.object(music.subprocess, "check_output", side_effect=samples), patch.object(app, "load_lyrics_async") as load:
            for step in range(2):
                now = 100 + step * 0.4
                with patch.object(music.time, "monotonic", return_value=now):
                    app.update_mpris()
                    self.assertAlmostEqual(app.get_interpolated_pos(), 90 + step * 0.4)
            self.assertEqual(load.call_count, 1)
        self.assertEqual(app.clock_track_key, "url:ID")

    def test_a_different_video_with_the_same_title_starts_a_new_clock(self):
        app = self.make_app()
        samples = ["Playing\t90000000\t200000000\tTitle\tArtist\tAlbum\thttps://www.youtube.com/watch?v=One\n",
                   "Playing\t0\t200000000\tTitle\tArtist\tAlbum\thttps://www.youtube.com/watch?v=Two\n"]
        with patch.object(music.subprocess, "check_output", side_effect=samples), patch.object(app, "load_lyrics_async") as load:
            for step in range(2):
                with patch.object(music.time, "monotonic", return_value=100 + step):
                    app.update_mpris()
            self.assertEqual(load.call_count, 2)
        self.assertEqual(app.position, 0)
        self.assertEqual(app.clock_track_key, "url:Two")

    def test_constant_position_reports_still_allow_karaoke_to_advance(self):
        app = self.make_app()
        for now in (100, 100.4, 100.8, 101.2, 102):
            with patch.object(music.time, "monotonic", return_value=now):
                app.sync_playback("Playing", 12, "track")
        with patch.object(music.time, "monotonic", return_value=102):
            self.assertEqual(app.get_interpolated_pos(), 14)
        self.assertTrue(app.position_is_estimated)

    def test_new_track_resets_estimated_clock(self):
        app = self.make_app()
        with patch.object(music.time, "monotonic", return_value=100):
            app.sync_playback("Playing", 0, "old")
        with patch.object(music.time, "monotonic", return_value=150):
            app.sync_playback("Playing", 0, "new")
            self.assertEqual(app.get_interpolated_pos(), 0)

    def test_old_lyrics_cannot_overwrite_a_new_track(self):
        app = self.make_app()
        with patch.object(music.threading, "Thread") as thread:
            app.load_lyrics_async("Old", "", 30)
            old_worker = thread.call_args.kwargs["target"]
            app.load_lyrics_async("New", "", 30)
            new_worker = thread.call_args.kwargs["target"]
        with patch.object(music, "fetch_lrclib", side_effect=[
            {"syncedLyrics": "[00:00]New lyric"}, {"syncedLyrics": "[00:00]Old lyric"}
        ]):
            new_worker()
            old_worker()
        self.assertEqual(app.synced_lyrics, [(0, "New lyric")])
        self.assertFalse(app.loading_lyrics)

    def test_active_lyric_is_doubled_and_centered_in_kitty(self):
        app = self.make_app()
        app.scaled_lyrics = True
        app.is_synced = True
        app.synced_lyrics = [(0, "First line"), (10, "Current line"), (20, "Next line")]
        app.position = 15
        app.status = "Paused"
        output = io.StringIO()
        with patch.object(music.sys, "stdout", output), patch.object(music.shutil, "get_terminal_size", return_value=(80, 24)):
            app.render()
        frame = output.getvalue()
        payload = re.search(r"\x1b\[(\d+);1H[^H]*?\x1b\]66;s=2;", frame)
        self.assertIsNotNone(payload)
        self.assertEqual(int(payload[1]), 12)
        self.assertIn(music.fg(music.PALETTE['text_inverse']), frame)
        self.assertNotIn(music.fg(music.C_LYRIC_HIGHLIGHT), frame)
        self.assertNotIn("Play/Pause", frame)


class LyricsLookupTests(unittest.TestCase):
    title = "có hẹn với thanh xuân - MONSTAR | official music video"
    artist = "ST.319 Entertainment"

    def record(self, title="Có Hẹn Với Thanh Xuân", artist="MONSTAR", duration=218, synced=True):
        return {"trackName": title, "artistName": artist, "duration": duration,
                "syncedLyrics": "[00:00]Test lyric" if synced else None,
                "plainLyrics": "Test lyric"}

    def test_rejects_unrelated_monstar_tv_result_from_the_reported_bug(self):
        wrong = self.record("Vandebo - Huuhdiin 100 (Official Music Video)", "Monstar TV", 230)
        candidates = music.track_candidates(self.title, self.artist)
        self.assertIsNone(music.select_lyrics([wrong], candidates, 268))

    def test_selects_correct_track_instead_of_first_synced_search_result(self):
        wrong = self.record("Vandebo - Huuhdiin 100", "Monstar TV", 230)
        right = self.record(synced=False)
        candidates = music.track_candidates(self.title, self.artist)
        self.assertIs(music.select_lyrics([wrong, right], candidates, 268), right)

    def test_both_youtube_title_orders_work_with_uploader_as_metadata_artist(self):
        right = self.record()
        for title in (self.title, "MONSTAR - CÓ HẸN VỚI THANH XUÂN (Official MV)"):
            with self.subTest(title=title):
                candidates = music.track_candidates(title, self.artist)
                self.assertIs(music.select_lyrics([right], candidates, 268), right)

    def test_pipe_separated_mtp_titles_preserve_the_song_name(self):
        right = self.record('Muộn Rồi Mà Sao Còn', 'Sơn Tùng M-TP', 275)
        wrong = [self.record('SƠN TÙNG M-TP | ĐỪNG LÀM TRÁI TIM ANH ĐAU | OFFICIAL MUSIC VIDEO', 'Sơn Tùng M-TP', 326),
                 self.record('Nắng Ấm Xa Dần - Sơn Tùng M-TP', 'Sơn Tùng M-TP Official', 192)]
        titles = ('SƠN TÙNG M-TP | MUỘN RỒI MÀ SAO CÒN | OFFICIAL MUSIC VIDEO',
                  'MUỘN RỒI MÀ SAO CÒN ｜ SƠN TÙNG M-TP ｜ Official MV')
        for title in titles:
            with self.subTest(title=title):
                candidates = music.track_candidates(title, 'Sơn Tùng M-TP Official')
                self.assertIs(music.select_lyrics(wrong + [right], candidates), right)
                self.assertIsNone(music.select_lyrics(wrong, candidates))

    def test_pipe_separated_record_must_match_the_song_not_just_the_performer(self):
        title = 'SƠN TÙNG M-TP | MUỘN RỒI MÀ SAO CÒN | OFFICIAL MUSIC VIDEO'
        right = self.record(title, 'Sơn Tùng M-TP', 275)
        candidates = music.track_candidates('Muộn Rồi Mà Sao Còn', 'Sơn Tùng M-TP')
        self.assertIs(music.select_lyrics([right], candidates), right)

    def test_pipe_video_decoration_does_not_pollute_track_or_artist(self):
        candidates = music.track_candidates('Không Buông - Hngle, Ari x CaoTri | Official Lofi Lyrics', 'CaoTri Official')
        self.assertIn(('Không Buông', 'Hngle, Ari x CaoTri'), candidates)
        self.assertEqual(candidates.versions, {'lofi'})

    def test_wrong_cached_song_from_same_singer_does_not_skip_the_correct_lookup(self):
        title = 'SƠN TÙNG M-TP | MUỘN RỒI MÀ SAO CÒN | OFFICIAL MUSIC VIDEO'
        artist = 'Sơn Tùng M-TP Official'
        right = self.record('Muộn Rồi Mà Sao Còn', 'Sơn Tùng M-TP', 275)
        wrong = dict(self.record('SƠN TÙNG M-TP | ĐỪNG LÀM TRÁI TIM ANH ĐAU | OFFICIAL MUSIC VIDEO', 'Sơn Tùng M-TP', 326), _lookup_version=3)
        with tempfile.TemporaryDirectory() as folder, patch.object(music, 'CACHE_DIR', folder):
            path = music.lyrics_cache_path(title, artist)
            path.write_text(json.dumps(wrong))
            response = io.BytesIO(json.dumps([right]).encode())
            with patch.object(music.urllib.request, 'urlopen', return_value=response) as request:
                found = music.fetch_lrclib(title, artist)
            self.assertEqual(found['trackName'], right['trackName'])
            params = urllib.parse.parse_qs(urllib.parse.urlparse(request.call_args.args[0].full_url).query)
            self.assertEqual(params['track_name'], ['MUỘN RỒI MÀ SAO CÒN'])
            self.assertEqual(json.loads(path.read_text())['trackName'], right['trackName'])

    def test_punctuation_and_vietnamese_diacritics_do_not_prevent_a_match(self):
        right = self.record("Noi Nay Co Anh", "Son Tung MTP")
        candidates = music.track_candidates("Sơn Tùng M-TP - Nơi Này Có Anh (Official Audio)", "Subtify")
        self.assertIs(music.select_lyrics([right], candidates), right)

    def test_same_title_with_another_performer_is_rejected(self):
        wrong = self.record("Có Hẹn Với Thanh Xuân", "Different Artist")
        candidates = music.track_candidates("Có Hẹn Với Thanh Xuân", "MONSTAR")
        self.assertIsNone(music.select_lyrics([wrong], candidates))

    def test_generic_browser_title_cannot_match_an_unrelated_song(self):
        wrong = self.record("Make Your Troubles Go Away", "Andra Day")
        candidates = music.track_candidates("(3)TikTok - Make Your Day")
        self.assertIsNone(music.select_lyrics([wrong], candidates))

    def test_other_languages_still_work_when_track_and_performer_match(self):
        right = self.record("Монгол тест", "Test Band")
        self.assertIs(music.select_lyrics([right], music.track_candidates("Монгол тест", "Test Band")), right)

    def test_records_without_lyrics_are_skipped(self):
        empty = self.record()
        empty.update(syncedLyrics=None, plainLyrics=None)
        self.assertIsNone(music.select_lyrics([empty], music.track_candidates(self.title, self.artist)))

    def test_word_synced_version_is_preferred_over_line_only_record(self):
        line_only = self.record()
        word_synced = dict(self.record(duration=219), hasWordSync=True, lyricsfile="version: '1.0'")
        candidates = music.track_candidates(self.title, self.artist)
        self.assertIs(music.select_lyrics([line_only, word_synced], candidates, 218), word_synced)

    def test_instrumental_and_sped_up_versions_do_not_match_original(self):
        candidates = music.track_candidates("Thức Giấc - Da LAB (Official MV)", "Da LAB Official")
        for title in ("Thức Giấc (Instrumental)", "Thức Giấc - Sped Up", "Thức Giấc (Remix)"):
            with self.subTest(title=title):
                self.assertIsNone(music.select_lyrics([self.record(title, "Da LAB")], candidates))

    def test_requested_live_version_is_kept_even_inside_video_decoration(self):
        candidates = music.track_candidates("Artist - Song (Live Official Video)", "Artist")
        right = self.record("Song (Live)", "Artist")
        self.assertIs(music.select_lyrics([right], candidates), right)

    def test_cache_identity_retains_unicode_and_full_length_titles(self):
        first = music.lyrics_cache_path("a" * 80 + "Có", "MONSTAR")
        second = music.lyrics_cache_path("a" * 80 + "Cò", "MONSTAR")
        self.assertNotEqual(first, second)

    def test_wrong_legacy_cache_is_ignored_and_correct_result_is_cached(self):
        right = self.record()
        with tempfile.TemporaryDirectory() as folder, patch.object(music, "CACHE_DIR", folder):
            wrong = self.record("Vandebo - Huuhdiin 100", "Monstar TV", 230)
            (Path(folder) / "ST_319_Entertainment_bad.json").write_text(json.dumps(wrong))
            response = io.BytesIO(json.dumps([wrong, right]).encode("utf-8"))
            with patch.object(music.urllib.request, "urlopen", return_value=response) as request:
                result = music.fetch_lrclib(self.title, self.artist, 268)
            self.assertEqual(result["trackName"], right["trackName"])
            params = urllib.parse.parse_qs(urllib.parse.urlparse(request.call_args.args[0].full_url).query)
            self.assertEqual(params["track_name"], ["có hẹn với thanh xuân"])
            self.assertEqual(params["artist_name"], ["MONSTAR"])
            with patch.object(music.urllib.request, "urlopen") as request:
                cached = music.fetch_lrclib(self.title, self.artist, 268)
                request.assert_not_called()
            self.assertEqual(cached["artistName"], "MONSTAR")

    def test_no_match_returns_none_instead_of_falling_back_to_first_result(self):
        wrong = self.record("Completely Unrelated Song", "Other Singer")
        with tempfile.TemporaryDirectory() as folder, patch.object(music, "CACHE_DIR", folder):
            with patch.object(music.urllib.request, "urlopen", side_effect=lambda *args, **kwargs: io.BytesIO(json.dumps([wrong]).encode())):
                with patch.object(music.time, "sleep"):
                    self.assertIsNone(music.fetch_lrclib(self.title, self.artist, 268))
            self.assertFalse(list(Path(folder).glob("*.json")))


@unittest.skipIf(music.SpectrumCanvas is None, "Cairo/Pango is unavailable")
class SpectrumCanvasTests(unittest.TestCase):
    def test_gradient_tile_cache_reuses_surfaces_and_limits_memory(self):
        import cairo
        canvas = music.SpectrumCanvas(music.GRADIENT_STOPS)
        canvas.bar_cache_limit = 64 * 1024
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 160, 100)
        context = cairo.Context(surface)
        canvas.paint_cached(context, [20, 30, 20], 8, 160, 100)
        previous = dict(canvas.bar_cache)
        canvas.paint_cached(context, [20, 30, 20], 8, 160, 100)
        self.assertTrue(all(canvas.bar_cache[key] is value for key, value in previous.items()))
        for height in range(1, 100):
            canvas.paint_cached(context, [height] * 3, 8, 160, 100)
        self.assertLessEqual(canvas.bar_cache_bytes, canvas.bar_cache_limit)

    def test_default_transport_uses_inline_compressed_stream_without_temp_files(self):
        canvas = music.SpectrumCanvas(music.GRADIENT_STOPS)
        self.assertFalse(canvas.file_transport)
        self.addCleanup(canvas.clear)
        command = canvas.render([30] * 3, 80, 24, 15, cell_dimensions=(9, 20))
        self.assertIn('o=z,', command)
        self.assertNotIn('t=t,', command)
        self.assertIsNone(canvas.buffers)
        self.assertEqual(len(canvas.pending), 0)

    def test_local_transport_is_bounded_and_releases_temporary_frames(self):
        from pathlib import Path
        canvas = music.SpectrumCanvas(music.GRADIENT_STOPS)
        canvas.file_transport = True
        self.addCleanup(canvas.clear)
        for level in (10, 20, 30):
            command = canvas.render([level] * 3, 8, 12, 9, cell_dimensions=(10, 20))
            self.assertIn('t=t,', command)
        self.assertEqual(canvas.render([40] * 3, 8, 12, 9, cell_dimensions=(10, 20)), '')
        self.assertEqual(len(canvas.pending), 3)
        paths = [path for path, _ in canvas.pending]
        self.assertTrue(all(path.stat().st_size == 80 * 60 * 4 for path in paths))
        pixels = paths[-1].read_bytes()
        bottom = pixels[((60 - 1) * 80 + 10) * 4:((60 - 1) * 80 + 10) * 4 + 4]
        expected = music.hex_to_rgb(music.GRADIENT_STOPS[-1][1])
        self.assertEqual(bottom[3], 255)
        self.assertTrue(all(abs(a - b) < 12 for a, b in zip(bottom[:3], expected)))
        root = Path(canvas.buffers.name)
        canvas.clear()
        self.assertFalse(root.exists())
        self.assertTrue(all(not path.exists() for path in paths))

    def test_unread_local_frames_fall_back_to_inline_transport(self):
        canvas = music.SpectrumCanvas(music.GRADIENT_STOPS)
        canvas.file_transport = True
        self.addCleanup(canvas.clear)
        with patch('music_spectrum.time.monotonic', return_value=0):
            for level in (10, 20, 30):
                canvas.render([level] * 3, 8, 12, 9, cell_dimensions=(10, 20))
        with patch('music_spectrum.time.monotonic', return_value=1):
            command = canvas.render([40] * 3, 8, 12, 9, cell_dimensions=(10, 20))
        self.assertFalse(canvas.file_transport)
        self.assertIn('o=z,', command)
        self.assertFalse(canvas.pending)

    def test_gradient_changes_per_pixel_and_preserves_transparent_gaps(self):
        import cairo
        import sys
        canvas = music.SpectrumCanvas(music.GRADIENT_STOPS)
        png = canvas.render_png((120, 60, 30), 8, 80, 120)
        surface = cairo.ImageSurface.create_from_png(io.BytesIO(png))
        data, stride = bytes(surface.get_data()), surface.get_stride()

        def pixel(x, y):
            channels = data[y * stride + x * 4:y * stride + x * 4 + 4]
            return tuple(channels[index] for index in ((2, 1, 0, 3) if sys.byteorder == 'little' else (1, 2, 3, 0)))

        colors = [pixel(10, y) for y in range(120)]
        self.assertGreater(len(set(colors)), 100)
        self.assertLess(max(abs(a - b) for left, right in zip(colors, colors[1:])
                            for a, b in zip(left[:3], right[:3])), 6)
        self.assertTrue(all(color[3] == 255 for color in colors))
        self.assertEqual(pixel(25, 119)[3], 0)  # Space between adjacent bars.
        self.assertEqual(pixel(40, 59)[3], 0)   # Space above a shorter bar.
        self.assertEqual(pixel(40, 60)[3], 255)

    def test_subcell_motion_resize_and_cleanup_reuse_one_image(self):
        canvas = music.SpectrumCanvas(music.GRADIENT_STOPS)
        first = canvas.render([20, 40, 20], 8, 12, 9, gain=2, cell_dimensions=(10, 20))
        self.assertIn(f'i={canvas.image_id}', first)
        self.assertEqual(canvas.render([20, 40, 20], 8, 12, 9, gain=2, cell_dimensions=(10, 20)), '')
        moved = canvas.render([21, 40, 20], 8, 12, 9, gain=2, cell_dimensions=(10, 20))
        self.assertIn(f'i={canvas.image_id}', moved)
        resized = canvas.render([20] * 4, 11, 16, 12, gain=2, cell_dimensions=(10, 20))
        self.assertIn('c=11,r=4', resized)
        self.assertIn(f'i={canvas.image_id}', resized)
        self.assertIn(f'd=I,i={canvas.image_id}', canvas.clear())
        self.assertEqual(canvas.clear(), '')


@unittest.skipIf(music.LyricsCanvas is None, "Cairo/Pango is unavailable")
class LyricsCanvasTests(unittest.TestCase):
    def make_canvas(self):
        return music.LyricsCanvas(music.PALETTE)

    def test_transition_moves_through_fractional_positions(self):
        canvas = self.make_canvas()
        self.assertEqual(canvas.set_target(0, "track", 100), 0)
        self.assertEqual(canvas.set_target(1, "track", 101), 0)
        import music_lyrics
        middle = canvas.scroll_at(101 + music_lyrics.TRANSITION_SECONDS / 2)
        self.assertAlmostEqual(middle, 0.5)
        self.assertEqual(canvas.scroll_at(102), 1)
        self.assertEqual(canvas.set_target(8, "track", 103), 8)

    def test_png_frames_scroll_text_up_in_pixels(self):
        import cairo
        canvas = self.make_canvas()
        centroids = []
        for scroll in (0.0, 0.3, 0.6, 1.0):
            png = canvas.render_png([(0, ""), (5, "Moving text"), (10, "")], scroll, 400, 200, 20)
            surface = cairo.ImageSurface.create_from_png(io.BytesIO(png))
            data = bytes(surface.get_data())
            stride = surface.get_stride()
            alpha_offset = 3 if __import__('sys').byteorder == 'little' else 0
            weights = [sum(data[row * stride + alpha_offset:(row + 1) * stride:4]) for row in range(200)]
            centroids.append(sum(row * weight for row, weight in enumerate(weights)) / sum(weights))
            self.assertEqual(data[alpha_offset], 0)
        self.assertTrue(all(left > right for left, right in zip(centroids, centroids[1:])))

    def test_graphics_payload_is_chunked_png_and_reuses_one_image_id(self):
        canvas = self.make_canvas()
        lines = [(0, "Test lyric"), (5, "Next")]
        _, command = canvas.render(lines, 0, 80, 24, "track", now=0, cell_dimensions=(9, 20))
        chunks = re.findall(r"\x1b_G([^;]*);([^\x1b]*)\x1b\\", command)
        self.assertTrue(chunks)
        self.assertIn(f"i={canvas.image_id}", chunks[0][0])
        self.assertIn("C=1", chunks[0][0])
        self.assertTrue(all(len(payload) <= 4096 for _, payload in chunks))
        self.assertTrue(base64.b64decode(''.join(payload for _, payload in chunks)).startswith(b'\x89PNG\r\n\x1a\n'))
        _, unchanged = canvas.render(lines, 0, 80, 24, "track", now=1, cell_dimensions=(9, 20))
        self.assertEqual(unchanged, '')
        self.assertIn(f"i={canvas.image_id}", canvas.clear())
        self.assertEqual(canvas.clear(), '')


class VisibilityWatcherTests(unittest.TestCase):
    def test_watcher_defaults_to_visible_without_hyprland(self):
        with patch.dict(music.os.environ, {}, clear=True):
            watcher = music.HyprlandVisibilityWatcher()
            self.assertTrue(watcher.is_visible)
            self.assertIsNone(watcher.get_socket_fd())
            watcher.close()

    def test_watcher_detects_hidden_and_visible_workspaces(self):
        with patch.dict(music.os.environ, {"HYPRLAND_INSTANCE_SIGNATURE": "fake_sig", "XDG_RUNTIME_DIR": "/tmp"}):
            with patch.object(music.socket.socket, "connect", return_value=None), \
                 patch.object(music.os.path, "exists", return_value=True):
                watcher = music.HyprlandVisibilityWatcher()
                
                # Mock monitors on workspace 1, window on workspace 3 -> hidden
                watcher.active_workspaces = {1}
                watcher.window_workspace_id = 3
                watcher.is_visible = (watcher.window_workspace_id in watcher.active_workspaces)
                self.assertFalse(watcher.is_visible)

                # Monitor switches to workspace 3 -> visible
                watcher.active_workspaces = {3}
                watcher.is_visible = (watcher.window_workspace_id in watcher.active_workspaces)
                self.assertTrue(watcher.is_visible)
                watcher.close()


if __name__ == "__main__":
    unittest.main()
