# Clarifying questions — how to ask well

Read this in Phase 3. The goal is the fewest questions that remove every guess from the
implementation. A good question saves a rewrite; a bad one wastes the user's attention.

## Ask only when all three are true

1. The answer **changes what code is written** (behavior, contract, data, scope).
2. Neither the requirement **nor the code** answers it. (Check the scout report first.)
3. A wrong guess would be **costly to undo** or **silently wrong**.

If the code already settles it (naming, error-handling style, which helper to call),
follow the code and do not ask.

## Where gaps usually hide

| Area | Example gap |
|------|-------------|
| Behavior | What should happen on empty / null / duplicate / over-limit input? |
| Existing logic | Does the new rule *replace* the old branch or apply *alongside* it? |
| Contract | Is the response/field/column name fixed, or mine to choose? Is the change allowed to alter a public signature? |
| Data | Is a schema/migration change acceptable, or must it fit existing columns? |
| Errors | Which failure surfaces to the caller, which is logged and swallowed? |
| Compatibility | Must old callers/clients/data keep working? |
| Scope edges | The requirement says "X"; does it also include the sibling case "Y"? |
| Source conflict | Spec says one thing, code (or another document) says another — which wins? |
| Tests | Which tests are expected: unit, integration, none? |
| Done criteria | How will the user check it works? |

## Question format

Each question stands alone — the user may see only the dialog. Include:
- **What you found**, with `file:line` ("`OrderService.cs:88` rejects negative totals").
- **The decision needed**, as one sentence.
- **2–4 concrete options**, each with its consequence in a few words.
- **Your recommendation**, first in the list and marked "(Recommended)", with the reason.

Good:
> `Cart.cs:52` returns silently when the coupon is expired. For the new rule, should an
> expired coupon (a) keep returning silently, (b) throw `CouponExpiredException`, or
> (c) return a validation message? Recommend (c): matches `Checkout.cs:120`.

Bad:
> How should I handle errors?

## Mechanics

- Batch independent questions into one `AskUserQuestion` call (up to 4). Ask dependent
  questions in a later round.
- Do not bundle a question with "or whatever you think" — you are the one who is meant
  to propose a default; the user confirms or corrects it.
- Put long context (a spec excerpt, a table of cases) in the brief file and refer to it,
  rather than overloading the dialog.
- Record each answer **verbatim** in the brief's Decisions table. The implementor reads
  those, and they stop the same question being asked twice.
- If the user answers "you decide", pick the option that follows existing code, record
  it as an Assumption in the brief, and surface it in the final message.
- Stop asking when there are no remaining guesses. Saying "no open questions" is a
  valid and good outcome.
