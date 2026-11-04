# Brief: <short title>

> Written by the orchestrator, approved by the user. Agents implement this file and
> nothing else. Anything not listed under "In scope" is out.

## Requirement
<the user's requirement, quoted or closely paraphrased, with the source (ticket/spec path)>

## Decisions (user answers, verbatim)
| # | Question | Answer | Source |
|---|----------|--------|--------|
| 1 | | | user / requirement / code `file:line` |

## Assumptions (only if the user deferred a choice)
- <assumption> — followed existing pattern at `file:line`

## In scope
1. <behavior to deliver, traceable to the requirement or a decision above>
2. ...

## Out of scope
- <things nearby that must NOT be touched or added>

## Protected existing logic (must keep working unchanged)
- `file:line` — <behavior that must survive>

## Authorised replacements (empty unless the requirement replaces old behavior)
- `file:line` — <what is replaced, by which In-scope item>

## Work units
| Unit | Files (only these may be edited) | Delivers item(s) |
|------|----------------------------------|------------------|
| U1 | | 1 |

## Conventions to match
- <naming / layering / error handling / test style, with an example path>

## Acceptance checks
- Build/test command: `<command>`
- [ ] <observable check for item 1>
- [ ] <observable check for item 2>

## Noticed but not in scope (for the user to decide later)
- <idea or risk> — not implemented
