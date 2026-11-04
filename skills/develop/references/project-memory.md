# Project memory

A short file the pipeline keeps current so the next run starts with a map instead of
re-exploring the codebase. It saves tokens in two places: scouts skip areas that have not
changed, and the orchestrator does not re-ask decisions the user already made.

Default location: `.dev-pipeline/project-memory.md`. Set `context.memory_file` to a
tracked path (for example `docs/PROJECT_MEMORY.md`) to share it with the team.

## Format

```markdown
# Project memory

## Map
- `src/payments` - cart total, tax, discount rules <!--fp:98f32357-->
- `src/api/orders.py` - order endpoints; validation lives here <!--fp:1a2b3c4d-->

## Conventions
- money is integer cents; never float

## Decisions
- 2026-11-04 negative quantity is rejected with ValueError (user, story 42)

## Gotchas
- tax.py rounds half-up; do not use round()
```

- **Map**: one line per module, file or directory: path and what it is for. The hidden
  `fp` is a fingerprint of the file (or of every file under the directory).
- **Conventions**: how this codebase does things (naming, layering, error handling, test
  style) that a newcomer would otherwise have to rediscover.
- **Decisions**: durable answers from the user that will apply again.
- **Gotchas**: traps that cost time once.

Keep it under `context.max_memory_lines` (default 150). Short, specific lines beat prose.

## How staleness works

`memory.py status` recomputes each Map entry's fingerprint from the code on disk:

| State | Meaning | What the scout does |
|-------|---------|---------------------|
| FRESH | unchanged since the entry was written | trusts it, does not re-read |
| STALE | files changed since (by anyone, any tool) | re-reads and reports the area |
| MISSING | path no longer exists | ignores it; `prune` removes it |

No git history is needed, so uncommitted changes and non-git projects work. An entry
without a fingerprint counts as stale.

## What to store, what not to

Store: facts verified in code or confirmed by the user that a future run would otherwise
pay to rediscover.

Do not store: secrets, credentials or personal data; code or long excerpts; guesses;
details of a single requirement; anything a one-line `grep` finds faster than reading the
memory. When memory and code disagree, the code wins — fix the memory.

## Commands

```
memory.py init
memory.py status
memory.py add --section map --path src/payments --text "cart total, tax, discount"
memory.py add --section decisions --text "negative quantity is rejected"
memory.py refresh --paths src/payments/cart.py     # restamp entries covering these files
memory.py prune                                    # drop entries whose path is gone
```

`add` for a Map path replaces the existing line for that path; other sections ignore exact
duplicates.

## Code index refresh (optional)

If you maintain a code graph or search index, tell the pipeline how to bring it up to date
after a successful change. Set one of:

- `context.refresh_command`: a shell command, run in the background so a slow rebuild never
  blocks the run. Prefer an incremental/update mode.
- `context.refresh_tool`: the name of an MCP tool to call instead (for example a graph
  "update" tool). Tool calls run in the foreground, so use this only if the update is fast.

`context.hint` is a free-text line given to scouts, such as "query the code graph before
using grep". To let scouts call an MCP query tool, add it to `tools:` in `agents/scout.md`.
