#!/usr/bin/env python3
"""
ask-the-group — v0.1 - initial submission(script under construction)

Reads a folder of .txt(or .md) files and prints what's inside.
The starting point for a small offline helper for volunteer groups and similar.

Usage:
    python ask_the_group.py <folder>
"""

import os
import sys


def find_text_files(folder):
    if not os.path.isdir(folder):
        sys.exit(f"ERROR: Not a folder: {folder}")

    files = []
    for dirpath, dirnames, filenames in os.walk(folder):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for name in sorted(filenames):
            if name.lower().endswith((".txt", ".md")):
                files.append(os.path.join(dirpath, name))
    return files


def read_lines(path):
    try:
        with open(path, errors="replace", encoding="utf-8") as f:
            return [ln.strip() for ln in f if ln.strip()]
    except OSError as e:
        print(f"  (Error: Could not read: {e})")
        return []


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    folder = sys.argv[1]
    files = find_text_files(folder)

    if not files:
        sys.exit(f"No .txt or .md files found in folder:{folder}")

    print(f"Found {len(files)} file(s) in folder:{folder}:")
    print()

    total_lines = 0
    for path in files:
        rel = os.path.relpath(path, folder)
        lines = read_lines(path)
        total_lines += len(lines)
        print(f"  {rel}  ({len(lines)} lines)")
        for line in lines[:4]:
            print(f"      {line}")
        if len(lines) > 4:
            print(f"      ... and {len(lines) - 4} more")
        print()

    print(f"Total: Found {total_lines} lines across {len(files)} file(s).")
    print("Coming soon: this script will become a question-answering tool without the use of AI.")


if __name__ == "__main__":
    main()

##################################################################################################
