#!/usr/bin/env python3
"""Run a build/test command and print only what matters.

Usage:
  run_checks.py --task test|build   command from dev-pipeline.json, else auto-detected
  run_checks.py --cmd "<command>"   explicit command
  run_checks.py --detect            print detected build/test commands as JSON
  Options: [--timeout SEC] [--cwd DIR] [--tail 8] [--max-lines 60]

On success: one PASS line plus the last few output lines (usually the summary).
On failure: the failure/error lines with one line of context, then the output tail.
The full output is always saved to .dev-pipeline/last-run.log, so nothing is lost.

Exit code: the command's own exit code; 124 on timeout; 2 if it could not start.
Standard library only.
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import devconfig  # noqa: E402

ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
FAIL_RE = re.compile(
    r"(\bFAIL(ED)?\b|\bERROR\b|\berror\b[: ]|\bfailed\b|Exception|Traceback|panic:|"
    r"AssertionError|\bassert(ion)?\b.*\b(fail|expected)|✗|✖|×|\bnot ok\b)",
)
WARN_RE = re.compile(r"\bwarning\b", re.IGNORECASE)


def short(text, n=200):
    return text if len(text) <= n else text[: n - 3] + "..."


def _has(root, *names):
    return any(os.path.exists(os.path.join(root, n)) for n in names)


def _read_json(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def _make_has_target(root, target):
    try:
        with open(os.path.join(root, "Makefile"), encoding="utf-8", errors="replace") as fh:
            return re.search(rf"^{target}\s*:", fh.read(), re.MULTILINE) is not None
    except OSError:
        return False


def detect(root):
    """Best-effort list of {stack, build, test} guesses from marker files."""
    found = []
    if _has(root, "package.json"):
        scripts = _read_json(os.path.join(root, "package.json")).get("scripts", {})
        pm = "pnpm" if _has(root, "pnpm-lock.yaml") else "yarn" if _has(root, "yarn.lock") \
            else "bun" if _has(root, "bun.lockb", "bun.lock") else "npm"
        run = f"{pm} run" if pm in ("npm", "bun") else pm
        found.append({
            "stack": "node",
            "build": f"{run} build" if "build" in scripts else None,
            "test": (f"{pm} test" if "test" in scripts else None),
        })
    if _has(root, "pyproject.toml", "pytest.ini", "setup.py", "setup.cfg", "tox.ini"):
        found.append({"stack": "python", "build": None, "test": "python -m pytest -q"})
    if glob.glob(os.path.join(root, "*.sln")) or glob.glob(os.path.join(root, "*.csproj")) \
            or glob.glob(os.path.join(root, "*", "*.csproj")):
        found.append({"stack": "dotnet", "build": "dotnet build", "test": "dotnet test"})
    if _has(root, "pom.xml"):
        found.append({"stack": "maven", "build": "mvn -q -DskipTests package", "test": "mvn -q test"})
    if _has(root, "build.gradle", "build.gradle.kts"):
        gw = "gradlew.bat" if os.name == "nt" and _has(root, "gradlew.bat") \
            else "./gradlew" if _has(root, "gradlew") else "gradle"
        found.append({"stack": "gradle", "build": f"{gw} build -x test", "test": f"{gw} test"})
    if _has(root, "go.mod"):
        found.append({"stack": "go", "build": "go build ./...", "test": "go test ./..."})
    if _has(root, "Cargo.toml"):
        found.append({"stack": "rust", "build": "cargo build", "test": "cargo test"})
    if _has(root, "composer.json"):
        scripts = _read_json(os.path.join(root, "composer.json")).get("scripts", {})
        found.append({"stack": "php", "build": None, "test": "composer test" if "test" in scripts else None})
    if _has(root, "Makefile"):
        found.append({
            "stack": "make",
            "build": "make build" if _make_has_target(root, "build") else None,
            "test": "make test" if _make_has_target(root, "test") else None,
        })
    return found


def resolve_command(args, cfg, root):
    """Return (command, source) or (None, reason)."""
    if args.cmd:
        return args.cmd, "--cmd"
    if args.task:
        if cfg["commands"].get(args.task):
            return cfg["commands"][args.task], "dev-pipeline.json"
        for guess in detect(root):
            if guess.get(args.task):
                return guess[args.task], f"auto-detected ({guess['stack']})"
        return None, (f"no {args.task} command known: set commands.{args.task} in "
                      f"{devconfig.CONFIG_NAME} or pass --cmd")
    return None, "give --cmd, --task or --detect"


def kill_tree(proc):
    """Kill the shell and its children so the output pipe closes promptly."""
    if os.name == "nt":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True)
    else:
        import signal
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except OSError:
            proc.kill()


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cmd", help="command line to run (via the shell)")
    ap.add_argument("--task", choices=["test", "build"], help="use configured/detected command")
    ap.add_argument("--detect", action="store_true", help="print detected commands as JSON and exit")
    ap.add_argument("--cwd", default=".", help="project directory to run in")
    ap.add_argument("--timeout", type=int, help="seconds before the command is killed")
    ap.add_argument("--tail", type=int, default=8, help="trailing lines to show")
    ap.add_argument("--max-lines", type=int, default=60, help="cap on failure lines shown")
    args = ap.parse_args()

    cwd = os.path.abspath(args.cwd)
    cfg, warnings = devconfig.load(cwd)
    for w in warnings:
        print(f"config warning: {w}")
    if args.detect:
        print(json.dumps({"detected": detect(cwd), "configured": cfg["commands"]}, indent=2))
        return 0
    command, source = resolve_command(args, cfg, cwd)
    if command is None:
        print(f"COULD NOT START: {source}")
        return 2
    args.cmd = command
    timeout = args.timeout or cfg["checks"]["timeout_seconds"]
    fail_re = re.compile(cfg["checks"]["failure_regex"]) if cfg["checks"]["failure_regex"] else FAIL_RE
    start = time.time()
    timed_out = False
    try:
        proc = subprocess.Popen(
            args.cmd, shell=True, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            start_new_session=(os.name != "nt"),
        )
        try:
            raw, _ = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            kill_tree(proc)
            raw, _ = proc.communicate()
            timed_out = True
        code = 124 if timed_out else proc.returncode
    except OSError as exc:
        print(f"COULD NOT START: {exc}")
        return 2

    elapsed = time.time() - start
    lines = ANSI_RE.sub("", raw.decode("utf-8", errors="replace")).splitlines()

    log_dir = os.path.join(cwd, ".dev-pipeline")
    log_path = os.path.join(log_dir, "last-run.log")
    try:
        os.makedirs(log_dir, exist_ok=True)
        with open(log_path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))
    except OSError:
        log_path = "(could not write log)"

    status = "TIMEOUT" if timed_out else ("PASS" if code == 0 else "FAIL")
    warnings = sum(1 for l in lines if WARN_RE.search(l))
    print(f"{status}  exit={code}  {elapsed:.1f}s  lines={len(lines)}  warnings={warnings}")
    print(f"cmd: {args.cmd}  [{source}]")

    if status == "FAIL" or status == "TIMEOUT":
        picked, seen = [], set()
        for i, line in enumerate(lines):
            if fail_re.search(line):
                for j in (i, i + 1):  # the matching line plus one line of context
                    if j < len(lines) and j not in seen and lines[j].strip():
                        seen.add(j)
                        picked.append(short(lines[j]))
        if picked:
            print("--- failure lines ---")
            for row in picked[: args.max_lines]:
                print(row)
            if len(picked) > args.max_lines:
                print(f"... {len(picked) - args.max_lines} more failure lines in the log")
        if timed_out:
            print(f"--- killed after {timeout}s ---")

    print("--- tail ---")
    for row in lines[-args.tail:]:
        print(short(row))
    print(f"full output: {log_path}")
    return code


if __name__ == "__main__":
    sys.exit(main())
