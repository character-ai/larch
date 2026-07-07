# design-step3-review.sh

## Purpose

Foreground bgjob launcher for the `/design` Step 3 plan-review loop, with an internal child mode that keeps `skills/design/SKILL.md` free of inline Bash.

## Primary callers

- `skills/design/SKILL.md`

## Invariants

- Accepts `--session-env-path` from the prompt-side Bash call.
- Accepts `--claude-pid` when the wrapped logic must refresh session state or pass the bgjob owner PID.
- Accepts `--starting-round N` for mid-loop resumes and forwards it to `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" plan-review run --mode loop` in the bgjob child.
- Accepts `--read-result-env` for a hook-safe compatibility read, delegated to `python/cli.py plan-review normalize-status --read-result-env`. The Python normalizer reads `$DESIGN_TMPDIR/bgjob/design-step3-review.result.env` first and falls back to `$DESIGN_TMPDIR/.step3-review-result.env` only when the bgjob result env is absent.
- Validates resume-state flags and starting-round bounds before writing state.
- Calls without `--phase`, `--findings-file`, or `--postplan-operator-continue` preserve the existing first-entry pause ordering before bgjob launch.
- Calls with resume-state flags write validated phase, findings env, or postplan continue state before pause-save.
- Before a fresh `bgjob start`, checks the identity-valid registry row for `design-step3-review`. A live row refuses a second start and routes the caller to `bgjob wait`; stale or dead rows are cleared before a fresh launch.
- Immediately before each fresh `bgjob start`, truncates `$DESIGN_TMPDIR/.step3-review-result.env` as the merge-result input and removes stale `$DESIGN_TMPDIR/bgjob/design-step3-review.result.env` so prior KVs cannot satisfy a new completion gate.
- Fresh launcher stdout is exactly one line: `BGJOB_STATUS=STARTED STEP=design-step3-review PGID=<n>`.
- The wrapper passes `--merge-result-env "$DESIGN_TMPDIR/.step3-review-result.env"` and sentinel `$DESIGN_TMPDIR/.completed/step-3-terminal` to `python/cli.py bgjob start`. The bgjob daemon writes `$DESIGN_TMPDIR/bgjob/design-step3-review.result.env`, which is the completion source of truth.
- The internal child runs `plan-review run --new-process-group --orphan-timeout-s 7200`; Python calls `os.setsid()` before reviewer children start and detached loops self-stop after the configured orphan bound.
- The child redirects the plan-review loop process's stderr to `$DESIGN_TMPDIR/plan-review-loop-stderr.log`; machine stdout remains the canonical KV envelope captured for normalization.
- Step 3 loop contract lives in `python/plan_review.py`. The child captures stdout and delegates post-loop status normalization to `python/cli.py plan-review normalize-status`, which reads the merge input through `load_bash_quoted_env` after a quiet in-process `read_result_env_main` call.
- The normalizer emits and persists `NEXT_ACTION` before raw status fields so prompt-side routing does not reconstruct the Step 3 branch matrix.
- Post-loop `**⚠ Step 3:` markdown warnings are emitted on stderr by the normalizer. Machine stdout remains the canonical KV envelope. Loop-end `SUMMARY_OUTCOME` KVs are emitted by the normalizer, not by this Bash wrapper.
- Refuses to launch the child when `$DESIGN_TMPDIR/plan-review-scope-anchor.txt` is absent, empty, or invalid. That prelaunch path emits `panel-init-failed`, stages `failed-judge-panel`, and exits non-zero so Gate C and Step 5 cannot run with zero reviewer coverage.
- Normalizes `panel-failed` with zero completed rounds or no `plan-review/round-1/` directory to `panel-init-failed`.
- The retained legacy `$DESIGN_TMPDIR/.step3-review-result.env` is a merge input and fallback only. Prompt-side continuation after bgjob migration must parse `$DESIGN_TMPDIR/bgjob/design-step3-review.result.env` first and require `BGJOB_RC=0` plus the route KVs.
- Compatibility sentinels remain: `.completed/step-3-terminal` is written by bgjob on child completion, and `.completed/step-3` is still owned by the Step 3 loop/normalizer. They are not sufficient for prompt-side continuation without the bgjob result env gate.
- This wrapper is not a state-only helper. A call with resume flags also starts or rejoins the Step 3 bgjob after pause-save.
- Sites that previously wrote phase state and then launched review separately must collapse to one wrapper invocation at the resume boundary.
- `awaiting-vote` remains an internal loop state and is not accepted as a wrapper resume phase.
- Does not derive the root Claude PID from `$PPID` internally.

## Harness

Covered by `scripts/test-design-structure.sh`, `skills/design/scripts/test-design-step3-review.sh`, and relevant `/design` script checks.

## KV-only postplan failure

When `STEP3_REVIEW_LOOP_STATUS=postplan-failed`, the Python normalizer emits `SUMMARY_OUTCOME=failed-postplan` and exits non-zero. The bgjob result env records that child rc in `BGJOB_RC`. The wrapper does not print final-summary prose; prompt-side orchestration runs the Final summary block after `DONE` parsing routes to that branch.
