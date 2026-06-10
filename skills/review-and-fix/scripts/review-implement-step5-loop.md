# review-implement-step5-loop.sh

Internal loop driver for `/implement` Step 5. Runs repeated `review-and-fix.sh` rounds, handles post-round status routing, checks captures, lint-fix repair, bulk-skip gating, and cap enforcement. Emits the `STEP5_REVIEW_STATUS` envelope consumed by `run-step5-review.sh`.

**Primary contract**: this file is authoritative for Step 5 loop envelopes emitted by `review-implement-step5-loop.sh`: `STEP5_REVIEW_STATUS` is one of `complete`, `cap-hit`, `stall`, `main-agent-vote-required`, `coder-main-agent-required` (#3207: Cursor → Codex both exhausted this round; the Step 5 orchestrator applies the accepted fixes via main-agent Edit/Write — the Claude tier of the coder waterfall), or `mav-resume-past-cap`; `STALL_TRACKING=true` means the orchestrator may rename the tracking issue to `[STALLED]`, while `STALL_TRACKING=false` preserves non-stalled cleanup flow.

**Lint-fix cap re-verify (#3592 bug a)**: when the `lint_attempts` counter reaches `lint_max` in the `applied` branch, the loop runs one final captured-checks pass before emitting `lint-fix-attempt-cap`. If that final pass reports clean (`RELEVANT_CHECKS_OK=true` or `RELEVANT_CHECKS_SKIPPED=true`), the loop breaks out of the lint inner loop and continues the main loop as if checks had passed — the stall is avoided. Only when the re-verify also fails does the loop emit the `lint-fix-attempt-cap` stall.

**Callers**: `scripts/run-step5-review.sh` (sources this file and calls `step5_review_loop`)

`step5_parse_kv_tokens` always exits status 0 so `set -e` callers can safely use `v="$(step5_parse_kv_tokens "$line" KEY)"`; a missing key is signaled by empty stdout (after command substitution strips the lone newline), not a non-zero exit. After reading a capture file, `step5_parse_checks_capture_file` requires at least one of `STATUS`, `RELEVANT_CHECKS_OK`, or `RELEVANT_CHECKS_SKIPPED` to have been set; otherwise it logs a required-field line to stderr and fail-closes with `STATUS=fail` and `FAILURE_REASON=malformed-capture`. `step5_parse_lint_capture_file` logs a similar stderr line when `LINT_FIX_STATUS` was never seen but does not force globals—the loop’s `case` on lint status treats empty as the catch-all stall path.

## Starting-round resume

At loop entry, `run_implement_loop` uses the flat `ROUND_CAP` value as the effective cap (5 from `/implement` Step 5) before validating the prior-round artifact. If `STARTING_ROUND > cap`, the loop emits `mav-resume-past-cap` only when the immediately previous `round-N/review-and-fix.env` exists. That artifact anchor prevents arbitrary high `--starting-round` values from being silently treated as success.

When the previous artifact is required but not visible, `step5_probe_prior_round_env` checks once, runs `sync >/dev/null 2>&1 || true`, then checks once more. This is a bounded best-effort retry for just-written files; `sync` is not a guaranteed cache-invalidation barrier.

If both probes miss, the loop emits one diagnostic line with `IMPLEMENT_TMPDIR`, `STARTING_ROUND`, `expected_env_path`, and `base_cap`, then returns a `stall` envelope with `STALL_REASON=starting-round-invalid` and `STALL_TRACKING=false`. The orchestrator must not rename the tracking issue to `[STALLED]` for that stall reason, but it still needs to persist that `STALL_TRACKING=false` decision into Step 18's durable state: rewrite the existing `ship-pr-state.sh` when present, or seed the minimal Step-8-shape `ship-pr-state.sh` — key list in `skills/implement/SKILL.md` Step 5, stall branch body in `skills/implement/references/step5-review-branches.md` — before jumping to cleanup.

## Pre-coder head and structural-diff telemetry

Bulk-skip and substantial-round gates read `pre-coder-head.txt` from `pre_coder_snapshot_dir "$post_round_dir"` (defined in `review-and-fix.sh`) and `post-coder-head.txt` from `$post_round_dir`. `run_implement_mav_apply` clears stale snapshot artifacts, writes only `pre-coder-head.txt` into that snapshot dir before coder dispatch, then `chmod 0444` the head file; it does **not** call `snapshot_pre_coder_tracked_state`, so MAV rounds keep the same head-only carryover behavior as before relocation. `post-coder-head.txt` is written and chmod'd only when `CODER_STATUS=applied`.

The loop records one best-effort timing `round` row per completed in-loop Step 5 round. Handoff statuses (`main-agent-vote-required`, `coder-main-agent-required`) persist `round-start-s` under `round-N/` and defer emission to the Step 5 orchestrator after prompt-side adjudication/application and checks.

## Prune-skipped rounds

`prune-skipped` is handled before fix/substantiality and convergence gates. Below the fixed round cap, the loop records timing, increments `round_num`, and continues so the round-5 full-panel re-probe remains reachable. At the cap boundary it emits the normal complete envelope. The status is not a convergence candidate and is not classified as degraded.
