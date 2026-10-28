#!/usr/bin/env bash
# change_theme.sh — Shortcut script to change and synchronize Serena Rice themes.

SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do
    DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
    SOURCE="$(readlink "$SOURCE")"
    [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
done
SCRIPT_DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"

THEME_PY="$SCRIPT_DIR/theme_manager.py"
if [ ! -f "$THEME_PY" ]; then
    THEME_PY="$SCRIPT_DIR/scripts/theme_manager.py"
fi
if [ ! -f "$THEME_PY" ]; then
    THEME_PY="$HOME/.config/hypr/scripts/theme_manager.py"
fi

if [ -f "$THEME_PY" ]; then
    python3 "$THEME_PY" "$@"
else
    echo "Error: theme_manager.py not found!"
    exit 1
fi
