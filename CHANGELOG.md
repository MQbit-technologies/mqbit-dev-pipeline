# Changelog

## 0.1.2 - 2026-11-04
- README: explicit "What it runs, and data handling" section (scripts, writes, no network,
  no personal data) for the plugin directory review.
- Added a plugin icon.
- Changelog wording simplified (no inline command snippets).

## 0.1.1 - 2026-11-04
- Found by live testing: the skill's model setting is not applied when Claude invokes the
  skill itself. The orchestrator now states which model it runs on, and the docs advise
  starting the session on Opus.
- Small changes no longer skip the cheap steps: brief, snapshot, implementor, scope check,
  test run and memory update always run. A scout is required unless the change is confined
  to one file the user named.
- Final message now ends with a one-line-per-phase pipeline receipt showing what ran and
  why anything was skipped.
- Scripts are started with the Python no-bytecode flag so no cache folder appears in the
  plugin folder.
- The evals folder moved to the plugin root, where the eval runner expects it.
- Fixed a markdown table in the main skill file that was split by a blank line.

## 0.1.0 - 2026-11-04
- Initial release: develop skill (orchestrator), scout (Haiku), implementor (Sonnet),
  diff-auditor (Haiku).
- Reference guides for clarifying questions, scope guardrails, model routing.
- Brief template.
- Optional project config file (models, commands, protected paths, context files,
  question style, approval, fix rounds) with a JSON schema, and a setup skill that detects
  the stack and writes it.
- Phase 8 "update context": project memory with content fingerprints so scouts re-read
  only stale areas and recorded decisions are not re-asked; optional settings to refresh a
  code index.
- One-line comment rule: the implementor adds only short single-line comments; a config
  limit and a scope-check test enforce it.
- Build and test auto-detection for Node, Python, .NET, Maven, Gradle, Go, Rust, PHP, Make.
- Scope-check and test-runner scripts (Python 3, standard library only) to cut token use;
  the diff-auditor agent is the fallback when they cannot run.
