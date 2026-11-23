#!/usr/bin/env python3
# music_player_mpris.py — Desktop media controls for the local terminal player.

import subprocess
import threading
from urllib.parse import unquote, urlparse
from pathlib import Path

from gi.repository import Gio, GLib

ROOT = 'org.mpris.MediaPlayer2'
PLAYER = ROOT + '.Player'
OBJECT_PATH = '/org/mpris/MediaPlayer2'
XML = '''<node>
<interface name="org.mpris.MediaPlayer2">
 <method name="Raise"/><method name="Quit"/>
 <property name="CanQuit" type="b" access="read"/>
 <property name="CanRaise" type="b" access="read"/>
 <property name="HasTrackList" type="b" access="read"/>
 <property name="Identity" type="s" access="read"/>
 <property name="DesktopEntry" type="s" access="read"/>
 <property name="SupportedUriSchemes" type="as" access="read"/>
 <property name="SupportedMimeTypes" type="as" access="read"/>
</interface>
<interface name="org.mpris.MediaPlayer2.Player">
 <method name="Next"/><method name="Previous"/><method name="Pause"/>
 <method name="PlayPause"/><method name="Stop"/><method name="Play"/>
 <method name="Seek"><arg name="Offset" type="x" direction="in"/></method>
 <method name="SetPosition"><arg name="TrackId" type="o" direction="in"/><arg name="Position" type="x" direction="in"/></method>
 <method name="OpenUri"><arg name="Uri" type="s" direction="in"/></method>
 <signal name="Seeked"><arg name="Position" type="x"/></signal>
 <property name="PlaybackStatus" type="s" access="read"/>
 <property name="LoopStatus" type="s" access="readwrite"/>
 <property name="Rate" type="d" access="readwrite"/>
 <property name="Shuffle" type="b" access="readwrite"/>
 <property name="Metadata" type="a{sv}" access="read"/>
 <property name="Volume" type="d" access="readwrite"/>
 <property name="Position" type="x" access="read"/>
 <property name="MinimumRate" type="d" access="read"/>
 <property name="MaximumRate" type="d" access="read"/>
 <property name="CanGoNext" type="b" access="read"/>
 <property name="CanGoPrevious" type="b" access="read"/>
 <property name="CanPlay" type="b" access="read"/>
 <property name="CanPause" type="b" access="read"/>
 <property name="CanSeek" type="b" access="read"/>
 <property name="CanControl" type="b" access="read"/>
</interface></node>'''


def raise_window():
    try:
        subprocess.Popen(['hyprctl', 'eval',
                          'hl.dispatch(hl.dsp.focus({window="class:music-vis"}))'],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        pass


class MediaService:
    def __init__(self, player):
        self.player = player
        self.connection = None
        self.registrations = []
        self.ready = threading.Event()
        self.loop = GLib.MainLoop()
        self.last_properties = {}
        self.pending = False
        self.seek_pending = False
        self.pending_lock = threading.Lock()
        self.closed = False
        self.owner = Gio.bus_own_name(Gio.BusType.SESSION, ROOT + '.serena',
                                     Gio.BusNameOwnerFlags.NONE, self.acquired,
                                     lambda *args: self.ready.set(), self.lost)
        self.thread = threading.Thread(target=self.loop.run, daemon=True)
        self.thread.start()
        self.player.listeners.append(self.notify)

    def acquired(self, connection, name):
        self.connection = connection
        for interface in Gio.DBusNodeInfo.new_for_xml(XML).interfaces:
            self.registrations.append(connection.register_object(
                OBJECT_PATH, interface, self.method, self.get_property, self.set_property))
        self.notify()

    def lost(self, *args):
        if not self.closed:
            self.player.notice = 'Desktop media controls are unavailable'
        self.ready.set()

    def properties(self, interface):
        V = GLib.Variant
        if interface == ROOT:
            return {'CanQuit': V('b', True), 'CanRaise': V('b', True),
                    'HasTrackList': V('b', False), 'Identity': V('s', 'Serena Music'),
                    'DesktopEntry': V('s', 'serena-player'),
                    'SupportedUriSchemes': V('as', ['file']),
                    'SupportedMimeTypes': V('as', ['audio/mp4', 'audio/mpeg', 'audio/flac',
                                                  'audio/ogg', 'audio/opus', 'audio/wav'])}
        with self.player.lock:
            p = self.player
            track = p.track
            metadata = {}
            if track:
                metadata = {'mpris:trackid': V('o', track.track_id),
                            'mpris:length': V('x', round(p.duration * 1_000_000)),
                            'xesam:title': V('s', track.title),
                            'xesam:artist': V('as', [a.strip() for a in track.artist.split(',') if a.strip()]),
                            'xesam:album': V('s', track.album),
                            'xesam:url': V('s', track.path.as_uri())}
            return {'PlaybackStatus': V('s', p.status), 'LoopStatus': V('s', p.loop),
                    'Rate': V('d', 1.0), 'Shuffle': V('b', p.shuffled),
                    'Metadata': V('a{sv}', metadata), 'Volume': V('d', p.volume / 100),
                    'Position': V('x', round(p.position * 1_000_000)),
                    'MinimumRate': V('d', 1.0), 'MaximumRate': V('d', 1.0),
                    'CanGoNext': V('b', bool(p.order)), 'CanGoPrevious': V('b', bool(p.order)),
                    'CanPlay': V('b', bool(p.order)), 'CanPause': V('b', bool(track)),
                    'CanSeek': V('b', p.status != 'Stopped'), 'CanControl': V('b', True)}

    def get_property(self, connection, sender, path, interface, name):
        return self.properties(interface).get(name)

    def set_property(self, connection, sender, path, interface, name, value):
        if interface != PLAYER:
            return False
        value = value.unpack()
        if name == 'Volume':
            self.player.set_volume(value * 100)
        elif name == 'Shuffle':
            if value != self.player.shuffled:
                self.player.shuffle(value)
        elif name == 'LoopStatus' and value in ('None', 'All', 'Track'):
            with self.player.lock:
                self.player.loop = value
            self.player.notify()
        elif name == 'Rate' and value == 1.0:
            pass
        else:
            return False
        return True

    def method(self, connection, sender, path, interface, name, parameters, invocation):
        p = self.player
        args = parameters.unpack()
        try:
            actions = {'Next': p.next, 'Previous': p.previous, 'Pause': p.pause,
                       'PlayPause': p.toggle, 'Play': p.resume, 'Stop': p.stop}
            if interface == ROOT and name == 'Raise':
                raise_window()
            elif interface == ROOT and name == 'Quit':
                p.exit_requested = True
            elif interface == PLAYER and name in actions:
                actions[name]()
            elif interface == PLAYER and name == 'Seek':
                p.seek(args[0] / 1_000_000)
            elif interface == PLAYER and name == 'SetPosition':
                with p.lock:
                    if p.track and p.track.track_id == args[0] and args[1] >= 0:
                        p.seek(args[1] / 1_000_000, absolute=True)
            elif interface == PLAYER and name == 'OpenUri':
                uri = urlparse(args[0])
                local = str(Path(unquote(uri.path)).resolve())
                if uri.scheme != 'file' or uri.netloc not in ('', 'localhost') or local not in p.order:
                    raise ValueError('Choose a file from the local music library')
                p.play(local)
            else:
                raise ValueError('Unsupported media command')
            invocation.return_value(None)
        except Exception as error:
            invocation.return_dbus_error('org.freedesktop.DBus.Error.InvalidArgs', str(error))

    def notify(self, seeked=False):
        if self.closed:
            return
        with self.pending_lock:
            self.seek_pending |= seeked
            if self.pending:
                return
            self.pending = True
        GLib.idle_add(self.emit)

    def emit(self):
        with self.pending_lock:
            self.pending = False
            seeked = self.seek_pending
            self.seek_pending = False
        if self.closed or self.connection is None:
            return False
        properties = self.properties(PLAYER)
        changed = {k: v for k, v in properties.items()
                   if k != 'Position' and self.last_properties.get(k) != v}
        if changed:
            self.connection.emit_signal(None, OBJECT_PATH, 'org.freedesktop.DBus.Properties',
                                        'PropertiesChanged', GLib.Variant('(sa{sv}as)', (PLAYER, changed, [])))
            self.last_properties = properties
        if seeked:
            self.connection.emit_signal(None, OBJECT_PATH, PLAYER, 'Seeked',
                                        GLib.Variant('(x)', (round(self.player.position * 1_000_000),)))
        return False

    def close(self):
        self.closed = True
        if self.notify in self.player.listeners:
            self.player.listeners.remove(self.notify)
        Gio.bus_unown_name(self.owner)
        if self.connection:
            for registration in self.registrations:
                self.connection.unregister_object(registration)
        self.loop.quit()
        self.thread.join(timeout=1)
