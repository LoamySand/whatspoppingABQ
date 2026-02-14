#!/usr/bin/env python3
"""
Remove emoji characters from text files in the repo.

Creates a backup of any modified file with a `.bak` suffix.

Usage:
  python scripts/remove_emojis.py [--dry-run] [--root PATH]

By default runs in-place under repository root.
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Iterable, Tuple


EMOJI_RANGES = [
    (0x1F300, 0x1F5FF),
    (0x1F600, 0x1F64F),
    (0x1F680, 0x1F6FF),
    (0x1F700, 0x1F77F),
    (0x1F780, 0x1F7FF),
    (0x1F900, 0x1F9FF),
    (0x1FA70, 0x1FAFF),
    (0x2600, 0x26FF),
    (0x2700, 0x27BF),
    (0x1F1E6, 0x1F1FF),
]
VARIATION_SELECTOR = 0xFE0F


def is_emoji_char(ch: str) -> bool:
    if not ch:
        return False
    o = ord(ch)
    if o == VARIATION_SELECTOR:
        return True
    for a, b in EMOJI_RANGES:
        if a <= o <= b:
            return True
    return False


def remove_emojis_from_text(text: str) -> Tuple[str, int]:
    out_chars = []
    removed = 0
    for ch in text:
        if is_emoji_char(ch):
            removed += 1
            continue
        out_chars.append(ch)
    return ("".join(out_chars), removed)


def iter_files(root: str) -> Iterable[str]:
    skip_dirs = {".git", "__pycache__", "node_modules", "venv", "env"}
    for dirpath, dirnames, filenames in os.walk(root):
        # modify dirnames in-place to skip
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        for fn in filenames:
            yield os.path.join(dirpath, fn)


def should_process_file(path: str) -> bool:
    # Skip typical binary extensions
    binary_exts = {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".ico",
        ".exe",
        ".dll",
        ".so",
        ".pyc",
        ".db",
        ".sqlite",
        ".zip",
        ".tar",
        ".gz",
        ".class",
        ".jar",
    }
    _, ext = os.path.splitext(path.lower())
    if ext in binary_exts:
        return False
    return True


def process_file(path: str, dry_run: bool = True) -> Tuple[int, bool]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = f.read()
    except Exception:
        return (0, False)
    new_data, removed = remove_emojis_from_text(data)
    if removed == 0:
        return (0, False)
    if dry_run:
        return (removed, True)
    # backup
    bak = path + ".bak"
    try:
        os.replace(path, bak)
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_data)
    except Exception:
        # attempt to restore
        if os.path.exists(bak):
            os.replace(bak, path)
        return (0, False)
    return (removed, True)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Remove emoji characters from files in a repo.")
    p.add_argument("--root", default=".", help="Root directory to scan")
    p.add_argument("--dry-run", action="store_true", help="Only report changes")
    args = p.parse_args(argv)

    root = os.path.abspath(args.root)
    total_files = 0
    changed_files = 0
    total_removed = 0
    for path in iter_files(root):
        if not should_process_file(path):
            continue
        removed, touched = process_file(path, dry_run=args.dry_run)
        total_files += 1
        if touched:
            changed_files += 1
            total_removed += removed
            print(f"Modified: {path} — removed {removed} emoji chars")

    print("---")
    print(f"Scanned files: {total_files}")
    print(f"Files changed: {changed_files}")
    print(f"Total emoji characters removed: {total_removed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
