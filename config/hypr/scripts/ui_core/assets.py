#!/usr/bin/env python3
# assets.py — Unified asset resolver for Hyprland widgets and popups.
# Resolves paths across repository structure, ~/.config, and asset subdirectories.

import os
import sys

_REPO_ROOT = None
_ASSET_CACHE = {}

def get_repo_root() -> str:
    """Finds the root directory of the dotfiles repository dynamically."""
    global _REPO_ROOT
    if _REPO_ROOT is not None:
        return _REPO_ROOT

    # Start from current file location
    curr = os.path.dirname(os.path.abspath(__file__))
    for _ in range(6):
        if os.path.exists(os.path.join(curr, ".git")) or os.path.exists(os.path.join(curr, "config", "theme", "tokens.json")):
            _REPO_ROOT = curr
            return _REPO_ROOT
        parent = os.path.dirname(curr)
        if parent == curr:
            break
        curr = parent

    # Fallback to current working directory or ~/custom
    cwd = os.getcwd()
    if os.path.exists(os.path.join(cwd, "config", "theme", "tokens.json")):
        _REPO_ROOT = cwd
        return _REPO_ROOT

    fallback = os.path.expanduser("~/custom")
    _REPO_ROOT = fallback if os.path.exists(fallback) else os.path.expanduser("~")
    return _REPO_ROOT


def resolve_asset(name_or_relpath: str) -> str:
    """
    Resolves an asset path gracefully with fallback searches and memoization.
    Supports filenames, relative paths, and canonical category lookups.
    """
    if not name_or_relpath:
        return ""

    if name_or_relpath in _ASSET_CACHE:
        return _ASSET_CACHE[name_or_relpath]

    # 1. Direct absolute path
    if os.path.isabs(name_or_relpath) and os.path.exists(name_or_relpath):
        _ASSET_CACHE[name_or_relpath] = name_or_relpath
        return name_or_relpath

    repo_root = get_repo_root()
    base_name = os.path.basename(name_or_relpath)
    clean_rel = name_or_relpath.lstrip("/")

    # 2. Check candidate locations
    candidates = [
        # Relative to repo root
        os.path.join(repo_root, clean_rel),
        os.path.join(repo_root, "config", "hypr", clean_rel),
        os.path.join(repo_root, "config", "hypr", "assets", base_name),
        os.path.join(repo_root, "assets", clean_rel),
        os.path.join(repo_root, "assets", base_name),
        # System ~/.config paths
        os.path.expanduser(f"~/.config/hypr/{clean_rel}"),
        os.path.expanduser(f"~/.config/hypr/assets/{base_name}"),
        os.path.expanduser(f"~/.config/hypr/{base_name}"),
        # Wallpapers directory
        os.path.expanduser(f"~/Pictures/wallpapers/{base_name}"),
    ]

    # 3. Check asset subcategories in repo
    subdirs = ["avatars", "banners", "icons", "illustrations", "pokemon", "wallpapers"]
    for sub in subdirs:
        candidates.append(os.path.join(repo_root, "assets", sub, base_name))
        candidates.append(os.path.expanduser(f"~/.config/hypr/assets/{sub}/{base_name}"))

    for path in candidates:
        if os.path.exists(path):
            _ASSET_CACHE[name_or_relpath] = path
            return path

    return ""
