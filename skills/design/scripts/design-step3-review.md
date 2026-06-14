# design-step3-review.sh

## Purpose

Wrapper for a `/design` Bash block that keeps `skills/design/SKILL.md` free of inline Bash.

## Primary callers

- `skills/design/SKILL.md`

## Invariants

- Writes `$DESIGN_TMPDIR/.bg-wait-active` after pause-save checks and removes it on exit so hook enforcement covers the immediate-background wait.
- Accepts `--session-env-path` from the prompt-side Bash call.
- Accepts `--claude-pid` when the wrapped logic must refresh session state.
- Accepts `--starting-round N` for mid-loop resumes and forwards it to `run-step3-review.sh --mode loop`.
- Validates resume-state flags and starting-round bounds before writing state.
- Calls without `--phase`, `--findings-file`, or `--postplan-operator-continue` preserve the existing first-entry pause ordering before review launch.
- Calls with resume-state flags write validated phase, findings env, or postplan continue state before pause-save.
- `run-step3-review.sh` still owns Step 3 review execution.
- This wrapper is not a state-only helper. A call with resume flags also resumes the Step 3 loop after pause-save.
- Sites that previously wrote phase state and then launched review separately must collapse to one wrapper invocation at the resume boundary.
- `awaiting-vote` remains an internal loop state and is not accepted as a wrapper resume phase.
- Does not derive the root Claude PID from `$PPID` internally.
- After merging `.step3-review-result.env` and captured child stdout, an empty `STEP3_REVIEW_LOOP_STATUS` is repaired from a valid recoverable `LOOP_STATUS` when possible.
- The legacy `LOOP_STATUS=zero-findings-degraded-panel` token is not newly mapped to `complete`.
- If no recoverable Step 3 loop status is available, the wrapper emits the missing-result warning to stderr and degrades to `panel-failed`.

## Harness

Covered by `scripts/test-design-structure.sh`, `skills/design/scripts/test-design-step3-review.sh`, and relevant `/design` script checks.

## KV-only postplan failure

When `STEP3_REVIEW_LOOP_STATUS=postplan-failed`, this wrapper emits `SUMMARY_OUTCOME=failed-postplan` and exits non-zero. It does not print final-summary prose; prompt-side orchestration runs the Final summary block.
