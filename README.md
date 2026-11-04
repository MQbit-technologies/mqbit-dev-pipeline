# dev-pipeline

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
        7 Verify & close (Opus) ◄── 6 Audit (script) ◄── 5 Implement (Sonnet)
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

## Scripts (optional)

Python 3 (standard library only) and git make the pipeline cheaper; neither is required.

- `scope_check.py` compares your working tree to the brief and prints files outside
  scope, removed/replaced lines, renames, formatting-only edits, uncovered brief items
  and new declarations. Exit 0 clean, 1 findings, 2 cannot run.
- `run_checks.py --task test` runs your configured (or auto-detected) test command and
  prints PASS/FAIL, the failure lines and a short tail; the full log goes to
  `.dev-pipeline/last-run.log`. `--cmd "<command>"` runs any command you give it.

- `memory.py` maintains the project memory. Each map entry stores a fingerprint of the
  code it describes, so `status` shows exactly which entries are stale and scouts re-read
  only those. See [`project-memory.md`](skills/develop/references/project-memory.md).

To keep a code graph or search index current too, set `context.refresh_command` (runs in
the background) or `context.refresh_tool` (an MCP tool) in `dev-pipeline.json`.

Without Python or git, the pipeline falls back to the `diff-auditor` agent and raw test
output. The result is the same, just with more tokens spent.

## Install

From a marketplace (after you publish this repo to GitHub):

```
/plugin marketplace add mqbitplatform-ctrl/dev-pipeline
/plugin install dev-pipeline@dev-pipeline
```

Try it locally without installing:

```
claude --plugin-dir ./dev-pipeline
```

## Use

```
/dev-pipeline:develop Add a 10% discount for orders above 100 EUR, see docs/story-42.md
```

It also triggers on its own when you ask Claude to implement, build, add, change or fix
something from a requirement.

## Works with any stack

Nothing in the plugin assumes a language, framework or OS. Build/test commands are
auto-detected for Node (npm/pnpm/yarn/bun), Python, .NET, Maven, Gradle, Go, Rust, PHP
and Make, and you can set your own. It needs Claude Code (subagents + skills); git and
Python 3 are optional and only save tokens. The assistant answers in your language.

## Configuration

Zero config works. To tune it, run `/dev-pipeline:setup` (detects your stack, asks a few
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
dev-pipeline/
├── .claude-plugin/
│   ├── plugin.json            # plugin manifest
│   └── marketplace.json       # lets this repo act as its own marketplace
├── agents/
│   ├── scout.md               # Haiku, read-only
│   ├── implementor.md         # Sonnet, edits only the files in the brief
│   └── diff-auditor.md        # Haiku, fallback when scope_check.py can't run
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
│   ├── scripts/               # optional token savers (Python 3, stdlib only)
│   │   ├── scope_check.py     # diff vs brief → ~20-line report
│   │   ├── run_checks.py      # test/build runner that trims output
│   │   ├── memory.py          # project memory with staleness fingerprints
│   │   └── devconfig.py       # shared dev-pipeline.json loader
├── skills/setup/SKILL.md      # /dev-pipeline:setup — writes dev-pipeline.json
├── evals/                     # test cases: claude plugin eval .
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

## Security

`dev-pipeline.json` can hold shell commands (`commands.build`, `commands.test`,
`context.refresh_command`), and the pipeline runs them. Treat that file like a build
script: read it before running the pipeline in a repository you do not trust. The plugin
itself runs only the commands you or your config provide, makes no network calls, and
writes only to your project (the `.dev-pipeline/` folder, the memory file, and the files
listed in the approved brief).

## License

MIT — see [LICENSE](LICENSE).
