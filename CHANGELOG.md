# Changelog

## 0.1.1 - 2026-11-04
- Found by live testing: the skill's `model: opus` is not applied when the skill is invoked
  through the Skill tool. The orchestrator now states which model it runs on, and the docs
  say to start the session with `/model opus`.
- Small changes no longer skip the cheap steps: brief, snapshot, implementor, `scope_check`,
  `run_checks` and the memory update always run. A scout is required unless the change is
  confined to one file the user named.
- Final message now ends with a one-line-per-phase "pipeline receipt" showing what ran and
  why anything was skipped.
- Scripts are invoked with `python -B` so no `__pycache__` appears in the plugin folder.
- `evals/` moved to the plugin root, where `claude plugin eval` expects it.
- Fixed a markdown table in `SKILL.md` that was split by a blank line.

## 0.1.0 — 2026-11-04
- Initial release: `develop` skill (orchestrator), `scout` (Haiku), `implementor`
  (Sonnet), `diff-auditor` (Haiku).
- Reference guides for clarifying questions, scope guardrails, model routing.
- Brief template.
- Optional `dev-pipeline.json` project config (models, commands, protected paths,
  context files, question style, approval, fix rounds) with JSON schema, and a
  `/dev-pipeline:setup` skill that detects the stack and writes it.
- Phase 8 "update context": project memory (`scripts/memory.py`) with content
  fingerprints so scouts re-read only stale areas and recorded decisions are not re-asked;
  optional `context.refresh_command` / `context.refresh_tool` to refresh a code index.
- One-line comment rule: implementor adds only short single-line comments;
  `comments.max_lines` config (default 1) and a `scope_check` check for longer ones.
- Build/test auto-detection for Node, Python, .NET, Maven, Gradle, Go, Rust, PHP, Make.
- `scripts/scope_check.py` and `scripts/run_checks.py` (Python 3, stdlib only) to cut
  token use; `diff-auditor` becomes the fallback when they cannot run.
