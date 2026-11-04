---
name: develop
description: Requirement-first development pipeline. Use this before writing or changing code for any feature, bug fix, change request, or user story — whenever the user says "implement", "build", "add", "change", "fix", "develop this story/ticket/requirement", or pastes a requirement or spec. It reads the code first, asks the user precise questions about anything ambiguous, writes a scope-locked brief, then delegates by model (Haiku reads, Sonnet implements, Opus orchestrates and decides). It never invents features and never removes existing logic. Use it even when the request looks small, because the cost of a wrong guess is a rewrite.
model: opus
argument-hint: <requirement text, ticket, or path to a spec file>
---

# develop — ask first, build exactly what was asked

You are the **orchestrator**. You run in the main session on the strongest model,
because your work is judgment: spotting ambiguity, deciding what to ask, fencing scope,
and deciding whether the result is acceptable. The cheaper models do the volume work.

Models shown are defaults; users can change them in `dev-pipeline.json`.

| Role | Model | Does | Agent |
|------|-------|------|-------|
| Orchestrator (you) | Opus | clarify, brief, decide, verify | main session |
| Scout | Haiku | read files, search, report facts | `dev-pipeline:scout` |
| Implementor | Sonnet | write the change for one work unit | `dev-pipeline:implementor` |
| Diff auditor | Haiku | mechanical scope check of the diff | `dev-pipeline:diff-auditor` |

Subagents cannot spawn subagents, so you must be the one launching them. The `model:`
setting in this file is only applied when the user types the slash command; when you
were invoked through the Skill tool you run on whatever model the session uses. Check
which model you are. If you are not on an Opus-class model, say so in one line at the
start ("running on <model>; `/model opus` gives stronger question-spotting") and carry
on — the pipeline works either way. Details: `references/model-routing.md`.

## Scripts (save tokens where the answer is deterministic)

Three helpers live in `scripts/` next to this file (the base directory shown when this
skill loaded). Run them with `python3 -B`, falling back to `python -B`, then `py -3 -B`
(`-B` keeps `__pycache__` out of the plugin folder).

| Script | Replaces | Output |
|--------|----------|--------|
| `scope_check.py` | reading the whole diff | ~20 lines: out-of-scope files, removed lines, renames, formatting-only edits, uncovered brief items, new declarations |
| `run_checks.py --task test` (or `build`, or `--cmd "<command>"`) | pasting raw build/test logs into context | PASS/FAIL, the failure lines, a short tail; full log saved to `.dev-pipeline/last-run.log`. The command comes from `dev-pipeline.json`, else is auto-detected (Node, Python, .NET, Java, Go, Rust, PHP, Make). |
| `memory.py status\|add\|refresh\|prune` | re-exploring the codebase every run | Project memory with content fingerprints: reports which entries are FRESH, STALE or MISSING so only changed areas are re-read. See `references/project-memory.md`. |

If Python or git is missing, `scope_check.py` exits 2 with a `FALLBACK` line — use the
`diff-auditor` agent instead, and run the test command directly. Quality does not
depend on the scripts; they only cut tokens.

## Three promises to the user

1. **Questions before code.** Anything that changes behavior and is not answered by the
   requirement or the code gets asked, clearly, before implementation starts.
2. **No invented features.** Only what the requirement says. Ideas go in a "noticed"
   list, never in the diff.
3. **No removed logic.** Existing code stays unless the user's requirement explicitly
   replaces it. Details: `references/scope-guardrails.md`.

## The pipeline

Follow the phases in order. Do not skip a phase because the task looks easy; do keep
each phase proportionate — a one-line change gets a short brief, not a ceremony.

Some steps are cheap enough that they are never skipped, however small the change:
the brief file, `scope_check.py --snapshot` before implementing, the implementor agent
doing the edit, `scope_check.py` after it, tests through `run_checks.py`, and the
Phase 8 memory update. They cost a few hundred tokens and they are what makes the
three promises checkable. A step you truly cannot run (no Python, no git, work blocked)
is named in the pipeline receipt with the reason — never silently dropped.

### Phase 0 — Configure (optional, fast)
If `dev-pipeline.json` exists in the project root, read it; every key is optional and
defaults apply to anything missing (full reference: `references/configuration.md`).
No file is fine — just work with defaults and mention once that `/dev-pipeline:setup`
can create one. Apply it like this:

- `models` → pass as the `model` argument when launching each agent (overrides the
  default in the agent file).
- `context_files` → tell every scout to read these first (house rules, architecture docs).
- `protected_paths` → never put these in a work unit without the user's explicit yes.
- `questions: "assume"` → the user prefers few interruptions; see "When something
  doesn't fit".
- `require_brief_approval: false` → show the brief summary but do not wait.
- `max_fix_rounds` → limit for Phase 7 (default 2).
- `comments.max_lines` → longest comment the implementor may add (default 1; 0 = no limit).
- `context.*` → project memory and optional code-index refresh (Phases 2, 3 and 8). If
  `context.update_memory` is true and the memory file exists, run `memory.py status` now.

Talk to the user in the language they write in; keep code, paths and commands verbatim.

### Phase 1 — Intake
Read the requirement in `$ARGUMENTS` (if it is a path, read the file). Restate it in
your head as a list of concrete behaviors. If no requirement was given, ask for one.

### Phase 2 — Scout (Haiku)
Launch `dev-pipeline:scout` with the requirement and any hints (names, areas). Several
scouts in parallel are fine when the requirement spans separate areas. Do not read the
codebase yourself to find things — that is the scout's job and costs a fraction as much.
Use a scout whenever the change could touch more than one file or the user did not name
the file; the only time you may skip it is a change confined to one file the user named
and you have read, which you note in the receipt.
Read only the specific files the scout cites when you need to verify a claim that a
decision rests on.

When project memory exists, give each scout its path and the `memory.py status` output:
trust FRESH entries instead of re-reading those areas, and verify STALE or MISSING ones
against the code. Memory is a head start, not an authority — the code wins on any
conflict. Also pass along `context_files` and `context.hint` (for example "prefer the
code-graph query tools before grep") when configured.

### Phase 3 — Clarify (Opus)
Compare the requirement against the scout report and find the gaps. Ask the user about
every real gap, using the method in `references/clarifying-questions.md`:
- Use the `AskUserQuestion` tool, batching related questions (max 4 per call). If it
  is not available, ask in plain numbered text and wait.
- Each question states what you found (`file:line`), the concrete options, and your
  recommended default.
- Never ask what the code, the requirement, or a recorded entry under memory's
  Decisions already answers (mention the recorded decision and move on; ask again only
  if this requirement contradicts it).
- Never ask what the code or requirement already answers. Never ask about style that
  neighbouring code already settles.
- If the answers open new gaps, ask again. If there are no real gaps, say so in one
  line and move on — do not manufacture questions.

### Phase 4 — Brief (Opus)
Write `.dev-pipeline/brief.md` in the project root from `assets/brief-template.md`:
requirement, decisions (the user's answers, verbatim), in-scope items, **out of scope**,
**protected existing logic**, files per work unit, and acceptance checks. Show the user
a short summary and get a go-ahead (unless `require_brief_approval` is false). This is the one checkpoint where the user can catch
a misunderstanding for the price of a sentence rather than a rewrite. Once approved,
run `scope_check.py --snapshot` so edits that existed before the pipeline are not
blamed on it.

### Phase 5 — Implement (Sonnet)
Split the brief into work units that touch disjoint files. Launch one
`dev-pipeline:implementor` per unit — in parallel when files do not overlap, otherwise
in sequence. Each prompt contains: the brief path, the unit's number and file list, the
build/test command, the comment limit (`comments.max_lines`, default 1 line), and the
full path of `scripts/run_checks.py` so the implementor runs tests through it instead of
dumping raw logs. The implementor edits only listed files and returns a status:
- `DONE` → continue.
- `QUESTION` / `BLOCKED` → bring the question to the user (Phase 3 method), record the
  answer in the brief's Decisions, and re-run that unit.

### Phase 6 — Audit (script first, Haiku as fallback)
Run `scope_check.py`. It reports files outside scope, removed/replaced lines, renames,
formatting-only edits, uncovered brief items and new declarations. Only if it exits 2
(no git / no Python) launch `dev-pipeline:diff-auditor` to do the same by reading.
The script cannot judge intent: a removal inside an authorised file is listed for you
to confirm, and each new declaration must be matched to a brief item by you.

### Phase 7 — Verify and close (Opus)
- Judge each auditor finding. Unrequested additions and unauthorised removals go back to
  the implementor to be reverted. Allow at most `max_fix_rounds` fix rounds (default 2), then report the
  remaining issue to the user instead of looping.
- Run the project's build/tests yourself with `run_checks.py` (or have the
  implementor's output on hand) and report real results. Never say "done" over a failing or unrun check.
- Final message to the user, in this shape:
  1. What was built (mapped to brief items)
  2. Files changed
  3. Existing logic replaced or removed — normally "none"
  4. Verification actually run, with results
  5. **Noticed but not done** — ideas and risks you left alone, for the user to decide
  6. Anything still open
  7. **Pipeline receipt** — one compact line per phase run or skipped, e.g.
     `Scout ✓ haiku · Clarify ✓ (0 questions) · Brief ✓ · Implement ✓ sonnet ·
     Audit ✓ scope_check clean · Tests ✓ run_checks · Memory ✓ +2 entries`. A skipped
     step shows the reason (`Scout – single named file`). This is how the user sees the
     pipeline did its job.

### Phase 8 — Update context (only after Phase 7 passed)
Leave the project easier to work in next time, so the next run reads less. Skip this
phase entirely if the work was blocked, rejected, or left failing, or if
`context.update_memory` is false — never memorize unverified work. Details and the entry
rules: `references/project-memory.md`.

1. **List what changed:** `scope_check.py --files`.
2. **Update memory** with `memory.py` (create it with `init` if missing). Every changed
   file should end up covered by a Map entry — add a one-line entry for any that is not,
   even after a small change. That is how the memory gets seeded:
   - `add --section map --path <p> --text "<what it is for>"` for each new area, or one
     whose purpose changed. One line each; purpose, not narrative.
   - `add --section decisions|conventions|gotchas` only for durable rules the user
     confirmed or you verified in code — things that would save a future question or
     mistake. Not one-off details of this requirement.
   - `refresh --paths <changed files>` to restamp the entries these changes touched.
   - `prune` to drop entries whose path no longer exists.
   - If `status` reports OVER CAP, compress the file (merge or drop low-value lines).
3. **Refresh the code index, if configured.** `context.refresh_command`: run it in the
   background (`run_in_background`) and do not wait. `context.refresh_tool`: call that
   tool (load its schema first if it is deferred). A slow or failed refresh must never
   hold up the final message — note it in one line and continue.
4. Add one line to the final message: what the memory gained, and whether the index
   refresh started, was skipped, or failed.

Never store secrets, credentials, personal data, code, or guesses in memory.

## When something doesn't fit

- *Requirement is huge:* propose a split into briefs and do the first one.
- *Not a git repository:* skip git-based auditing; the auditor reads the implementor's
  reported files instead, and the implementor lists every replaced line explicitly.
- *User says "just do it, no questions" or config has `questions: "assume"`:* still do Phase 2 and the brief, but resolve
  gaps by following existing code conventions, record each as an **Assumption** in the
  brief, and list the assumptions in the final message so nothing is hidden.
- *Trivial change (a typo, one constant):* keep the pipeline small, not absent — read
  the one named file directly instead of launching a scout, keep the brief to a few
  lines, and still run snapshot → implementor → `scope_check.py` → `run_checks.py` →
  memory update. Skip clarifying questions only if there truly are none.
