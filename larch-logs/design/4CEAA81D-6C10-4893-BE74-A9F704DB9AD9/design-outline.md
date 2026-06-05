## Proposed Design Outline

### Goals
- Close all ~15 orphans in #3446 sections A–F in one combined SIMPLE plan.
- Make ship.py failure paths honor the JSON-stdout contract: argparse-failure envelope, redacted INTERNAL_ERROR detail, in-driver 3.11 guard, quiet-routing parity.
- Reconcile SKILL.md Step 8+ python-branch prose + pin the JSON-routing contract in tests; finish constant/context/test/doc cleanup (D, E) and the F nit.

### Non-goals
- No edits to bash ship-pr.sh / ship-pr-state.sh (frozen pre-Phase-7).
- No re-file/re-implement of the issue's "Excluded" items (already-fixed set; #3404 / #3448 / #3449).
- No change to the existing happy-path ship-result JSON contract bytes.

### Approach sketch
- B (ship.py): fold parse_args + early exits into the emit_result envelope (argparse failure → INTERNAL_ERROR exit 1, `--help`/exit-0 stays plain); redact the traceback + emit a specific INTERNAL_ERROR detail; add `sys.version_info >= (3,11)` guard emitting the STALLED-JSON shape; wire Python quiet-routing init to match ship-pr.sh.
- C: collapse duplicate per-poll CI breadcrumbs to one source; surface the run_logs RefreshSkip reason on degraded post-merge flush.
- D: remove unused EXIT_STALL (keep + annotate EXIT_BAIL); reconcile RunContext `forked`/`forked_target` + `branch`/`branch_name`; honor XDG_CACHE_HOME in both finalize cache-root allowlists; extract one shared RecordingRunner test helper; drop the bare pr_view_current wrapper.
- A/E/F: correct the SKILL.md python-branch prose (exit-4/exit-3/OOS read sources; the over-absolute "don't read ship-pr-state.sh" line); pin exit-code→action routing in test-implement-structure.sh; update docs/linting.md to the 3.11/3.12 matrix; pass `base=` from ensure_pr.
- Add a regression test for every behavioral change (Round 1).

### Surfaces in scope
- python/: ship.py, config.py, run_context.py, finalize.py, gh.py, pr.py, run_logs.py, ci_monitor.py (+ quiet/logging helper).
- python/test_*.py: new per-change tests + one shared RecordingRunner helper across ~11 files.
- skills/implement/SKILL.md (LARCH_SHIP_PR_IMPL=python branch); scripts/test-implement-structure.sh; docs/linting.md.

### Open questions
- None. Round 1 settled scope (all A–F, combined, Python+docs only), test depth, and the argparse-failure exit code.
