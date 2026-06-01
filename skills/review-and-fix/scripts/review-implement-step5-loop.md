# review-implement-step5-loop.sh

Internal loop driver for `/implement` Step 5. Runs repeated `review-and-fix.sh` rounds, handles post-round status routing, checks captures, lint-fix repair, bulk-skip gating, and cap enforcement. Emits the `STEP5_REVIEW_STATUS` envelope consumed by `run-step5-review.sh`.

**Primary contract**: this file is authoritative for Step 5 loop envelopes emitted by `review-implement-step5-loop.sh`: `STEP5_REVIEW_STATUS` is one of `complete`, `cap-hit`, `stall`, `main-agent-vote-required`, `coder-main-agent-required` (#3207: Codex → Cursor both exhausted this round; the Step 5 orchestrator applies the accepted fixes via main-agent Edit/Write — the Claude tier of the coder waterfall), or `mav-resume-past-cap`; `STALL_TRACKING=true` means the orchestrator may rename the tracking issue to `[STALLED]`, while `STALL_TRACKING=false` preserves non-stalled cleanup flow.

**Callers**: `scripts/run-step5-review.sh` (sources this file and calls `step5_review_loop`)

`step5_parse_kv_tokens` always exits status 0 so `set -e` callers can safely use `v="$(step5_parse_kv_tokens "$line" KEY)"`; a missing key is signaled by empty stdout (after command substitution strips the lone newline), not a non-zero exit. After reading a capture file, `step5_parse_checks_capture_file` requires at least one of `STATUS`, `RELEVANT_CHECKS_OK`, or `RELEVANT_CHECKS_SKIPPED` to have been set; otherwise it logs a required-field line to stderr and fail-closes with `STATUS=fail` and `FAILURE_REASON=malformed-capture`. `step5_parse_lint_capture_file` logs a similar stderr line when `LINT_FIX_STATUS` was never seen but does not force globals—the loop’s `case` on lint status treats empty as the catch-all stall path.

## Starting-round resume

At loop entry, `run_implement_loop` computes the effective cap from `ROUND_CAP + count_prior_degraded_rounds(IMPLEMENT_TMPDIR, STARTING_ROUND)` before validating the prior-round artifact. If `STARTING_ROUND > entry_effective_cap`, the loop emits `mav-resume-past-cap` only when the immediately previous `round-N/review-and-fix.env` exists. That artifact anchor prevents arbitrary high `--starting-round` values from being silently treated as success.

When the previous artifact is required but not visible, `step5_probe_prior_round_env` checks once, runs `sync >/dev/null 2>&1 || true`, then checks once more. This is a bounded best-effort retry for just-written files; `sync` is not a guaranteed cache-invalidation barrier.

If both probes miss, the loop emits one diagnostic line with `IMPLEMENT_TMPDIR`, `STARTING_ROUND`, `expected_env_path`, `base_cap`, `entry_prior_deg`, and `entry_effective_cap`, then returns a `stall` envelope with `STALL_REASON=starting-round-invalid` and `STALL_TRACKING=false`. The orchestrator must not rename the tracking issue to `[STALLED]` for that stall reason, but it still needs to persist that `STALL_TRACKING=false` decision into Step 18's durable state: rewrite the existing `ship-pr-state.sh` when present, or seed the minimal Step-8-shape `ship-pr-state.sh` described in `skills/implement/SKILL.md` Step 5 before jumping to cleanup.

## Pre-coder head and structural-diff telemetry

Bulk-skip and substantial-round gates read `pre-coder-head.txt` from `pre_coder_snapshot_dir "$post_round_dir"` (defined in `review-and-fix.sh`) and `post-coder-head.txt` from `$post_round_dir`. `run_implement_mav_apply` clears stale snapshot artifacts, writes only `pre-coder-head.txt` into that snapshot dir before coder dispatch, then `chmod 0444` the head file; it does **not** call `snapshot_pre_coder_tracked_state`, so MAV rounds keep the same head-only carryover behavior as before relocation. `post-coder-head.txt` is written and chmod'd only when `CODER_STATUS=applied`.
