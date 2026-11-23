#!/usr/bin/env bash
# open_music_player.sh — Open the terminal music library.
set -euo pipefail
script_dir="$(dirname "$(readlink -f "$0")")"
if [[ -t 0 && -t 1 ]] || [[ "${1:-}" == '--help' ]] || [[ "${1:-}" == '--headless' ]]; then
    exec python3 "$script_dir/music.py" --mode library "$@"
fi
exec kitty --class music-vis \
    --override background_opacity=0.96 \
    python3 "$script_dir/music.py" --mode library "$@"
