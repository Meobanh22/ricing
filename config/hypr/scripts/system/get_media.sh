#!/usr/bin/env bash
# get_media.sh — Wrapper executing get_media.py.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="$HOME/.config/hypr/scripts/system/get_media.py"
[ ! -f "$TARGET" ] && TARGET="$SCRIPT_DIR/get_media.py"
exec python3 "$TARGET"
