# design-step3-review.sh

## Purpose

Wrapper for a `/design` Bash block that keeps `skills/design/SKILL.md` free of inline Bash.

## Primary callers

- `skills/design/SKILL.md`

## Invariants

- Writes `$DESIGN_TMPDIR/.bg-wait-active` after pause-save checks and removes it on exit so hook enforcement covers the immediate-background wait.
- Accepts `--session-env-path` from the prompt-side Bash call.
- Accepts `--claude-pid` when the wrapped logic must refresh session state.
- Accepts `--starting-round N` for mid-loop resumes and forwards it to `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" plan-review run --mode loop`.
- Validates resume-state flags and starting-round bounds before writing state.
- Calls without `--phase`, `--findings-file`, or `--postplan-operator-continue` preserve the existing first-entry pause ordering before review launch.
- Calls with resume-state flags write validated phase, findings env, or postplan continue state before pause-save.
- Performs two cleanup passes after loop shutdown: first kill the loop process
  group, then best-effort kill any remaining process whose argv references
  `$DESIGN_TMPDIR`.
- The tmpdir process cleanup pass is allowed to fail silently.
- This wrapper is not a state-only helper. A call with resume flags also resumes the Step 3 loop after pause-save.
- Sites that previously wrote phase state and then launched review separately must collapse to one wrapper invocation at the resume boundary.
- `awaiting-vote` remains an internal loop state and is not accepted as a wrapper resume phase.
- Does not derive the root Claude PID from `$PPID` internally.
- Step 3 loop contract lives in `python/plan_review.py`; this wrapper captures stdout, reads `.step3-review-result.env` through `scripts/read-result-env.sh`, overlays the full allowlisted KV envelope from captured stdout when needed, normalizes `STEP3_REVIEW_LOOP_STATUS` / `LOOP_STATUS`, and records escalation evidence only for terminal degradation statuses.

## Harness

Covered by `scripts/test-design-structure.sh`, `skills/design/scripts/test-design-step3-review.sh`, and relevant `/design` script checks.

## KV-only postplan failure

When `STEP3_REVIEW_LOOP_STATUS=postplan-failed`, this wrapper emits `SUMMARY_OUTCOME=failed-postplan` and exits non-zero. It does not print final-summary prose; prompt-side orchestration runs the Final summary block.
