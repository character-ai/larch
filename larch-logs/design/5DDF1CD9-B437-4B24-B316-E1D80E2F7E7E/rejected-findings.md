### [Plan Review] FINDING_1

### FINDING_1: `_checks_rollup_empty` must consult text fallback before declaring rollup empty
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: `_checks_rollup_empty` must mirror the `_resolve_checks_status` empty-bucket branch and must not treat JSON bucket `empty` alone as rollup-empty. When `gh pr checks --json` returns `[]` but text output already lists in-flight checks, `_resolve_checks_status` classifies `pending`; a probe that keys only on JSON `empty` would keep accumulating the startup deadline and false-bail `NO_CHECKS` at ~300s while CI is still running.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In `_checks_rollup_empty`, after `_classify_checks_json` returns `empty`, read `_read_pr_checks_text` and return `False` when stripped text is non-empty (same order as `_resolve_checks_status`); add a unit test for JSON `[]` plus non-empty text -> `False`


### [Plan Review] FINDING_2

### FINDING_2: `initial_startup_deadline_available` must be armed once before the merge loop
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: `initial_startup_deadline_available` must be armed once before the merge `while True`, not re-derived each iteration. If the flag is initialized inside the loop body with an all-zero-counter guard, any later iteration that still has zero counters (for example `evaluate_failure` OK without bumping `iteration`/`fix_attempts`) would re-arm the 300s startup window after the post-first-monitor clear, repeating bounded `NO_CHECKS` stalls on benign re-polls.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Initialize `initial_startup_deadline_available` once immediately before `while True` when entry counters are all zero; clear only after each `monitor()` return; add a ship test where counters stay zero across two iterations and the second `monitor()` sees startup deadline `0`


