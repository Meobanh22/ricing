"""Idle transparency and input handling regression checks."""

import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "config/hypr/scripts/terminal"))
from music_idle import IdleBackdrop, TerminalInput


class IdleBackdropTests(unittest.TestCase):
    def make_backdrop(self):
        backdrop = IdleBackdrop("#201011")
        backdrop.start(now=0)
        return backdrop

    def test_background_stays_normal_for_six_seconds_then_fades_to_zero(self):
        backdrop = self.make_backdrop()
        self.assertEqual(backdrop.update(now=5.99), '')
        self.assertIn('Serena Music Focus', backdrop.update(now=6))
        self.assertIn('@0.500', backdrop.update(now=6.4))
        self.assertIn('@0.000', backdrop.update(now=6.81))
        self.assertEqual(backdrop.update(now=7), '')

    def test_activity_restores_default_background(self):
        backdrop = self.make_backdrop()
        backdrop.update(now=6)
        backdrop.update(now=6.81)
        backdrop.interact(now=7)
        self.assertIn('Serena Music\x1b', backdrop.update(now=7))
        self.assertIn('@0.500', backdrop.update(now=7.4))
        self.assertIn('transparent_background_color7\x1b', backdrop.update(now=7.81))
        self.assertEqual(backdrop.update(now=8), '')

    def test_mouse_activity_postpones_focus_mode(self):
        backdrop = self.make_backdrop()
        backdrop.interact(now=5)
        self.assertEqual(backdrop.update(now=10.9), '')
        self.assertIn('Serena Music Focus', backdrop.update(now=11))

    def test_desktop_focus_keeps_background_clear_while_controls_are_used(self):
        backdrop = self.make_backdrop()
        backdrop.forced = True
        backdrop.update(now=1)
        self.assertIn('@0.000', backdrop.update(now=1.81))
        backdrop.interact(now=2)
        self.assertEqual(backdrop.update(now=2), '')
        backdrop.forced = False
        self.assertIn('Serena Music\x1b', backdrop.update(now=2))
        self.assertIn('transparent_background_color7\x1b', backdrop.update(now=2.81))

    def test_close_restores_colors_title_and_mouse_modes_once(self):
        backdrop = self.make_backdrop()
        command = backdrop.close()
        self.assertIn('transparent_background_color7\x1b', command)
        self.assertIn('\x1b[?1003l', command)
        self.assertIn('\x1b[?1006l', command)
        self.assertIn('\x1b[?1004l', command)
        self.assertIn('\x1b]30101', command)
        self.assertIn('\x1b[23;0t', command)
        self.assertEqual(backdrop.close(), '')

    def test_background_transition_does_not_change_foreground(self):
        backdrop = self.make_backdrop()
        command = backdrop.update(now=6) + backdrop.update(now=6.81)
        self.assertNotIn('foreground', command)
        self.assertNotIn('cursor=', command)
        self.assertIn('rgb:20/10/11', command)

    def test_disabled_terminal_remains_unchanged(self):
        backdrop = IdleBackdrop("#201011", enabled=False)
        self.assertEqual(backdrop.start(now=0), '')
        self.assertEqual(backdrop.update(now=10), '')
        self.assertEqual(backdrop.close(), '')

    def test_native_fade_covers_padding_and_restores_kitty_defaults(self):
        backdrop = IdleBackdrop('#201011', native=True)
        start = backdrop.start(now=0)
        self.assertIn('set-spacing', start)
        backdrop.update(now=6)
        halfway = backdrop.update(now=6.4)
        self.assertIn('"opacity":0.5', halfway)
        self.assertIn('"opacity":0.0', backdrop.update(now=6.81))
        commands = [json.loads(value) for value in re.findall(r'\x1bP@kitty-cmd(.*?)\x1b\\', backdrop.close())]
        self.assertEqual(commands[0]['payload'], {'opacity': 0.0, 'toggle': True})
        self.assertTrue(all(value is None for value in commands[1]['payload']['settings'].values()))
        self.assertTrue(all(command['no_response'] for command in commands))

    def test_native_controls_are_limited_to_the_requesting_music_window(self):
        import importlib.util
        from types import SimpleNamespace
        spec = importlib.util.spec_from_file_location('music_control', Path(__file__).resolve().parents[1] / 'config/kitty/music_control.py')
        control = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(control)
        window = SimpleNamespace(title='Serena Music Focus')
        command = {'cmd': 'set-background-opacity', 'payload': {'opacity': 0.5}}
        self.assertTrue(control.is_cmd_allowed(command, window, False, {}))
        self.assertFalse(control.is_cmd_allowed(command, window, True, {}))
        self.assertFalse(control.is_cmd_allowed(command, SimpleNamespace(title='Shell'), False, {}))
        for payload in ({'opacity': 0, 'all': True}, {'opacity': 0, 'match_window': 'all'}, {'opacity': float('nan')}):
            self.assertFalse(control.is_cmd_allowed(dict(command, payload=payload), window, False, {}))
        self.assertFalse(control.is_cmd_allowed(dict(command, cmd='send-text'), window, False, {}))


class TerminalInputTests(unittest.TestCase):
    def test_mouse_reports_wake_background_without_becoming_commands(self):
        decoder = TerminalInput()
        self.assertEqual(decoder.feed('\x1b[<35;12;'), ([], False))
        self.assertEqual(decoder.feed('9M'), ([], True))

    def test_split_arrow_and_existing_controls_are_preserved(self):
        decoder = TerminalInput()
        self.assertEqual(decoder.feed('\x1b['), ([], False))
        self.assertEqual(decoder.feed('Dn p'), (['\x1b[D', 'n', ' ', 'p'], True))

    def test_terminal_replies_cannot_trigger_media_shortcuts(self):
        decoder = TerminalInput()
        self.assertEqual(decoder.feed('\x1b_Gi=3;ENOENT:not found next previous q\x1b\\'), ([], False))
        self.assertEqual(decoder.feed('\x1b]21;background=rgb:20/10/11\x1b\\q'), (['q'], True))

    def test_focus_in_wakes_but_focus_out_does_not(self):
        decoder = TerminalInput()
        self.assertEqual(decoder.feed('\x1b[O'), ([], False))
        self.assertEqual(decoder.feed('\x1b[I'), ([], True))


if __name__ == '__main__':
    unittest.main()
