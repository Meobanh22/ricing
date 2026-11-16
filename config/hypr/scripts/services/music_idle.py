#!/usr/bin/env python3
# music_idle.py — Idle background transparency and terminal input for music.

import json
import re
import time

IDLE_SECONDS = 6.0
FADE_SECONDS = 0.80
NORMAL_TITLE = 'Serena Music'
FOCUS_TITLE = 'Serena Music Focus'
TRANSPARENT_COLOR = 'transparent_background_color7'


class IdleBackdrop:
    def __init__(self, color, enabled=True, normal_opacity=1.0, native=False):
        self.color = 'rgb:' + '/'.join(color.lstrip('#')[index:index + 2] for index in (0, 2, 4))
        self.enabled = enabled
        self.native = native
        # Native mode controls the OS window background, including its edges.
        # The OSC fallback multiplies Kitty's configured background opacity.
        self.normal_opacity = normal_opacity
        self.started = False
        self.focused = False
        self.forced = False
        self.last_activity = 0.0
        self.changed_at = 0.0
        self.from_opacity = normal_opacity
        self.target_opacity = normal_opacity
        self.last_sent = None

    def remote_command(self, name, payload):
        command = {'cmd': name, 'version': [0, 26, 0], 'no_response': True, 'payload': payload}
        return '\x1bP@kitty-cmd' + json.dumps(command, separators=(',', ':')) + '\x1b\\'

    def reset_opacity(self):
        if self.native and self.last_sent is not None:
            # Kitty restores its actual configured opacity when toggling this value.
            return self.remote_command('set-background-opacity', {'opacity': self.last_sent, 'toggle': True})
        return f'\x1b]21;{TRANSPARENT_COLOR}\x1b\\'

    def start(self, now=None):
        if not self.enabled or self.started:
            return ''
        self.started = True
        self.last_activity = time.monotonic() if now is None else now
        command = ('\x1b]30001\x1b\\\x1b[22;0t'
                f'\x1b]2;{NORMAL_TITLE}\x1b\\'
                '\x1b[?1003h\x1b[?1006h\x1b[?1004h')
        if self.native:
            command += self.remote_command('set-spacing', {'settings': {f'padding-{edge}': 0 for edge in ('left', 'right', 'top', 'bottom')}})
        return command

    def interact(self, now=None):
        self.last_activity = time.monotonic() if now is None else now

    def opacity_at(self, now):
        fraction = max(0.0, min(1.0, (now - self.changed_at) / FADE_SECONDS))
        amount = fraction * fraction * (3 - 2 * fraction)
        return self.from_opacity + (self.target_opacity - self.from_opacity) * amount

    def update(self, now=None):
        if not self.started:
            return ''
        now = time.monotonic() if now is None else now
        focused = self.forced or now - self.last_activity >= IDLE_SECONDS
        command = ''
        if focused != self.focused:
            self.from_opacity = self.opacity_at(now)
            self.changed_at = now
            self.target_opacity = 0.0 if focused else self.normal_opacity
            self.focused = focused
            title = FOCUS_TITLE if focused else NORMAL_TITLE
            command += f'\x1b]2;{title}\x1b\\'
        if not focused and now - self.changed_at >= FADE_SECONDS:
            if self.last_sent is not None:
                # Complete the transition before requesting Kitty's default.
                if self.native:
                    command += self.remote_command('set-background-opacity', {'opacity': self.normal_opacity})
                    self.last_sent = self.normal_opacity
                command += self.reset_opacity()
                self.last_sent = None
            return command
        if not focused and self.last_sent is None:
            return command
        opacity = round(self.opacity_at(now), 3)
        if self.last_sent != opacity:
            if self.native:
                command += self.remote_command('set-background-opacity', {'opacity': opacity})
            else:
                command += f'\x1b]21;{TRANSPARENT_COLOR}={self.color}@{opacity:.3f}\x1b\\'
            self.last_sent = opacity
        return command

    def close(self):
        if not self.started:
            return ''
        self.started = False
        command = self.reset_opacity()
        if self.native:
            command += self.remote_command('set-spacing', {'settings': {f'padding-{edge}': None for edge in ('left', 'right', 'top', 'bottom')}})
        return (command + f'\x1b]21;{TRANSPARENT_COLOR}\x1b\\'
                '\x1b[?1003l\x1b[?1006l\x1b[?1004l'
                '\x1b]30101\x1b\\\x1b[23;0t')


class TerminalInput:
    """Consume mouse/focus reports separately, preserving split arrow sequences."""
    mouse = re.compile(r'\x1b\[<\d+;\d+;\d+[Mm]')
    csi = re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]')

    def __init__(self):
        self.pending = ''

    def feed(self, text):
        self.pending += text
        keys = []
        activity = False
        while self.pending:
            if self.pending[0] != '\x1b':
                keys.append(self.pending[0])
                activity = True
                self.pending = self.pending[1:]
                continue
            mouse = self.mouse.match(self.pending)
            if mouse:
                activity = True
                self.pending = self.pending[mouse.end():]
                continue
            if self.pending.startswith(('\x1b]', '\x1b_', '\x1bP')):
                end = self.pending.find('\x1b\\', 2)
                bell = self.pending.find('\x07', 2)
                if bell >= 0 and (end < 0 or bell < end):
                    self.pending = self.pending[bell + 1:]
                elif end >= 0:
                    self.pending = self.pending[end + 2:]
                else:
                    break
                continue
            sequence = self.csi.match(self.pending)
            if sequence:
                value = sequence.group()
                if value in ('\x1b[C', '\x1b[D'):
                    keys.append(value)
                if value != '\x1b[O':
                    activity = True
                self.pending = self.pending[sequence.end():]
                continue
            if len(self.pending) == 1 or self.pending.startswith('\x1b['):
                break
            self.pending = self.pending[2:]
        if len(self.pending) > 8192:
            self.pending = ''
        return keys, activity
