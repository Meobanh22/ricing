#!/usr/bin/env python3
"""
Hyprland IPC Bridge for Lua Config Provider
Translates legacy hyprlang dispatch commands (e.g. 'dispatch workspace <id>')
into Hyprland Lua dispatcher syntax (e.g. "dispatch hl.dsp.focus({ workspace = <id> })").
This enables native Waybar workspace switching and legacy hyprctl compatibility.
"""

import os
import re
import socket
import select
import signal
import sys
import threading
import time

SIGNATURE = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE")
if not SIGNATURE:
    print("[bridge] Error: HYPRLAND_INSTANCE_SIGNATURE is not set.", file=sys.stderr)
    sys.exit(1)

XDG_RUNTIME_DIR = os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
HYPR_DIR = os.path.join(XDG_RUNTIME_DIR, "hypr", SIGNATURE)
REAL_SOCK_PATH = os.path.join(HYPR_DIR, ".socket.real.sock")
PROXY_SOCK_PATH = os.path.join(HYPR_DIR, ".socket.sock")

running = True

def translate_command(cmd_bytes: bytes) -> bytes:
    try:
        cmd_str = cmd_bytes.decode('utf-8', errors='replace').strip()
    except Exception:
        return cmd_bytes

    rest = cmd_str
    if rest.startswith('/'):
        rest = rest[1:]

    if rest.startswith('dispatch '):
        dispatch_args = rest[len('dispatch '):].strip()
        if 'hl.dsp' in dispatch_args or dispatch_args.startswith('('):
            return cmd_bytes

        # Focus workspace: workspace 1, workspace name:2, focusworkspaceoncurrentmonitor 1
        m_ws = re.match(r'^(?:workspace|focusworkspaceoncurrentmonitor)\s+(?:name:)?(.+)$', dispatch_args)
        if m_ws:
            target = m_ws.group(1).strip()
            if target.isdigit():
                return f'dispatch hl.dsp.focus({{ workspace = {target} }})'.encode('utf-8')
            else:
                return f'dispatch hl.dsp.focus({{ workspace = "{target}" }})'.encode('utf-8')

        # Move to workspace: movetoworkspace 1, movetoworkspacesilent 1
        m_move = re.match(r'^movetoworkspace(?:silent)?\s+(?:name:)?(.+)$', dispatch_args)
        if m_move:
            target = m_move.group(1).strip()
            silent = "silent" in dispatch_args
            silent_str = ", silent = true" if silent else ""
            if target.isdigit():
                return f'dispatch hl.dsp.window.move({{ workspace = {target}{silent_str} }})'.encode('utf-8')
            else:
                return f'dispatch hl.dsp.window.move({{ workspace = "{target}"{silent_str} }})'.encode('utf-8')

        # Window controls
        if dispatch_args == "killactive":
            return b"dispatch hl.dsp.window.close()"
        if dispatch_args == "togglefloating":
            return b'dispatch hl.dsp.window.float({ action = "toggle" })'
        if dispatch_args.startswith("fullscreen"):
            return b'dispatch hl.dsp.window.fullscreen()'
        if dispatch_args.startswith("exit"):
            return b"dispatch hl.dsp.exit()"
        if dispatch_args.startswith("exec "):
            exec_target = dispatch_args[len("exec "):].strip()
            escaped = exec_target.replace('\\', '\\\\').replace('"', '\\"')
            return f'dispatch hl.dsp.exec_cmd("{escaped}")'.encode('utf-8')

    return cmd_bytes

def handle_client(client_conn: socket.socket):
    try:
        data = client_conn.recv(65536)
        if not data:
            client_conn.close()
            return
        
        translated = translate_command(data)
        
        # Forward to real Hyprland socket
        fwd_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        fwd_sock.connect(REAL_SOCK_PATH)
        fwd_sock.sendall(translated)
        
        while True:
            chunk = fwd_sock.recv(65536)
            if not chunk:
                break
            client_conn.sendall(chunk)
            
        fwd_sock.close()
    except Exception as e:
        pass
    finally:
        try:
            client_conn.close()
        except Exception:
            pass

def cleanup(signum=None, frame=None):
    global running
    running = False
    print("[bridge] Shutting down, restoring original socket...")
    try:
        if os.path.exists(PROXY_SOCK_PATH):
            os.remove(PROXY_SOCK_PATH)
        if os.path.exists(REAL_SOCK_PATH):
            os.rename(REAL_SOCK_PATH, PROXY_SOCK_PATH)
    except Exception as e:
        print(f"[bridge] Cleanup error: {e}", file=sys.stderr)
    sys.exit(0)

def main():
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    signal.signal(signal.SIGHUP, cleanup)

    if not os.path.exists(REAL_SOCK_PATH):
        if not os.path.exists(PROXY_SOCK_PATH):
            print(f"[bridge] Waiting for Hyprland socket at {PROXY_SOCK_PATH}...")
            for _ in range(50):
                if os.path.exists(PROXY_SOCK_PATH):
                    break
                time.sleep(0.1)
        if not os.path.exists(PROXY_SOCK_PATH):
            print(f"[bridge] Error: Socket {PROXY_SOCK_PATH} not found.", file=sys.stderr)
            sys.exit(1)
        # Rename original socket to real socket
        os.rename(PROXY_SOCK_PATH, REAL_SOCK_PATH)
    elif os.path.exists(PROXY_SOCK_PATH):
        # A previous proxy socket was left over
        try:
            os.remove(PROXY_SOCK_PATH)
        except OSError:
            pass

    server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server_sock.bind(PROXY_SOCK_PATH)
    server_sock.listen(64)
    # Give proper permissions so all user tools can connect
    os.chmod(PROXY_SOCK_PATH, 0o700)
    print(f"[bridge] Hyprland IPC bridge active on {PROXY_SOCK_PATH} -> {REAL_SOCK_PATH}")

    while running:
        try:
            r, _, _ = select.select([server_sock], [], [], 1.0)
            if r:
                conn, _ = server_sock.accept()
                t = threading.Thread(target=handle_client, args=(conn,), daemon=True)
                t.start()
        except (select.error, socket.error):
            if not running:
                break
        except Exception:
            pass

    cleanup()

if __name__ == "__main__":
    main()
