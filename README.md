# Mqbit Dev Pipeline

*A Claude Code plugin by Mqbit Technologies.*

A Claude Code plugin that makes AI-assisted development **ask first, build exactly what
was asked, and keep costs sensible** by routing each kind of work to the right model.

- **Questions before code** — reads your codebase, then asks you precise questions about
  anything ambiguous (with options and a recommended default).
- **No invented features** — only what the requirement says. Extra ideas are listed for
  you, never added to the diff.
- **No removed logic** — existing code stays unless your requirement replaces it.
- **Short comments** — new comments are one line, only where the reason isn't obvious
  (configurable).
- **Project memory** — after a verified change it updates a short map of the project
  (modules, conventions, decisions) and refreshes your code index if you set one up, so
  the next run reads less.
- **Model routing** — Haiku reads, Sonnet implements, Opus decides.

## The pipeline

```
 requirement
     │
     ▼
 1 Intake ──► 2 Scout (Haiku) ──► 3 Clarify (Opus ⇄ you) ──► 4 Brief (you approve)
                                                                   │
        7 Verify & close (Opus) ◄── 6 Audit (Haiku) ◄── 5 Implement (Sonnet)
                │
                ▼
        8 Update context: project memory + code-index refresh
```

| Role | Model | Agent |
|------|-------|-------|
| Orchestrator | Opus (main session) | skill `develop` |
| Scout — reads/searches code | Haiku | `scout` |
| Implementor — writes the change | Sonnet | `implementor` |
| Diff auditor — checks the diff against the brief | Haiku | `diff-auditor` |

The shared source of truth is `.dev-pipeline/brief.md`, created in your project during a
run. It records your answers, what is in/out of scope, and which existing logic is
protected. Add `.dev-pipeline/` to your `.gitignore` if you don't want to commit it.

## Keeping token use low

The plugin is Markdown and JSON only; it ships no scripts.

- The `diff-auditor` (Haiku) checks the change against the brief from `git diff`, so the
  orchestrator never reads whole files to audit them.
- Test and build output goes to `.dev-pipeline/last-run.log`; only the exit code, the
  failure lines and a short tail are read back.
- The project memory stamps each map entry with the commit it was verified at, so one
  `git diff --name-only` shows which entries are stale and scouts re-read only those. See
  [`project-memory.md`](skills/develop/references/project-memory.md).

To keep a code graph or search index current too, set `context.refresh_command` (runs in
the background) or `context.refresh_tool` (an MCP tool) in `dev-pipeline.json`.

Git is optional. Without it, the auditor reads the files the implementor reports as
changed, and memory entries are re-checked when a requirement touches them.

## Install

From a marketplace (after you publish this repo to GitHub):

```
/plugin marketplace add mqbitplatform-ctrl/mqbit-dev-pipeline
/plugin install mqbit-dev-pipeline@mqbit-dev-pipeline
```

Try it locally without installing:

```
claude --plugin-dir ./mqbit-dev-pipeline
```

## Use

```
/mqbit-dev-pipeline:develop Add a 10% discount for orders above 100 EUR, see docs/story-42.md
```

Claude can also start it when you ask to use the dev pipeline, or hand over a ticket,
story or spec file to implement end to end. It does not take over ordinary questions,
reviews or quick edits.

Example prompts:

```
/mqbit-dev-pipeline:develop docs/story-42.md
Use the dev pipeline to implement JIRA-118: customers can export invoices as CSV
/mqbit-dev-pipeline:setup
```

## Works with any stack

Nothing in the plugin assumes a language, framework or OS. Build/test commands are
auto-detected for Node (npm/pnpm/yarn/bun), Python, .NET, Maven, Gradle, Go, Rust, PHP
and Make, and you can set your own. It needs Claude Code (subagents + skills); git is
optional and only saves tokens. The assistant answers in your language.

## Configuration

Zero config works. To tune it, run `/mqbit-dev-pipeline:setup` (detects your stack, asks a few
short questions) or create `dev-pipeline.json` in your project root by hand and commit it.
Every key is optional:

```json
{
  "models": { "scout": "haiku", "implementor": "sonnet", "auditor": "haiku" },
  "commands": { "build": "npm run build", "test": "npm test" },
  "context_files": ["CONTRIBUTING.md"],
  "protected_paths": ["migrations/**"],
  "scope": { "ignore": ["*.lock"] },
  "comments": { "max_lines": 1 },
  "questions": "ask",
  "require_brief_approval": true,
  "max_fix_rounds": 2
}
```

Full key reference: [`skills/develop/references/configuration.md`](skills/develop/references/configuration.md).
Editor validation: `skills/develop/assets/dev-pipeline.schema.json`.

For deeper customization everything else is plain Markdown:

| To change | Edit |
|-----------|------|
| Pin an exact model version | `model:` line in `agents/*.md` |
| Give the scout MCP/code-search tools | `tools:` line in `agents/scout.md` |
| How questions are asked | `skills/develop/references/clarifying-questions.md` |
| What counts as scope creep | `skills/develop/references/scope-guardrails.md` |
| Brief layout | `skills/develop/assets/brief-template.md` |

**Orchestrator model:** the pipeline's orchestrator is your main session, and the skill's
`model: opus` is not applied when Claude invokes the skill itself. For the best question-
spotting, start the session with `/model opus` (or `opusplan`). It works on Sonnet too,
and tells you which model it is on.

## Layout

```
mqbit-dev-pipeline/
├── .claude-plugin/
│   ├── plugin.json            # plugin manifest
│   └── marketplace.json       # lets this repo act as its own marketplace
├── agents/
│   ├── scout.md               # Haiku, read-only
│   ├── implementor.md         # Sonnet, edits only the files in the brief
│   └── diff-auditor.md        # Haiku, read-only, checks the diff against the brief
├── skills/develop/
│   ├── SKILL.md               # the orchestrator (pipeline + rules)
│   ├── references/            # loaded on demand
│   │   ├── clarifying-questions.md
│   │   ├── scope-guardrails.md
│   │   ├── model-routing.md
│   │   ├── project-memory.md
│   │   └── configuration.md
│   ├── assets/
│   │   ├── brief-template.md
│   │   ├── dev-pipeline.example.json
│   │   └── dev-pipeline.schema.json
├── skills/setup/SKILL.md      # /mqbit-dev-pipeline:setup — writes dev-pipeline.json
├── CHANGELOG.md
├── LICENSE
└── README.md
```

## Design notes

- **Subagents can't spawn subagents**, so the orchestrator is the main session.
- **Hand off by file, not by pasting.** Agents read the brief themselves, which keeps
  prompts small and identical across agents.
- **The user checkpoint is the brief.** One approval before any code is written is the
  cheapest place to catch a misunderstanding.
- **Haiku reports are checkable**: every claim carries `file:line`.

## What it runs, and data handling

Everything runs on your machine; the plugin has no server and makes **no network calls**.

**What the plugin runs:** the plugin contains no scripts or executables. Through Claude
Code's normal tools, with your usual permission prompts, the pipeline runs:

| Command | Why |
|---------|-----|
| read-only `git` commands (`rev-parse`, `status`, `diff`) | record a baseline and compare your changes to the approved brief |
| the build/test command from `dev-pipeline.json`, or one detected from your project files (for example `npm test`, `dotnet test`) | run your tests; output goes to `.dev-pipeline/last-run.log` |
| `context.refresh_command` from `dev-pipeline.json`, only if you set one | refresh your code index |

**What it writes** (only inside your project): `.dev-pipeline/` (brief, last test log,
baseline), the project memory file (default `.dev-pipeline/project-memory.md`), and the
source files listed in the brief you approve. It does not change Claude Code or permission
settings.

**Personal data:** the plugin does not collect, store or transmit personal data. The
project memory holds short notes about your own code and decisions, stays in your
repository or working folder, and is deleted by deleting the file. It is not sent anywhere
by the plugin. (Claude itself processes your prompts and code as it normally does.)

**Trust note:** `dev-pipeline.json` can contain shell commands (`commands.build`,
`commands.test`, `context.refresh_command`) and the pipeline runs them. Treat it like a
build script and read it before running the pipeline in a repository you do not trust.

## License

MIT — see [LICENSE](LICENSE).
