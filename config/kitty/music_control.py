"""Allow music to change only its own background and padding."""

import math


def is_cmd_allowed(command, window, from_socket, extra_data):
    if from_socket or window is None or window.title not in ('Serena Music', 'Serena Music Focus'):
        return False
    payload = command.get('payload', {})
    # Omitting a match targets the requesting terminal; never allow another window.
    if any(key not in ('opacity', 'toggle', 'settings') for key in payload):
        return False
    if command.get('cmd') == 'set-background-opacity':
        value = payload.get('opacity')
        return (set(payload) <= {'opacity', 'toggle'} and type(value) in (float, int)
                and math.isfinite(value) and 0 <= value <= 1
                and type(payload.get('toggle', False)) is bool)
    if command.get('cmd') == 'set-spacing':
        settings = payload.get('settings')
        return (set(payload) == {'settings'} and isinstance(settings, dict) and bool(settings)
                and all(key in ('padding-left', 'padding-right', 'padding-top', 'padding-bottom')
                        and (value is None or type(value) in (int, float) and value == 0)
                        for key, value in settings.items()))
    return False
