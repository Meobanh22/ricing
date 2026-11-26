"""Focus overlay transport and lifecycle checks without a desktop session."""

import os
import errno
from pathlib import Path
import socket
import sys
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'config/hypr/scripts/terminal'))
from music_focus import MusicFocus, receive_messages, send_message


class MusicFocusTests(unittest.TestCase):
    def setUp(self):
        left, right = socket.socketpair(socket.AF_UNIX, socket.SOCK_DGRAM)
        try:
            left.send(b'local IPC probe')
        except OSError as error:
            if error.errno in (errno.EPERM, errno.EACCES):
                self.skipTest('The sandbox blocks local socket messages')
            raise
        finally:
            left.close()
            right.close()

    def pair(self):
        left, right = socket.socketpair(socket.AF_UNIX, socket.SOCK_DGRAM)
        left.setblocking(False)
        right.setblocking(False)
        self.addCleanup(left.close)
        self.addCleanup(right.close)
        return left, right

    def test_unicode_frames_and_keys_keep_packet_boundaries(self):
        parent, child = self.pair()
        frame = {'type': 'frame', 'lines': [[0, 'Muộn rồi mà sao còn']], 'bars': [10, 30, 10]}
        self.assertTrue(send_message(parent, frame))
        self.assertEqual(receive_messages(child), [frame])
        child.send(b'invalid packet')
        send_message(child, {'type': 'key', 'value': '\x1b[D'})
        self.assertEqual(receive_messages(parent), [{'type': 'key', 'value': '\x1b[D'}])

    def test_start_ready_controls_and_close_release_the_child(self):
        peers = []
        process = Mock()
        process.poll.return_value = None

        def spawn(*args, **kwargs):
            peer = socket.socket(fileno=os.dup(kwargs['pass_fds'][0]))
            peer.setblocking(False)
            peers.append(peer)
            self.addCleanup(peer.close)
            return process

        focus = MusicFocus()
        with patch('music_focus.subprocess.Popen', side_effect=spawn):
            focus.toggle()
        self.assertTrue(focus.active)
        peer = peers[0]
        send_message(peer, {'type': 'ready'})
        send_message(peer, {'type': 'key', 'value': ' '})
        self.assertEqual(focus.read_keys(), [' '])
        self.assertTrue(focus.ready)
        focus.update([[0, 'Lyric']], 0, 'track', [10, 20], 2, [[0, '#A3183D'], [1, '#BE7AA8']])
        self.assertEqual(receive_messages(peer)[0]['track'], 'track')
        connection = focus.connection
        focus.close()
        self.assertEqual(receive_messages(peer), [{'type': 'close'}])
        self.assertEqual(connection.fileno(), -1)
        self.assertFalse(focus.active)
        focus.close()
        process.wait.assert_called_once()

    def test_toggle_off_reaps_overlay_without_blocking_caller(self):
        process = Mock()
        process.poll.return_value = None
        peers = []

        def spawn(*args, **kwargs):
            peer = socket.socket(fileno=os.dup(kwargs['pass_fds'][0]))
            peer.setblocking(False)
            peers.append(peer)
            self.addCleanup(peer.close)
            return process

        focus = MusicFocus()
        with patch('music_focus.subprocess.Popen', side_effect=spawn):
            focus.toggle()
        with patch('music_focus.threading.Thread') as thread:
            focus.toggle()
        self.assertFalse(focus.active)
        self.assertEqual(receive_messages(peers[0]), [{'type': 'close'}])
        process.wait.assert_not_called()
        thread.assert_called_once()
        thread.call_args.kwargs['target']()
        process.wait.assert_called_once()

    def test_unavailable_or_crashed_overlay_does_not_leave_focus_enabled(self):
        focus = MusicFocus(enabled=False)
        with patch('music_focus.subprocess.Popen') as spawn:
            focus.toggle()
            spawn.assert_not_called()
        parent, _ = self.pair()
        focus.connection = parent
        focus.process = Mock()
        focus.process.poll.return_value = 1
        focus.ready = True
        self.assertFalse(focus.active)
        self.assertFalse(focus.ready)
        self.assertEqual(parent.fileno(), -1)


if __name__ == '__main__':
    unittest.main()
