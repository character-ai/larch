# Review Round 2

- Mode: `diff`
- 4 accepted, 3 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Step 5c bg-wait marker creation is fail-closed under set -e
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-hook-enforcement-output.txt, dyn-design-wait-contract-output.txt
- **Severity**: important
- **Concern**: `design-step5c.sh` calls `design_bg_wait_marker_start` without `|| true` while the helper lacks the fail-soft `|| return 1` guards used in `design-step3-review.sh` and `design-step-final-summary.sh`. Under `set -euo pipefail`, a full/read-only `DESIGN_TMPDIR` or permission glitch during `.bg-wait-active` write/`mv` aborts Step 5c before `design-publish.sh`, so Gate C publish and `[DESIGNED]` rename never run even though the plan requires marker failure not to break `/design`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Mirror design-step3-review.sh: add || return 1 in the helper and call design_bg_wait_marker_start design-step5c || true.
  - From cursor-specialist-edge-cases-output.txt: Match step3/final-summary: add || return 1 on tmp write/mv inside design_bg_wait_marker_start and call design_bg_wait_marker_start design-step5c || true.
  - From cursor-specialist-testing-output.txt: Mirror design-step3-review.sh: add || return 1 inside the helper, call design_bg_wait_marker_start design-step5c || true, and pin the || true in test-design-structure.sh.
  - From dyn-hook-enforcement-output.txt: Match Step 3/final-summary: `design_bg_wait_marker_start design-step5c || true`, log a warning, and continue publish.
  - From dyn-design-wait-contract-output.txt: Match the other wrappers: add `|| return 1` inside `design_bg_wait_marker_start` and call `design_bg_wait_marker_start design-step5c || true` so publish continues when the guard cannot be armed.


### FINDING_11: design-step-final-summary.sh missing pause-before-marker gate
- **Reviewer(s)**: dyn-design-wait-contract-output.txt
- **Severity**: important
- **Concern**: Unlike `design-step3-review.sh` and `design-step5c.sh`, `design-step-final-summary.sh` has no `.pause-requested` check before creating `.bg-wait-active` and running `render-final-summary.sh`. A pause during the cancellation Final summary immediate-background wait cannot be honored until render completes, breaking the pause-before-marker contract used elsewhere.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-design-wait-contract-output.txt: Add the same `[ -f "$DESIGN_TMPDIR/.pause-requested" ] && exec ... design-pause-save.sh` gate immediately before `design_bg_wait_marker_start`, consistent with the other immediate-background wrappers.


### FINDING_2: Corrupt marker during candidate scan fail-opens entire hook
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-hook-enforcement-output.txt, dyn-design-wait-contract-output.txt
- **Severity**: important
- **Concern**: In `hook-bg-poll-guard.sh`, when `marker_is_live` returns `2` (parse/canonicalize failure), the marker scan hits `*) exit 0 ;;` and fail-opens the entire hook. If `find` returns a malformed `.bg-wait-active` before a live marker, one corrupt stale marker under `~/.cache/larch/sessions` disables all PreToolUse denials for that session even when another valid marker exists and its wrapper PID is still running.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: On marker_rc=2 continue to the next candidate; deny only when no live markers remain after the full scan.
  - From dyn-hook-enforcement-output.txt: Treat return `2` like return `1` (skip that marker only). Reserve global fail-open for unexpected hook/runtime failures, not per-marker parse errors.
  - From dyn-design-wait-contract-output.txt: On rc `2`, skip only that marker (optionally reap it), continue scanning other candidates, and deny when any remaining marker is live; reserve global fail-open for hook-runtime faults, not per-marker parse errors.


### FINDING_8: Hook misses $SESSION_TMPDIR alias as probe target
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: `bash_has_probe_target` recognizes `$DESIGN_TMPDIR` / `${DESIGN_TMPDIR}` but not `$SESSION_TMPDIR` / `${SESSION_TMPDIR}`, even though `/design` exports `SESSION_TMPDIR` to the same directory as `DESIGN_TMPDIR`. During a live marker, `ls "$SESSION_TMPDIR"` or `cat "$SESSION_TMPDIR/.step3-review-result.env"` has a probe verb but no recognized probe target, so the PreToolUse hook allows the same tmpdir polling the feature is meant to block.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Treat `$SESSION_TMPDIR` and `${SESSION_TMPDIR}` as equivalent probe targets beside `$DESIGN_TMPDIR`, and add a harness case for `live marker plus Bash ls "$SESSION_TMPDIR"`.


