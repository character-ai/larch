### OOS_1: Investigate breadcrumb-monitor early-exit cascade in /implement Step 5
- **Description**: During an /implement run for #2962, the orchestrator's `breadcrumb-monitor.sh` exited after only ~4 breadcrumbs (through "→ review: launching 9 reviewers") before the 4-minute gap to "→ review: consolidating findings". This caused the orchestrator to think `review-and-fix.sh` had completed (status `main-agent-vote-required`) while the script was still running in background. The orchestrator then ran redundant MAV adjudication and a concurrent round 2.

  Likely root cause (per Cursor-Edge sketch on #2973): `breadcrumb-monitor.sh` exits immediately when `LARCH_BREADCRUMBS_SURFACED_FILE` is non-empty, which `larch_quiet_init` writes when FD-3 is visible. Nested Family-B scripts (`collect-agent-results.sh`, `dispatch-with-waterfall.sh`, `review-and-fix.sh`) inherit the orchestrator's `LARCH_DONE_SENTINEL` / `LARCH_BREADCRUMBS_SURFACED_FILE` via env, and `larch_quiet_append_done_trap` plus the PID-keyed ownership check in `scripts/lib-quiet.sh:172` may not catch every nested re-ownership case.

  Suggested investigation paths (per Codex-Innovation and Codex-Pragmatic sketches on #2973):
  - Give nested Family-B scripts private sentinels by unsetting `LARCH_DONE_SENTINEL` / `LARCH_BREADCRUMBS_SURFACED_FILE` before synchronous nested calls unless the caller is the orchestrator-paired process.
  - Alternative: at `scripts/run-step5-review.sh` (around line 189), invoke `review-and-fix.sh` with `LARCH_DONE_SENTINEL` / `LARCH_STATUS_FILE` hidden from the child while preserving them in the parent, so only `run-step5-review.sh` signals the monitor.
  - Add focused harness coverage: a Step 5 wrapper test where a nested child writes a done sentinel early but the monitor remains blocked until the wrapper exits.

  This OOS was deferred from #2973 per Round 1 Decision 1 (defer monitor scope; voter `.done` wait + Codex stdin fix are sufficient defense-in-depth for the immediate failure modes).
- **Reviewer**: main-agent (round 1 scope decision)
- **Phase**: design
- **Filed URL**: https://github.com/character-ai/larch/issues/3005
