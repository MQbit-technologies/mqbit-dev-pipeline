# Model routing

The pipeline spends the expensive model where judgment matters and the cheap models
where volume matters.

## Assignment

| Work | Model | Why |
|------|-------|-----|
| Reading files, searching, summarizing what exists | **Haiku** (`scout`, `diff-auditor`) | High-volume, low-judgment, fast and cheap. Reports facts with `file:line`, so errors are checkable. |
| Writing the change for a well-specified work unit | **Sonnet** (`implementor`) | Strong coding at a moderate cost; the brief removes the ambiguity so deep reasoning is not needed. |
| Spotting ambiguity, asking the user, fencing scope, judging the audit, final verification | **Opus** (main session) | Where a wrong call is expensive: a missed question or an accepted scope violation costs a rewrite. |

## Scripts instead of models

Anything deterministic is done by a script, which costs no tokens: the diff-versus-brief
check (`scripts/scope_check.py`) and test-output trimming (`scripts/run_checks.py`).
That is why the Haiku `diff-auditor` is only a fallback. Models stay on the work that
needs judgment.

## How it is wired

- Each agent in `agents/` sets its own `model:` in frontmatter, so routing happens
  automatically whenever the orchestrator launches it.
- The orchestrator is the main session, so it runs on whatever model your session uses.
  The skill's `model: opus` setting is **not** applied when Claude invokes the skill
  itself (observed in testing: the orchestrator stayed on Sonnet). Start your session on
  Opus with `/model opus`, or use the `opusplan` alias, which plans on Opus and executes
  on Sonnet. The pipeline still works on Sonnet; Opus is better at spotting ambiguity.
  The skill tells the user at the start if it is not on an Opus-class model.
- **Subagents cannot launch subagents.** That is why the orchestrator is the main
  session and not itself a subagent.

## Overriding the defaults

Edit the `model:` line in the agent file. Accepted values are the aliases `haiku`,
`sonnet`, `opus` (always the latest of each family) or a full model ID. Common tweaks:
- Large or subtle codebase → set `scout` to `sonnet`.
- Hard algorithmic work unit → run that one implementor on `opus` by saying so in its
  prompt, or change the agent file.
- Tight budget → leave everything as is; Haiku already carries the most tokens.

## Parallelism

Launch scouts in parallel when the requirement spans separate areas. Launch
implementors in parallel only when their file lists are disjoint; two agents editing
the same file will overwrite each other.

## What to hand each agent

Pass paths and short instructions, not pasted file contents. The scout and implementor
read what they need themselves; the brief file is the shared source of truth, which keeps
prompts small and the handoff identical for every agent.
