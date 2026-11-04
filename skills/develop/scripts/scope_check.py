#!/usr/bin/env python3
"""Mechanical scope check of the working tree against the approved brief.

Usage:
  scope_check.py --snapshot [--repo DIR]            record files already dirty
  scope_check.py [--brief PATH] [--base REF] [--repo DIR] [--files]

Run --snapshot once, right before implementation starts, so edits that existed
before the pipeline are not blamed on it. The check then prints a compact report:
files outside the brief, removed/replaced lines, renames, formatting-only edits,
brief items nothing changed for, and new declarations to review.

Exit codes: 0 clean, 1 findings, 2 cannot run (caller should fall back to the
diff-auditor agent). Standard library only.
"""
import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import devconfig  # noqa: E402

EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
PIPE_DIR = ".dev-pipeline"
MAX_ITEMS = 40
DECL_RE = re.compile(
    r"^\s*(public|private|protected|internal|static|async|def|class|function|"
    r"export|interface|enum|record|struct|trait|fn|func)\b"
)
HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
BLOCK_COMMENTS = (("/*", "*/"), ('"""', '"""'), ("'''", "'''"), ("<!--", "-->"))
PREPROCESSOR_RE = re.compile(
    r"^#\s*(!|include|define|undef|if|ifdef|ifndef|else|elif|endif|region|endregion|"
    r"pragma|nullable|using|error|warning|line)\b"
)
DOC_EXTS = (".md", ".markdown", ".txt", ".rst", ".json", ".csv", ".lock")


class CannotRun(Exception):
    pass


def git(args, cwd):
    try:
        p = subprocess.run(
            ["git", "-c", "core.quotepath=false"] + args,
            cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
    except FileNotFoundError:
        raise CannotRun("git is not installed")
    if p.returncode != 0:
        raise CannotRun(p.stderr.strip() or "git command failed")
    return p.stdout


def is_line_comment(s):
    return s.startswith(("//", "--")) or (s.startswith("#") and not PREPROCESSOR_RE.match(s))


def long_comments(rows, max_lines):
    """rows: [(line_no, text)] of added lines. Return [(start, length, first_text)]
    for runs of consecutive comment lines longer than max_lines."""
    found, run, closer, prev = [], [], None, None

    def flush():
        if len(run) > max_lines:
            found.append((run[0][0], len(run), run[0][1]))
        run.clear()

    for ln, text in rows:
        s = text.strip()
        if prev is not None and ln != prev + 1 and closer is None:
            flush()
        prev = ln
        if closer:
            run.append((ln, s))
            if closer in s:
                closer = None
            continue
        opener = next((b for b in BLOCK_COMMENTS if s.startswith(b[0])), None)
        if opener:
            if s.find(opener[1], len(opener[0])) == -1:
                closer = opener[1]
            run.append((ln, s))
        elif is_line_comment(s):
            run.append((ln, s))
        else:
            flush()
    flush()
    return found


def short(text, n=110):
    text = text.strip()
    return text if len(text) <= n else text[: n - 3] + "..."


def to_repo_rel(entry, cwd, top):
    entry = entry.strip().strip("`").strip()
    if not entry:
        return ""
    absolute = os.path.normpath(os.path.join(cwd, entry))
    rel = os.path.relpath(absolute, top).replace("\\", "/")
    return rel + "/" if entry.endswith(("/", "\\")) and not rel.endswith("/") else rel


# ---------------------------------------------------------------- brief parsing
def sections(text):
    out, key, buf = {}, None, []
    for line in text.splitlines():
        m = re.match(r"^##\s+(.*)", line)
        if m:
            if key is not None:
                out[key] = buf
            key, buf = m.group(1).strip().lower(), []
        elif key is not None:
            buf.append(line)
    if key is not None:
        out[key] = buf
    return out


def find_section(secs, prefix):
    for k, v in secs.items():
        if k.startswith(prefix):
            return v
    return []


def parse_numbers(cell):
    nums = set()
    for a, b in re.findall(r"(\d+)(?:\s*-\s*(\d+))?", cell):
        lo, hi = int(a), int(b) if b else int(a)
        nums.update(range(lo, hi + 1))
    return nums


def parse_brief(path, cwd, top):
    with open(path, encoding="utf-8", errors="replace") as fh:
        secs = sections(fh.read())

    items = {}
    for line in find_section(secs, "in scope"):
        m = re.match(r"^\s*(\d+)[.)]\s+(.*)", line)
        if m:
            items[int(m.group(1))] = m.group(2).strip()

    units = []  # (name, [file patterns], {item numbers})
    for line in find_section(secs, "work units"):
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3 or re.fullmatch(r"[-:\s]*", "".join(cells)) or cells[0].lower() == "unit":
            continue
        files = [to_repo_rel(f, cwd, top) for f in re.split(r"<br\s*/?>|[,;]", cells[1])]
        files = [f for f in files if f]
        if files:
            units.append((cells[0], files, parse_numbers(cells[2])))

    authorised = {}  # repo-relative file -> list of (lo, hi) line ranges, or None for any line
    for line in find_section(secs, "authorised replacements"):
        m = re.search(r"`([^`]+)`", line)
        if not m:
            continue
        lines_m = re.search(r":(\d+)(?:-(\d+))?$", m.group(1))
        rel = to_repo_rel(re.sub(r":\d+(-\d+)?$", "", m.group(1)), cwd, top)
        if lines_m:
            lo = int(lines_m.group(1))
            rng = (lo, int(lines_m.group(2) or lo))
            if authorised.get(rel, []) is not None:
                authorised.setdefault(rel, []).append(rng)
        else:
            authorised[rel] = None
    return items, units, authorised


def removal_authorised(authorised, path, start, count):
    """A removal is authorised only if it overlaps a line range the brief cites."""
    if path not in authorised:
        return False
    ranges = authorised[path]
    if ranges is None:
        return True
    end = start + max(count, 1) - 1
    return any(start <= hi and end >= lo for lo, hi in ranges)


def matches(path, patterns):
    for pat in patterns:
        if path == pat or fnmatch.fnmatch(path, pat) or (pat.endswith("/") and path.startswith(pat)):
            return True
    return False


# -------------------------------------------------------------------- git state
def base_ref(cwd, wanted):
    if wanted:
        return wanted
    try:
        git(["rev-parse", "--verify", "HEAD"], cwd)
        return "HEAD"
    except CannotRun:
        return EMPTY_TREE


def untracked(cwd):
    return [p for p in git(["ls-files", "--others", "--exclude-standard"], cwd).splitlines() if p]


def changed_files(cwd, base):
    """Return list of (status, path, old_path) for tracked changes plus untracked files."""
    result = []
    for line in git(["diff", "--name-status", "-M", base], cwd).splitlines():
        parts = line.split("\t")
        status = parts[0][0]
        if status == "R" and len(parts) >= 3:
            result.append(("R", parts[2], parts[1]))
        elif len(parts) >= 2:
            result.append((status, parts[1], None))
    result += [("A", p, None) for p in untracked(cwd)]
    return [r for r in result if not r[1].startswith(PIPE_DIR + "/")]


def numstat(cwd, base, ignore_ws):
    args = ["diff", "--numstat", "-M"] + (["-w", "--ignore-blank-lines"] if ignore_ws else []) + [base]
    out = {}
    for line in git(args, cwd).splitlines():
        a, d, p = line.split("\t", 2)
        if "=>" in p:  # rename notation
            p = re.sub(r"\{.*? => (.*?)\}", r"\1", p).split(" => ")[-1]
        out[p] = (0 if a == "-" else int(a), 0 if d == "-" else int(d))
    return out


def file_hash(cwd, path):
    full = os.path.join(cwd, path)
    if not os.path.exists(full):
        return "DELETED"
    return git(["hash-object", "--", path], cwd).strip()


def parse_hunks(cwd, base):
    """Yield dicts: file, old_start, removed[], added[(line_no, text)]."""
    hunks, cur_file, hunk, new_ln = [], None, None, 0
    for line in git(["diff", "-U0", "-M", base], cwd).splitlines():
        if line.startswith("--- "):
            prev = line[4:]
            cur_file = prev[2:] if prev.startswith("a/") else None
        elif line.startswith("+++ "):
            nxt = line[4:]
            if nxt.startswith("b/"):
                cur_file = nxt[2:]
        elif line.startswith("@@"):
            m = HUNK_RE.match(line)
            if not m or cur_file is None:
                continue
            hunk = {"file": cur_file, "old_start": int(m.group(1)), "removed": [], "added": []}
            new_ln = int(m.group(3))
            hunks.append(hunk)
        elif hunk is not None and line.startswith("-"):
            hunk["removed"].append(line[1:])
        elif hunk is not None and line.startswith("+"):
            hunk["added"].append((new_ln, line[1:]))
            new_ln += 1
    return hunks


# ------------------------------------------------------------------- snapshot
def snapshot(cwd, top):
    base = base_ref(cwd, None)
    paths = {p for _, p, _ in changed_files(top, base)}
    data = {"files": {p: file_hash(top, p) for p in sorted(paths)}}
    os.makedirs(os.path.join(top, PIPE_DIR), exist_ok=True)
    with open(os.path.join(top, PIPE_DIR, "baseline.json"), "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    print(f"SNAPSHOT: {len(paths)} file(s) were already modified before implementation.")
    return 0


# ----------------------------------------------------------------------- check
def check(args, cwd, top):
    brief = args.brief or os.path.join(cwd, PIPE_DIR, "brief.md")
    if not os.path.isfile(brief):
        raise CannotRun(f"brief not found: {brief}")
    items, units, authorised = parse_brief(brief, cwd, top)
    base = base_ref(top, args.base)

    cfg, cfg_warnings = devconfig.load(cwd)
    if not os.path.isfile(os.path.join(cwd, devconfig.CONFIG_NAME)):
        cfg, cfg_warnings = devconfig.load(top)
    ignore = [to_repo_rel(g, cwd, top) for g in cfg["scope"]["ignore"]]
    protected = [to_repo_rel(g, cwd, top) for g in cfg["protected_paths"]]
    try:
        decl_re = re.compile(cfg["scope"]["declaration_regex"]) if cfg["scope"]["declaration_regex"] else DECL_RE
    except re.error as exc:
        cfg_warnings.append(f"scope.declaration_regex invalid ({exc}); using default")
        decl_re = DECL_RE

    baseline = {}
    bpath = os.path.join(top, PIPE_DIR, "baseline.json")
    if os.path.isfile(bpath):
        with open(bpath, encoding="utf-8") as fh:
            baseline = json.load(fh).get("files", {})

    memory_rel = to_repo_rel(cfg["context"]["memory_file"] or "", cwd, top)
    skipped, predirty, changes, ignored = [], [], [], 0
    for status, path, old in changed_files(top, base):
        if path == memory_rel:
            continue
        if ignore and matches(path, ignore):
            ignored += 1
            continue
        if path in baseline:
            if baseline[path] == file_hash(top, path):
                skipped.append(path)
                continue
            predirty.append(path)
        changes.append((status, path, old))
    changed_paths = [c[1] for c in changes]

    allowed = set(authorised) | {f for _, files, _ in units for f in files}
    out_of_scope = [p for p in changed_paths if not matches(p, allowed)] if allowed else []
    protected_hits = [p for p in changed_paths if protected and matches(p, protected)]

    renames = [f"{old} -> {path}" for s, path, old in changes if s == "R"]
    deleted = [p for s, p, _ in changes if s == "D"]

    plain, nows = numstat(top, base, False), numstat(top, base, True)
    formatting = [
        p for p in changed_paths
        if p in plain and sum(plain[p]) > 0 and sum(nows.get(p, (0, 0))) == 0
    ]

    hunks = [h for h in parse_hunks(top, base) if h["file"] in changed_paths]
    unauthorised, authorised_hits, declarations, long_cmts = [], [], [], []
    try:
        max_comment = int(cfg["comments"]["max_lines"] or 0)
    except (TypeError, ValueError):
        max_comment = 1
    for h in hunks:
        if max_comment and not h["file"].lower().endswith(DOC_EXTS):
            long_cmts += [f"{h['file']}:{st}  {n} lines: {short(t)}"
                          for st, n, t in long_comments(h["added"], max_comment)]
        real = [r for r in h["removed"] if r.strip()]
        if real and h["file"] not in formatting:
            kind = "replaced" if h["added"] else "removed"
            entry = f"{h['file']}:{h['old_start']}  {len(real)} line(s) {kind}: {short(real[0])}"
            ok = removal_authorised(authorised, h["file"], h["old_start"], len(h["removed"]))
            (authorised_hits if ok else unauthorised).append(entry)
        for ln, text in h["added"]:
            if decl_re.match(text):
                declarations.append(f"{h['file']}:{ln}  {short(text)}")
    for s, path, _ in changes:  # untracked files never appear in git diff
        if s == "A" and path not in plain:
            try:
                with open(os.path.join(top, path), encoding="utf-8") as fh:
                    rows = list(enumerate(fh.read().splitlines(), 1))
                for i, text in rows:
                    if decl_re.match(text):
                        declarations.append(f"{path}:{i}  {short(text)}")
                if max_comment and not path.lower().endswith(DOC_EXTS):
                    long_cmts += [f"{path}:{st}  {n} lines: {short(t)}"
                                  for st, n, t in long_comments(rows, max_comment)]
            except (OSError, UnicodeDecodeError):
                pass
    unauthorised += [f"{p}  file deleted" for p in deleted if authorised.get(p, [0]) is not None]

    not_covered = []
    if units and items:
        covered = set()
        for _, files, nums in units:
            if any(matches(p, files) for p in changed_paths):
                covered |= nums
        not_covered = [f"item {n}: {short(t, 80)}" for n, t in sorted(items.items()) if n not in covered]

    findings = bool(out_of_scope or unauthorised or renames or formatting or not_covered or protected_hits or long_cmts)

    def section(title, rows, note=""):
        print(f"{title}{note}")
        if not rows:
            print("  none")
        for r in rows[:MAX_ITEMS]:
            print(f"  - {r}")
        if len(rows) > MAX_ITEMS:
            print(f"  ... and {len(rows) - MAX_ITEMS} more")

    print(f"VERDICT: {'FINDINGS' if findings else 'CLEAN'}")
    print(f"files changed: {len(changed_paths)}  (brief units: {len(units)}, items: {len(items)})")
    for w in cfg_warnings:
        print(f"config warning: {w}")
    if args.files:
        section("CHANGED FILES", changed_paths)
    if not units:
        print("note: brief has no work-unit file list; scope and coverage checks skipped")
    section("OUT OF SCOPE FILES", out_of_scope)
    if protected:
        section("PROTECTED PATHS TOUCHED - needs explicit user approval", protected_hits)
    section("REMOVED / REPLACED LINES (file not authorised)", unauthorised)
    section("RENAMES", renames)
    section("FORMATTING-ONLY FILES", formatting)
    if max_comment:
        section(f"COMMENTS LONGER THAN {max_comment} LINE(S) - shorten", long_cmts)
    section("BRIEF ITEMS WITH NO CHANGE", not_covered)
    section("NEW DECLARATIONS - confirm each is in the brief", declarations)
    if authorised_hits:
        section("REMOVALS IN AUTHORISED FILES - confirm lines match the brief", authorised_hits)
    if predirty:
        section("EDITED BEFORE AND DURING PIPELINE - diff may include earlier edits", predirty)
    if skipped:
        print(f"ignored {len(skipped)} file(s) unchanged since snapshot")
    if ignored:
        print(f"ignored {ignored} file(s) matching scope.ignore in {devconfig.CONFIG_NAME}")
    return 1 if findings else 0


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--brief", help="path to brief (default .dev-pipeline/brief.md)")
    ap.add_argument("--base", help="git ref to compare against (default HEAD)")
    ap.add_argument("--repo", default=".", help="project directory (default .)")
    ap.add_argument("--snapshot", action="store_true", help="record already-modified files")
    ap.add_argument("--files", action="store_true", help="also list every changed file")
    args = ap.parse_args()
    cwd = os.path.abspath(args.repo)
    try:
        top = git(["rev-parse", "--show-toplevel"], cwd).strip()
        return snapshot(cwd, top) if args.snapshot else check(args, cwd, top)
    except CannotRun as exc:
        print(f"FALLBACK: scope_check cannot run ({exc}); use the diff-auditor agent instead.")
        return 2


if __name__ == "__main__":
    sys.exit(main())
