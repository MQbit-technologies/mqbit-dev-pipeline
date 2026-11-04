#!/usr/bin/env python3
"""Compact project memory with content fingerprints, so stale entries are found
without a model re-reading the code.

Usage (all accept --repo DIR and --file PATH):
  memory.py init
  memory.py status
  memory.py add --section map|conventions|decisions|gotchas --text "..." [--path P]
  memory.py refresh --paths A B ...
  memory.py prune

Map entries look like:  - `path` - what it is for <!--fp:1a2b3c4d-->
The fingerprint hashes the file (or every file under a directory). `status` compares it
with the code on disk: FRESH, STALE (changed since stamped) or MISSING (path gone).
The file location comes from `context.memory_file` in dev-pipeline.json.
Standard library only. Exit codes: 0 ok, 2 error.
"""
import argparse
import datetime
import hashlib
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import devconfig  # noqa: E402

SECTIONS = {"map": "Map", "conventions": "Conventions", "decisions": "Decisions", "gotchas": "Gotchas"}
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", "target", "bin", "obj", ".dev-pipeline"}
MAX_FILES = 3000
ENTRY_RE = re.compile(r"^- `([^`]+)`\s*(?:[-—–]\s*)?(.*?)\s*(?:<!--fp:([0-9a-f]+)-->)?\s*$")
TEMPLATE = """# Project memory
> Kept up to date by dev-pipeline. Facts only, one line each. Delete anything wrong.

## Map
<!-- - `path` - what it is for -->

## Conventions

## Decisions

## Gotchas
"""


def die(msg):
    print(f"ERROR: {msg}")
    sys.exit(2)


def list_files(root, rel):
    full = os.path.join(root, rel)
    if os.path.isfile(full):
        return [rel]
    if not os.path.isdir(full):
        return None
    try:
        out = subprocess.run(
            ["git", "ls-files", "-co", "--exclude-standard", "--", rel],
            cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        if out.returncode == 0:
            return sorted(p for p in out.stdout.splitlines() if p and os.path.isfile(os.path.join(root, p)))[:MAX_FILES]
    except OSError:
        pass
    files = []
    for dirpath, dirnames, names in os.walk(full):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        files += [os.path.relpath(os.path.join(dirpath, n), root).replace("\\", "/") for n in names]
        if len(files) > MAX_FILES:
            break
    return sorted(files)[:MAX_FILES]


def fingerprint(root, rel):
    """8-hex content fingerprint of a file or directory; None if the path is gone."""
    files = list_files(root, rel)
    if files is None:
        return None
    h = hashlib.sha1()
    for f in files:
        h.update(f.encode("utf-8") + b"\0")
        try:
            with open(os.path.join(root, f), "rb") as fh:
                h.update(hashlib.sha1(fh.read()).digest())
        except OSError:
            h.update(b"?")
    return h.hexdigest()[:8]


def locate(args):
    root = os.path.abspath(args.repo)
    cfg, warnings = devconfig.load(root)
    for w in warnings:
        print(f"config warning: {w}")
    rel = args.file or cfg["context"]["memory_file"] or devconfig.DEFAULTS["context"]["memory_file"]
    return root, cfg, os.path.join(root, rel), rel


def read_lines(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read().splitlines()


def write_lines(path, lines):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines).rstrip("\n") + "\n")


def section_range(lines, name):
    """Return (start, end) of body lines for '## name'; creates nothing."""
    start = None
    for i, line in enumerate(lines):
        if line.strip().lower() == f"## {name}".lower():
            start = i + 1
        elif start is not None and line.startswith("## "):
            return start, i
    return (start, len(lines)) if start is not None else (None, None)


def require_file(path):
    if not os.path.isfile(path):
        die(f"memory file not found: {path} (run: memory.py init)")


def cmd_init(args):
    root, cfg, path, rel = locate(args)
    if os.path.isfile(path):
        print(f"exists: {rel}")
        return 0
    write_lines(path, TEMPLATE.splitlines())
    print(f"created: {rel}")
    return 0


def cmd_status(args):
    root, cfg, path, rel = locate(args)
    if not os.path.isfile(path):
        print(f"MEMORY: none yet ({rel}); run memory.py init")
        return 0
    lines = read_lines(path)
    cap = int(cfg["context"]["max_memory_lines"] or 0)
    over = f"  OVER CAP - compress it" if cap and len(lines) > cap else ""
    print(f"MEMORY: {rel}  ({len(lines)} lines, cap {cap or 'none'}){over}")
    start, end = section_range(lines, "Map")
    fresh, stale, missing = 0, [], []
    for line in lines[start:end] if start is not None else []:
        m = ENTRY_RE.match(line)
        if not m:
            continue
        entry_path, _, fp = m.groups()
        now = fingerprint(root, entry_path)
        if now is None:
            missing.append(entry_path)
        elif fp and fp == now:
            fresh += 1
        else:
            stale.append(entry_path)
    print(f"map: {fresh + len(stale) + len(missing)} total - {fresh} fresh, {len(stale)} stale, {len(missing)} missing")
    if stale:
        print("STALE (re-verify before trusting):")
        for p in stale:
            print(f"  - {p}")
    if missing:
        print("MISSING (path gone; run prune):")
        for p in missing:
            print(f"  - {p}")
    for key in ("conventions", "decisions", "gotchas"):
        s, e = section_range(lines, SECTIONS[key])
        count = sum(1 for l in lines[s:e] if l.startswith("- ")) if s is not None else 0
        print(f"{key}: {count}")
    return 0


def cmd_add(args):
    root, cfg, path, rel = locate(args)
    if not os.path.isfile(path):
        write_lines(path, TEMPLATE.splitlines())
    lines = read_lines(path)
    name = SECTIONS[args.section]
    start, end = section_range(lines, name)
    if start is None:
        lines += ["", f"## {name}"]
        start = end = len(lines)
    text = " ".join(args.text.split())
    if args.section == "map":
        if not args.path:
            die("--path is required for the map section")
        rel_path = args.path.replace("\\", "/").strip("`")
        fp = fingerprint(root, rel_path)
        if fp is None:
            die(f"path does not exist: {rel_path}")
        new = f"- `{rel_path}` - {text} <!--fp:{fp}-->"
        for i in range(start, end):
            m = ENTRY_RE.match(lines[i])
            if m and m.group(1) == rel_path:
                lines[i] = new
                write_lines(path, lines)
                print(f"updated: {rel_path}")
                return 0
    else:
        stamp = datetime.date.today().isoformat() + " " if args.section == "decisions" else ""
        new = f"- {stamp}{text}"
        if any(l.endswith(text) for l in lines[start:end]):
            print("already recorded")
            return 0
    insert_at = end
    while insert_at > start and not lines[insert_at - 1].strip():
        insert_at -= 1
    lines.insert(insert_at, new)
    write_lines(path, lines)
    print(f"added to {name}")
    return 0


def cmd_refresh(args):
    root, cfg, path, rel = locate(args)
    require_file(path)
    lines = read_lines(path)
    start, end = section_range(lines, "Map")
    wanted = [p.replace("\\", "/") for p in args.paths]
    touched = 0
    for i in range(start or 0, end or 0):
        m = ENTRY_RE.match(lines[i])
        if not m:
            continue
        entry_path = m.group(1).rstrip("/")
        if any(p == entry_path or p.startswith(entry_path + "/") for p in wanted):
            fp = fingerprint(root, m.group(1))
            if fp:
                lines[i] = f"- `{m.group(1)}` - {m.group(2)} <!--fp:{fp}-->"
                touched += 1
    write_lines(path, lines)
    print(f"restamped {touched} map entr{'y' if touched == 1 else 'ies'}")
    return 0


def cmd_prune(args):
    root, cfg, path, rel = locate(args)
    require_file(path)
    lines = read_lines(path)
    start, end = section_range(lines, "Map")
    keep, dropped = [], []
    for i, line in enumerate(lines):
        m = ENTRY_RE.match(line) if start is not None and start <= i < end else None
        if m and fingerprint(root, m.group(1)) is None:
            dropped.append(m.group(1))
        else:
            keep.append(line)
    write_lines(path, keep)
    print(f"pruned {len(dropped)} entr{'y' if len(dropped) == 1 else 'ies'}" + "".join(f"\n  - {d}" for d in dropped))
    return 0


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=".", help="project directory (default .)")
    ap.add_argument("--file", help="memory file relative to --repo (default from config)")
    sub = ap.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    sub.add_parser("status")
    sub.add_parser("prune")
    a = sub.add_parser("add")
    a.add_argument("--section", required=True, choices=list(SECTIONS))
    a.add_argument("--text", required=True)
    a.add_argument("--path")
    r = sub.add_parser("refresh")
    r.add_argument("--paths", nargs="+", required=True)
    args = ap.parse_args()
    handler = {"init": cmd_init, "status": cmd_status, "add": cmd_add, "refresh": cmd_refresh, "prune": cmd_prune}
    return handler[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
