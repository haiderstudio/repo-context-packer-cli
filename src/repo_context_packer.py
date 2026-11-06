#!/usr/bin/env python3
"""Pack selected repo files into one AI-readable text file.

Run: python3 src/repo_context_packer.py <root> <path>... [-o output.txt]

Only the files and folders you name are packed, in the order you name
them. Nothing else is read. Secrets and build outputs are left out even
when you name them by mistake. The pack goes to standard output unless
-o is given, and -o must point outside the packed root, so the tool
never writes into the repo it packs. It sends nothing anywhere.

Python standard library only.
"""

import argparse
import fnmatch
import os
import sys
from pathlib import Path

VERSION = "1.0.0"

# Files that are never packed, even when named on the command line.
# A file is a possible secret if its name matches one of these.
SECRET_PATTERNS = (
    ".env",
    ".env.*",
    "*.pem",
    "*.key",
    "*.p12",
    "*.pfx",
    "id_rsa*",
    "id_ed25519*",
    "id_ecdsa*",
    "id_dsa*",
    "*credentials*",
    "*secret*",
)

# Folders that are never packed, even when named on the command line.
EXCLUDED_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    ".venv",
    "venv",
    ".pytest_cache",
    ".tox",
    ".eggs",
}

MAX_FILE_BYTES = 1_000_000


def is_secret(path):
    """True if the file name looks like a secret file."""
    name = path.name.lower()
    return any(fnmatch.fnmatchcase(name, pattern) for pattern in SECRET_PATTERNS)


def is_excluded_dir(path):
    """True if any part of the path is a build-output or VCS folder."""
    return any(part in EXCLUDED_DIRS or part.endswith(".egg-info")
               for part in path.parts)


def looks_binary(data):
    """True if the bytes look like a binary file, not text."""
    if b"\x00" in data[:8192]:
        return True
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return True
    return False


def collect(root, paths, include):
    """Return (files, skipped) for the named paths under root.

    files: list of (relative path, absolute path), in the order the
    user named them, files inside a named folder in sorted order.
    skipped: list of (relative path, reason) for files left out.
    """
    files = []
    skipped = []
    seen = set()

    def add_file(abs_path, rel, named):
        if rel in seen:
            return
        if is_secret(abs_path):
            skipped.append((str(rel), "secret file"))
            return
        if is_excluded_dir(rel):
            skipped.append((str(rel), "build output"))
            return
        if not named and rel.name.startswith("."):
            skipped.append((str(rel), "hidden file"))
            return
        if include and not any(fnmatch.fnmatchcase(str(rel), pat)
                               for pat in include):
            skipped.append((str(rel), "did not match --include"))
            return
        try:
            data = abs_path.read_bytes()
        except OSError as exc:
            skipped.append((str(rel), "unreadable: %s" % exc))
            return
        if len(data) > MAX_FILE_BYTES:
            skipped.append((str(rel), "over 1 MB"))
            return
        if looks_binary(data):
            skipped.append((str(rel), "binary file"))
            return
        seen.add(rel)
        files.append((rel, abs_path))

    def walk_dir(abs_dir, rel_dir):
        try:
            entries = sorted(abs_dir.iterdir(), key=lambda p: p.name)
        except OSError as exc:
            skipped.append((str(rel_dir), "unreadable: %s" % exc))
            return
        for entry in entries:
            rel = rel_dir / entry.name
            if entry.is_dir():
                if is_excluded_dir(rel):
                    skipped.append((str(rel), "build output"))
                    continue
                walk_dir(entry, rel)
            elif entry.is_file():
                add_file(entry, rel, named=False)

    for raw in paths:
        rel = Path(raw)
        if rel.is_absolute():
            raise ValueError("path must be relative to the root: %s" % raw)
        abs_path = root / rel
        if not abs_path.exists():
            raise ValueError("no such file or folder: %s" % raw)
        if abs_path.is_dir():
            if is_excluded_dir(rel):
                skipped.append((str(rel), "build output"))
                continue
            walk_dir(abs_path, rel)
        else:
            add_file(abs_path, rel, named=True)

    return files, skipped


def build_pack(root, files):
    """Build the plain-text pack. Returns (text, total_lines)."""
    lines = [
        "# Repo context pack",
        "# Root: %s" % root.name,
        "# Files: %d" % len(files),
    ]
    bodies = []
    total_lines = 0
    for rel, abs_path in files:
        text = abs_path.read_text(encoding="utf-8")
        bodies.append((str(rel), text))
        total_lines += text.count("\n") + (1 if text and not text.endswith("\n") else 0)
    lines.append("# Lines: %d" % total_lines)
    lines.append("# Note: secrets and build outputs were left out.")
    lines.append("## Files")
    for rel, _ in files:
        lines.append(str(rel))
    out = "\n".join(lines) + "\n"
    for rel, text in bodies:
        out += "\n==== %s ====\n" % rel
        out += text
        if not text.endswith("\n"):
            out += "\n"
    return out, total_lines


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="repo_context_packer",
        description="Pack selected repo files into one AI-readable text file.")
    parser.add_argument("root", help="repo folder to pack from")
    parser.add_argument("paths", nargs="+",
                        help="files or folders to pack, relative to root")
    parser.add_argument("-o", "--output", default=None,
                        help="write the pack to this file (must be outside root)")
    parser.add_argument("--list", action="store_true",
                        help="only list the files that would be packed")
    parser.add_argument("--include", action="append", default=[],
                        help="only pack files matching this glob (repeatable)")
    parser.add_argument("--version", action="version", version=VERSION)
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    if not root.is_dir():
        print("error: root is not a folder: %s" % args.root, file=sys.stderr)
        return 2

    try:
        files, skipped = collect(root, args.paths, args.include)
    except ValueError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2

    if args.list:
        for rel, _ in files:
            print(rel)
        for rel, reason in skipped:
            print("skipped %s (%s)" % (rel, reason), file=sys.stderr)
        return 0 if files else 1

    if not files:
        print("error: nothing to pack", file=sys.stderr)
        for rel, reason in skipped:
            print("skipped %s (%s)" % (rel, reason), file=sys.stderr)
        return 1

    pack, total_lines = build_pack(root, files)

    if args.output:
        out_path = Path(args.output).resolve()
        try:
            out_path.relative_to(root)
        except ValueError:
            pass
        else:
            print("error: output must be outside the packed root: %s"
                  % args.output, file=sys.stderr)
            return 2
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(pack, encoding="utf-8")
        print("packed %d file(s), %d lines into %s"
              % (len(files), total_lines, args.output), file=sys.stderr)
    else:
        sys.stdout.write(pack)

    for rel, reason in skipped:
        print("skipped %s (%s)" % (rel, reason), file=sys.stderr)
    if not args.output:
        print("packed %d file(s), %d lines"
              % (len(files), total_lines), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
