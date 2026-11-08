---
name: setup
description: One-time project setup for the dev-pipeline plugin. Detects the project's stack and build/test commands, asks a few short questions, and writes dev-pipeline.json in the project root. Use when the user says "set up dev-pipeline", "configure the pipeline", "change which model does what", "set my test command", or when /mqbit-dev-pipeline:develop reports no config and the user wants one.
argument-hint: (no arguments)
---

# setup — create `dev-pipeline.json` in under a minute

The pipeline works with zero configuration. This skill only exists to make the
common choices explicit and committed, so a whole team behaves the same way.
Reference for every key: `../develop/references/configuration.md`.

## Steps

1. **Detect.** Look at the project's marker files (`package.json`, `pyproject.toml`,
   `pytest.ini`, `*.sln`, `*.csproj`, `pom.xml`, `build.gradle*`, `go.mod`, `Cargo.toml`,
   `composer.json`, `Makefile`) and guess the build/test commands from them. For
   `package.json`, use its `scripts` entries and the lockfile present (`pnpm-lock.yaml`,
   `yarn.lock`, `bun.lockb`, else npm).
2. **If `dev-pipeline.json` already exists**, read it and treat this run as an edit: show
   the current values and change only what the user asks to change.
3. **Ask** with `AskUserQuestion` (plain numbered text if the tool is unavailable), in at
   most two rounds. Offer the detected value as the recommended option each time:
   - Test command and build command (confirm or correct the detected ones; "none" is valid).
   - Files every scout should read first (e.g. CONTRIBUTING.md, an architecture doc).
   - Paths that must not be edited without approval (migrations, generated code, vendored code).
   - Question style: ask about every real gap (`ask`), or assume from existing code and
     list assumptions at the end (`assume`).
   - Models: keep the defaults (Haiku reads, Sonnet implements) or change them.
   - Project memory: keep it local (`.dev-pipeline/project-memory.md`, the default) or
     share it with the team by pointing `context.memory_file` at a tracked path such as
     `docs/PROJECT_MEMORY.md`; or turn it off (`context.update_memory: false`).
   - Code index: if they use a code graph or search index, ask for the command (or MCP
     tool name) that updates it after changes, and write it to `context.refresh_command`
     or `context.refresh_tool`. Leave both out if they have none.
   Skip any question the user has already answered or that does not apply.
4. **Write** `dev-pipeline.json` in the project root. Include only keys that differ from
   the defaults.
5. **Ignore the runtime folder.** The pipeline writes working files to `.dev-pipeline/`.
   Ask whether to add `.dev-pipeline/` to `.gitignore`, and do it on yes. Do not touch
   `.gitignore` without that answer.
6. **Confirm** in two or three lines: what was written and how to run the pipeline
   (`/mqbit-dev-pipeline:develop <requirement>`).

## Rules

- Write only `dev-pipeline.json` (and `.gitignore` if approved). Nothing else.
- Never invent a command. If detection finds nothing and the user has none, leave the key out.
- Never run the project's build or tests during setup.
