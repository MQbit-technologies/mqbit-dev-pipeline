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
- `src/payments` - cart total, tax, discount rules <!--at:98f3235-->
- `src/api/orders.py` - order endpoints; validation lives here <!--at:1a2b3c4-->

## Conventions
- money is integer cents; never float

## Decisions
- 2026-11-04 negative quantity is rejected with ValueError (user, story 42)

## Gotchas
- tax.py rounds half-up; do not use round()
```

- **Map**: one line per module, file or directory: path and what it is for. The hidden
  `at` stamp is the short commit (`git rev-parse --short HEAD`) the entry was last
  verified against. Without git, leave the stamp out.
- **Conventions**: how this codebase does things (naming, layering, error handling, test
  style) that a newcomer would otherwise have to rediscover.
- **Decisions**: durable answers from the user that will apply again.
- **Gotchas**: traps that cost time once.

Keep it under `context.max_memory_lines` (default 150). Short, specific lines beat prose.

## How staleness works

Find changed files with two read-only git commands, run once per memory check:

```
git diff --name-only <oldest at-stamp in the file>   # committed + uncommitted changes since
git status --porcelain                               # adds new untracked files
```

Then classify each Map entry:

| State | Meaning | What the scout does |
|-------|---------|---------------------|
| FRESH | no changed file is at or under the entry's path since its stamp | trusts it, does not re-read |
| STALE | a file at or under the path changed since its stamp (by anyone, any tool) | re-reads and reports the area |
| MISSING | path no longer exists | ignores it; Phase 8 removes it |

An entry without an `at` stamp (including an old `fp` stamp from version 0.2), or any
entry in a project without git, counts as STALE: the
scout re-reads it only when the requirement touches that area.

## What to store, what not to

Store: facts verified in code or confirmed by the user that a future run would otherwise
pay to rediscover.

Do not store: secrets, credentials or personal data; code or long excerpts; guesses;
details of a single requirement; anything a one-line `grep` finds faster than reading the
memory. When memory and code disagree, the code wins — fix the memory.

## Editing it

The orchestrator edits the file directly with its normal file tools:

- A Map line for an existing path replaces that line; never keep two lines for one path.
- Restamp an entry (set `at` to the current short commit) only after its area was
  verified in this run.
- Decisions lines start with the date (`YYYY-MM-DD`). Skip exact duplicates in any section.
- Remove entries whose path no longer exists.

## Code index refresh (optional)

If you maintain a code graph or search index, tell the pipeline how to bring it up to date
after a successful change. Set one of:

- `context.refresh_command`: a shell command, run in the background so a slow rebuild never
  blocks the run. Prefer an incremental/update mode.
- `context.refresh_tool`: the name of an MCP tool to call instead (for example a graph
  "update" tool). Tool calls run in the foreground, so use this only if the update is fast.

`context.hint` is a free-text line given to scouts, such as "query the code graph before
using grep". To let scouts call an MCP query tool, add it to `tools:` in `agents/scout.md`.
