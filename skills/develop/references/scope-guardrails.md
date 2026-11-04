# Scope guardrails

Read this in Phase 4 (writing the brief) and Phase 7 (judging the audit). These rules
exist because the usual way an AI-assisted change goes wrong is not a bug in the
requested code — it is something nobody asked for riding along with it.

## 1. Do not invent features

The brief's **In scope** list is the whole job. Anything not traceable to a requirement
line or a recorded user decision is out.

Typical invented extras to reject:
- extra parameters, config keys, flags, endpoints, fields "for flexibility"
- new validation, logging, caching, retries, or error types nobody requested
- "while I'm here" cleanups, renames, reformatting, dependency bumps
- tests for behavior outside the requirement (tests for the requested behavior are fine
  when the brief lists them)

If a good idea comes up, it goes into the final message under **Noticed but not done**.
The user can say yes next time; the diff does not decide for them.

## 2. Do not remove existing logic

Existing code is evidence of a requirement you may not be able to see. Therefore:
- Keep every branch, validation, fallback, and guard that is not named in the brief.
- Do not delete code that merely *looks* unused. Report it under Noticed instead.
- Do not comment code out as a substitute for deleting it.
- Replacing logic is allowed **only** when the requirement or a recorded decision says
  that specific behavior changes. The brief then lists it under **Authorised
  replacements** with `file` and a description, and the audit checks against that list.
- When a new rule interacts with old logic, prefer extending (a new branch beside the
  old one) over rewriting, unless the user chose otherwise.

## 3. Minimum change

- Edit in place; smallest diff that satisfies the brief.
- No renames, moves, reordering, or reformatting of untouched code.
- Match existing naming, structure, comment density and test style.
- Place code where the project's existing layering puts it. If the project has
  conventions about where shared vs. feature-specific code lives, follow them; if the
  right place is unclear, that is a Phase 3 question, not a guess.

## 3b. Comments stay short

New comments are one short line (`comments.max_lines` in the config, default 1) and only
where the *why* is not obvious from the code. Long comment blocks, banners, essay
docstrings and "what this does" narration add review noise and drift out of date. Existing
comments are left alone. `scope_check.py` flags any added comment run longer than the
limit; shorten it rather than deleting the useful part.

## 4. Judging the audit (Phase 7)

| Auditor finding | Your call |
|-----------------|-----------|
| Out-of-scope file changed | Revert unless the brief should have listed it — then add it to the brief *and tell the user*. |
| Unauthorised removal/replacement | Restore it. |
| Unrequested addition | Remove it; move the idea to Noticed. |
| Rename / formatting-only hunk | Revert. |
| Comment longer than the limit | Send back to shorten to one line. |
| Brief item not implemented | Re-run that unit. |
| Ambiguous | Decide from the brief; if still unclear, ask the user. |

Two fix rounds maximum, then hand the remaining issue to the user with evidence.

## 5. Honest reporting

State what was run and what it returned. If a test failed, was not run, or a unit
ended `BLOCKED`, the final message says exactly that. A clean-looking summary over a
skipped check defeats the purpose of the pipeline.
