## Goal
Implement issue #4110: [IMPLEMENTING] [Bug] /design Step 3 poll loop leaves background task registered, blocks session exit.

## Implementation Plan
## Plan

Make the minimum doc and harness change.

- Strengthen both `/design` Step 3 immediate-background wait instructions.
- Add one shared NEVER rule for `run_in_background` result-file sleep loops.
- Extend the existing anti-polling harness to pin the new literals.
- Require the `/design` Step 3 literal to appear exactly twice, so both initial and resume fences are covered.
- Update the harness companion doc.

No runtime behavior changes.

## Files to modify/create

### UPDATED: skills/design/SKILL.md

Replace both Step 3 wait lines:

- Initial `design-step3-review.sh` fence.
- Resume `design-step3-review.sh --starting-round` fence.

Use this byte-identical literal at both sites:

- ``NEVER poll `.step3-review-result.env` with a sleep loop.``

Use the same consequence statement at both sites:

- Polling bypasses Claude Code task lifecycle.
- It can leave the task registered as running.
- It can block session exit until `TaskStop`.
- Wait for `<task-notification>` unconditionally before parsing stdout or reading `.step3-review-result.env`.

Keep the immediate-background fence text unchanged.

### UPDATED: skills/shared/orchestrator-never.md

Append item `4.` to the NEVER list.

Use the existing format:

- `**NEVER ...**`
- `**Why**:`
- `**How to apply**:`
- `**CI-backed**: yes — ...`

Pin this rule with this byte-identical literal:

- ``NEVER poll a `run_in_background` result file with a Bash sleep loop.``

Include these consequences:

- The task stays registered as running until `<task-notification>` fires.
- Polling that finds the result file first can leave a dangling task handle.
- The handle can block session exit.

Reference `scripts/test-implement-anti-polling-rule.sh` as the CI pin.

### UPDATED: scripts/test-implement-anti-polling-rule.sh

Extend the harness without renaming it.

Add paths:

- `DESIGN_MD="$REPO_ROOT/skills/design/SKILL.md"`
- `ORCH_NEVER_MD="$REPO_ROOT/skills/shared/orchestrator-never.md"`

Add file-existence checks for both.

Add pinned literals:

- `STEP3_LITERAL='NEVER poll `.step3-review-result.env` with a sleep loop.'`
- `ORCH_NEVER_LITERAL='NEVER poll a `run_in_background` result file with a Bash sleep loop.'`

Add a count assertion for `/design` Step 3:

- Use `grep -cF -- "$STEP3_LITERAL" "$DESIGN_MD"`.
- Assert the count is exactly `2`.
- Fail with a message that names both required sites: initial Step 3 and resume `--starting-round`.

Add a normal `check` call for the shared NEVER literal:

- `check "$ORCH_NEVER_MD" "$ORCH_NEVER_LITERAL"`

Update top comments so they describe all pinned surfaces, not only `AGENTS.md` and `skills/implement/SKILL.md`.

### UPDATED: scripts/test-implement-anti-polling-rule.md

Update the purpose and invariants.

Mention that the harness now also pins:

- `/design` Step 3 consequence prose.
- The exact count of `2` for the `/design` Step 3 literal.
- The shared orchestrator NEVER rule for `run_in_background` result-file sleep loops.

Keep the existing Makefile wiring and manual run instructions.

## Edge cases

- Update both Step 3 fences. A resume path must not retain the weaker instruction.
- Keep the `/design` prose and harness literal byte-identical.
- Use `grep -F`-safe literals. Avoid regex-only test expectations.
- Do not edit `AGENTS.md`. The approved outline excludes it.
- Do not add runtime gates, retries, or cleanup logic.

## Failure modes

- If only one Step 3 fence changes, the exact-count assertion fails.
- If the harness literal differs by case or punctuation from the docs, CI fails.
- If the shared NEVER item says `CI-backed: yes` but the harness does not pin it, the claim is false.

## Testing strategy

Run:

- `bash scripts/test-implement-anti-polling-rule.sh`
- `make test-implement-anti-polling-rule`
- `bash scripts/relevant-checks.sh`

For final verification, grep the two new literals in:

- `skills/design/SKILL.md`
- `skills/shared/orchestrator-never.md`

Also verify the `/design` literal count:

- `grep -cF -- 'NEVER poll `.step3-review-result.env` with a sleep loop.' skills/design/SKILL.md`

## Acceptance

Changes are complete when:

- Both Step 3 SKILL.md fences carry the byte-identical NEVER-poll consequence statement.
- `orchestrator-never.md` item 4 is present with NEVER/Why/How to apply/CI-backed format.
- `test-implement-anti-polling-rule.sh` asserts exact count = 2 for the Step 3 literal AND checks the orchestrator-never.md literal.
- `bash scripts/test-implement-anti-polling-rule.sh` exits 0.
- `bash scripts/relevant-checks.sh` exits 0.

diff_lines: 30

## Test plan
(no test plan section in plan-file)
