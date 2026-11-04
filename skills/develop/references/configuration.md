# Configuration — `dev-pipeline.json`

Optional file in the project root. Commit it so the whole team gets the same behavior.
Every key is optional; anything missing uses the default. Unknown keys are ignored with a
warning (usually a typo). Run `/dev-pipeline:setup` to create one interactively.

```json
{
  "$schema": "./skills/develop/assets/dev-pipeline.schema.json",
  "models": { "scout": "haiku", "implementor": "sonnet", "auditor": "haiku" },
  "commands": { "build": "npm run build", "test": "npm test" },
  "context_files": ["CONTRIBUTING.md", "docs/architecture.md"],
  "protected_paths": ["migrations/**", "src/generated/**"],
  "scope": { "ignore": ["package-lock.json", "*.lock"], "declaration_regex": null },
  "checks": { "timeout_seconds": 900, "failure_regex": null },
  "comments": { "max_lines": 1 },
  "context": {
    "update_memory": true,
    "memory_file": ".dev-pipeline/project-memory.md",
    "max_memory_lines": 150,
    "refresh_command": null,
    "refresh_tool": null,
    "hint": null
  },
  "questions": "ask",
  "require_brief_approval": true,
  "max_fix_rounds": 2
}
```

| Key | Default | Meaning |
|-----|---------|---------|
| `models.scout` / `implementor` / `auditor` | `haiku` / `sonnet` / `haiku` | Model alias per agent: `haiku`, `sonnet`, `opus`. The orchestrator is your main session; set it with `/model`. |
| `commands.build` / `commands.test` | auto-detected | Shell commands run by `run_checks.py --task build\|test`. Detection covers Node (npm/pnpm/yarn/bun), Python, .NET, Maven, Gradle, Go, Rust, PHP, Make. |
| `context_files` | `[]` | Files every scout reads first: contributing guides, architecture notes, house rules. |
| `protected_paths` | `[]` | Globs the pipeline must not edit without the user's explicit approval (migrations, generated code, vendored code). `scope_check` flags any touch. |
| `scope.ignore` | `[]` | Globs `scope_check` skips entirely (lockfiles, build output, generated files). |
| `scope.declaration_regex` | built-in multi-language pattern | Regex for lines that declare new public things (functions, classes, ...); matches are listed for review. Set it for languages the default misses. |
| `checks.timeout_seconds` | `900` | Kill the build/test command after this long. |
| `checks.failure_regex` | built-in | Regex that marks a line as a failure line when trimming output. |
| `comments.max_lines` | `1` | Longest comment (in lines) the implementor may add; `scope_check` flags longer added runs. `0` turns the limit off. Existing comments are never touched. |
| `context.update_memory` | `true` | After a verified change, update the project memory (see `project-memory.md`). `false` turns Phase 8 off. |
| `context.memory_file` | `.dev-pipeline/project-memory.md` | Where memory lives. Point it at a tracked path (e.g. `docs/PROJECT_MEMORY.md`) to share it with the team. |
| `context.max_memory_lines` | `150` | Soft cap; `status` warns above it and the pipeline compresses the file. |
| `context.refresh_command` | `null` | Shell command that refreshes your code index/graph after a change (run in the background, never awaited). |
| `context.refresh_tool` | `null` | MCP tool name to call for the same purpose (runs in the foreground; use only if fast). |
| `context.hint` | `null` | One line given to every scout, e.g. "query the code graph before grep". |
| `questions` | `"ask"` | `"ask"`: stop and ask about every real gap. `"assume"`: follow existing code conventions, record each assumption in the brief, and list them in the final message. |
| `require_brief_approval` | `true` | Wait for the user's go-ahead on the brief before implementing. |
| `max_fix_rounds` | `2` | How many times the audit may send work back before the issue is handed to the user. |

Globs are relative to the project root and use `*`/`**` shell-style matching.

## What config cannot change

The three promises (ask before coding, no invented features, no removed logic) are not
configurable. Everything else is a preference.

## Using a full model ID

`models.*` takes the aliases `haiku`, `sonnet`, `opus`. To pin an exact model version,
edit the `model:` line in the agent file under `agents/` instead.

## Giving the scout more tools

The scout is read-only (`Read`, `Grep`, `Glob`). If you use code-search or code-graph MCP
servers, add their tool names to the `tools:` line in `agents/scout.md` and the scout will
use them.
