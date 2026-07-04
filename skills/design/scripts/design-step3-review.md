# design-step3-review.sh

## Purpose

Wrapper for a `/design` Bash block that keeps `skills/design/SKILL.md` free of inline Bash.

## Primary callers

- `skills/design/SKILL.md`

## Invariants

- Writes `$DESIGN_TMPDIR/.bg-wait-active` after pause-save checks and removes it on exit so hook enforcement covers the immediate-background wait. The marker copies `CLONE_PATH` from sibling `.larch-keepalive` when available; marker setup remains best-effort.
- Accepts `--session-env-path` from the prompt-side Bash call.
- Accepts `--claude-pid` when the wrapped logic must refresh session state.
- Accepts `--starting-round N` for mid-loop resumes and forwards it to `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" plan-review run --mode loop`.
- Accepts `--read-result-env` for a hook-safe recovery read, delegated to `python/cli.py plan-review normalize-status --read-result-env`. The read mode directly stats `$DESIGN_TMPDIR/.step3-review-result.env`, uses a simple line scan for `READ_RESULT_ENV_STATUS=ok|missing` plus the seven follow-up KVs, and never calls `read_result_env_main`. It exits 0 without writing the `.bg-wait-active` marker or dispatching the review.
- Validates resume-state flags and starting-round bounds before writing state.
- Calls without `--phase`, `--findings-file`, or `--postplan-operator-continue` preserve the existing first-entry pause ordering before review launch.
- Calls with resume-state flags write validated phase, findings env, or postplan continue state before pause-save.
- Launches `plan-review run --new-process-group` so Python calls `os.setsid()` before reviewer children start; the wrapper immediately records the loop pid's process identity in `$DESIGN_TMPDIR/.step3-loop-identity.json` through `python/cli.py plan-review write-loop-identity`. The wrapper passes `--new-process-group` to both the fresh and resume (`--starting-round`) launch paths. Redirects the plan-review loop process's own stderr to a dedicated `$DESIGN_TMPDIR/plan-review-loop-stderr.log` so the worker's and reviewer children's stderr never reaches the task output stream. There is no longer a `bash-job-control.log` redirect or `set -m` invocation because monitor mode is not used. normalize-status reads the stdout-file plus loop-rc only, so the stderr redirect drops no data the orchestrator consumes.
- Trap-time cleanup delegates loop process-group termination to `python/cli.py plan-review teardown-loop-identity`, which validates the sidecar's pid, pgid, start time, and command signature before signaling and fails closed if the sidecar is absent or mismatched. After normal `wait`, the wrapper removes the sidecar and does not signal the reaped pid.
- Performs best-effort cleanup for any remaining process whose argv references `$DESIGN_TMPDIR` after loop shutdown.
- The tmpdir process cleanup pass is allowed to fail silently.
- Clears stale `.completed/step-3-terminal` and `.step3-terminal-persisted-this-run` before writing the immediate-background marker.
- Guarantees the Step 3 completion sentinel `.completed/step-3` on every terminal exit after the review path is entered, via `_step3_review_guarantee_completed_sentinels` (loop-cleanup trap atomically replaced by a dedicated post-loop `EXIT` trap in a single assignment, so no window exists where no `EXIT` trap is registered — #4724). The poll guard gates on `.completed/step-3-terminal`, which the loop writes after result-envelope persist; the wrapper trap may write `step-3-terminal` only when the current-pass persist sidecar exists. A stale `.step3-review-result.env` alone is not enough. Writes **only** `step-3`, never `.completed/step-3.5`: `step-3.5` is a deferred Gate C / pause-resume gate (`design_pause.py`, the Gate B post-apply idempotency guard, `design-step3b-entry.sh`), and creating it here would skip Gate B on apply-pending exits. The write is idempotent and best-effort and never alters the exit status. The `--read-result-env` and pause-save paths return before the trap is installed, so they never write the sentinel (#4489).
- This wrapper is not a state-only helper. A call with resume flags also resumes the Step 3 loop after pause-save.
- Sites that previously wrote phase state and then launched review separately must collapse to one wrapper invocation at the resume boundary.
- `awaiting-vote` remains an internal loop state and is not accepted as a wrapper resume phase.
- Does not derive the root Claude PID from `$PPID` internally.
- Step 3 loop contract lives in `python/plan_review.py`. This wrapper captures stdout and delegates post-loop status normalization to `python/cli.py plan-review normalize-status`, which reads the quoted temp env via `load_bash_quoted_env` after a quiet in-process `read_result_env_main` call.
- The normalizer owns the WARN/ERROR replay contract: quiet `read_result_env_main` leaks no replay lines, Stage 1 replays `WARN=` / `ERROR=` from the selected source once, and Stage 2 replays stdout-overlay `WARN=` lines only when the primary result env is regular.
- The normalizer guards status mapping: it back-maps `LOOP_STATUS` to `STEP3_REVIEW_LOOP_STATUS` only when the latter is unset, then forward-maps canonical `LOOP_STATUS` from a persisted `STEP3_REVIEW_LOOP_STATUS`.
- The normalizer emits and persists `NEXT_ACTION` before raw status fields so prompt-side routing does not reconstruct the Step 3 branch matrix.
- Post-loop `**⚠ Step 3:` markdown warnings are emitted on stderr by the normalizer. Machine stdout remains the canonical KV envelope. Loop-end `SUMMARY_OUTCOME` KVs are emitted by the normalizer, not by this Bash wrapper.
- `bash-job-control.log` is no longer produced. Monitor mode (`set -m`) is not used. The worker's process group is set by Python via `os.setsid()` through `--new-process-group`.
- Refuses to launch when `$DESIGN_TMPDIR/plan-review-scope-anchor.txt` is absent, empty, or invalid. That prelaunch path emits `panel-init-failed`, stages `failed-judge-panel`, and exits non-zero so Gate C and Step 5 cannot run with zero reviewer coverage.
- Normalizes `panel-failed` with zero completed rounds or no `plan-review/round-1/` directory to `panel-init-failed`.
- The Python normalizer synthesizes a terminal `.step3-review-result.env` and the `.step3-terminal-persisted-this-run` marker when a terminal failure status (`panel-failed` / `panel-init-failed` / `tally-error` / `degraded-empty-collector` / `postplan-failed`) is resolved but the plan-review loop never persisted a result env. Without it the guarantee trap cannot mint `.completed/step-3` and the orchestrator's Step 3 foreground recovery probe never resolves. Apply-pending / vote / operator statuses are excluded so the synthesized sentinel never skips Gate B (#4724).

## Harness

Covered by `scripts/test-design-structure.sh`, `skills/design/scripts/test-design-step3-review.sh`, and relevant `/design` script checks.

## KV-only postplan failure

When `STEP3_REVIEW_LOOP_STATUS=postplan-failed`, the Python normalizer emits `SUMMARY_OUTCOME=failed-postplan` and exits non-zero. The wrapper propagates that exit code. It does not print final-summary prose; prompt-side orchestration runs the Final summary block.
