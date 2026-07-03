## Goal
Implement issue #6112: [IMPLEMENTING] [BUG] When /design is run without -s, it should not time out asking for questions or asking for approval after 60 seconds, but wait for answers indefinitely.

## Implementation Plan
## Plan

## Approach

Add a local `/design` prompt-contract rule, not a new helper.

- In `skills/design/SKILL.md`, add anti-pattern rule 6.
- State that an `AskUserQuestion` no-response fallback is not an answer.
- Require the orchestrator to re-fire the identical `AskUserQuestion` call, uncapped.
- For repeat retries, stay quiet unless the prompt body itself must be shown by the tool.
- Do not treat terse real answers as no-response fallbacks. Keep the existing `discussion-rounds.md` guidance for terse answers.
- Keep the change local to `/design`.

Keep the design skill closure ratchet green.

- Add the new rule as compact prose.
- If `python3 python/cli.py lint skill-closure-growth --skill design` fails, trim nearby `skills/design/SKILL.md` anti-pattern prose without removing pinned literals.
- Do not update `python/skill-closure-baseline.json`; the approved scope only covers `skills/design/SKILL.md` and `scripts/test-design-structure.sh`.

## Files to modify/create

### UPDATED: skills/design/SKILL.md

Add a sixth rule under `## Anti-patterns`, after rule 5.

Suggested content shape:

- `6. **NEVER treat an AskUserQuestion no-response fallback as an operator answer.**`
- Why: the platform can return a 60-second fallback when the operator has not answered.
- How to apply: when the returned text is the no-response fallback, do not choose an option, infer consent, infer cancellation, or use “best judgment.” Re-fire the identical `AskUserQuestion` call. Retry without a cap. Keep repeat retries quiet.

Preserve existing AskUserQuestion branches. This rule governs orchestration after the tool returns.

### UPDATED: scripts/test-design-structure.sh

Add one `contains "$SKILL_MD" ...` assertion near the existing anti-pattern pins.

Pin a stable literal from the new rule, for example:

- `NEVER treat an AskUserQuestion no-response fallback as an operator answer`
- `Re-fire the identical \`AskUserQuestion\` call`
- `Retry without a cap`

Use the same `contains` helper and failure-message style as the existing anti-pattern checks.

## Edge cases

- A real terse answer, such as “sure” or “your recommendation is fine,” remains valid where existing instructions say to accept terse answers.
- `--skip-approve` still skips only Step 1d.7 and Gate C prompts. Other prompts still re-ask on no-response fallback.
- “See full plan” and similar re-prompt loops keep their current behavior. The new rule only intercepts no-response fallback returns.
- Cancel, Abort, Override, Split, and approval choices must still be honored when the operator actually chooses them.

## Failure modes when non-trivial

- The new rule may be too narrow if it names only one exact fallback string. Avoid this by describing the no-response fallback semantically and pinning a stable rule literal, not the whole platform message.
- The design skill closure ratchet may fail because `skills/design/SKILL.md` grows. Keep the new prose compact and trim nearby non-pinned prose if needed.
- A future maintainer may apply the rule only to `--skip-approve`-gated prompts. The rule must say every `/design` `AskUserQuestion` call site.

## Testing strategy

Run targeted checks only:

1. `python3 python/cli.py lint skill-closure-growth --skill design`
2. `make test-design-structure`

If the structural test fails on the new pin, adjust only the test literal or nearby wording. If the closure ratchet fails, trim `skills/design/SKILL.md` prose and rerun both commands.

## Acceptance

Run targeted checks only:

1. `python3 python/cli.py lint skill-closure-growth --skill design`
2. `make test-design-structure`

If the structural test fails on the new pin, adjust only the test literal or nearby wording. If the closure ratchet fails, trim `skills/design/SKILL.md` prose and rerun both commands.

diff_lines: 12

## Test plan
(no test plan section in plan-file)
