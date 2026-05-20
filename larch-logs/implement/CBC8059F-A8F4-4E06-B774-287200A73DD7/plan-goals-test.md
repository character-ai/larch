## Goal
Add emit_breadcrumb calls to ship-pr.sh, dispatch-panel.sh, review-core.sh, and review-and-fix.sh for operator visibility

## Implementation Plan

Add progress breadcrumbs to ship-pr.sh and the review/review-and-fix tree so operators can see activity during long-running /implement runs.

### Changes

**Plumbing — export env var:**
1. `skills/implement/SKILL.md` (Step 8+ block): add `export LARCH_QUIET_BREADCRUMBS=1` after `export CLAUDE_PLUGIN_ROOT` and before the ship-pr.sh invocation
2. `scripts/run-step5-review.sh`: add `export LARCH_QUIET_BREADCRUMBS=1` before the review-and-fix.sh invocation

**scripts/ship-pr.sh — 14 emit_breadcrumb calls:**
- A.1 phase-entry: mark_stall, exit_transient_net, run_checks_phase, run_bump_phase, run_pr_prep_phase, run_pr_create_phase, run_ci_phase, run_postmerge_phase, run_ci_fix_vendor, run_rebase_rebump
- A.2 phase-exit success: PR opened (after state_set_many PR_NUMBER), CI green (after state_set CI_PASSED true), merged (before rename_done_best_effort)
- A.4 rebase snag: conflict on rebase (before non-transient exit_stall in elif branch)

**skills/review/scripts/dispatch-panel.sh — 1 breadcrumb:**
- Panel composition summary after static+dynamic slots finalized, before waterfall dispatch

**skills/review/scripts/review-core.sh — 1 breadcrumb:**
- Before "$COLLECT_FINDINGS_SH" invocation (line 342)

**skills/review-and-fix/scripts/review-and-fix.sh — 6 breadcrumbs:**
- D.1: round entry (before round_dir=), round summary (after write_rejected_findings_aggregate), dispatching coder (before run_coder_dispatch), coder applied (after commit_sha)
- D.2: coder dispatch failed (before return 1 in run_coder_dispatch), panel failed (in panel-failed case)

**Tests:**
- scripts/test-ship-pr.sh: 3 assertions (phase entry with LARCH_QUIET_BREADCRUMBS=1, stall, transient)
- skills/review-and-fix/scripts/test-review-and-fix.sh: 2 assertions (round entry, dispatching coder)

**Sibling .md updates:**
- scripts/ship-pr.md, skills/review/scripts/dispatch-panel.md, skills/review/scripts/review-core.md, skills/review-and-fix/scripts/review-and-fix.md, scripts/lib-quiet.md

**Verification:** make lint-bash32, make test-ship-pr, make test-review-and-fix, /relevant-checks

## Test plan
(no test plan section in plan-file)
