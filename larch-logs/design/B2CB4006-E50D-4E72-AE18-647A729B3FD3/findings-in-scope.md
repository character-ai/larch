### FINDING_1: `test-redact` stem-collision risk from unpinned catch-all
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: Per-file guidance slices `scrub_log_secrets` and `tmpdir`/`operator` but does not pin the `test-redact` recipe. Because the issue gotcha forbids stem-colliding `-k` tokens and the module stem is `test_redact.py`, an implementer can satisfy the illustrative families with `-k redact` (or another stem substring) on `test-redact`. Pytest then selects the whole module, leaving overlap with the other three redact targets and blocking `ENFORCED` sign-off (or preserving a hidden full-file payment).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Explicitly require `test-redact` use a `not (...)` catch-all over the other three selections (e.g. secret/parity/pem families), and add a Makefile preflight grep that `test-redact:` does not contain `-k redact`.

### FINDING_2: `test_implement_dispatch.py` `run_dispatch` vs `test-run-step2-dispatch` partition ambiguity
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: `run_dispatch` tests are assigned to the catch-all slice while `test-run-step2-dispatch` remains a dedicated Makefile target. Plan line 122 lists `run_dispatch` with catch-all material, but `docs/linting.md:301` and the target name bind `test-run-step2-dispatch` to `python/cli.py implement run-dispatch` routing (`test_run_dispatch_*`). An implementer can give that target an overlapping `step2_dispatch` slice or leave it full-file; the guard then fails or a hidden duplicate full-file run remains outside the partition.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Assign `test-run-step2-dispatch` `-k run_dispatch` (five `test_run_dispatch_*` nodes only). Give `test-step2-dispatch` `-k step2_dispatch`. Put registry/recovery/auth/materialize in the catch-all with `not (run_dispatch or step2_dispatch or codex_launcher or cursor_launcher or commit_main)`.

### FINDING_3: `test_plan_review_panel.py` target ownership for `panel_dispatch` / `voter_dispatch` / registry
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: `test_plan_review_panel.py` lists three surviving Makefile targets but does not assign which target owns `panel_dispatch`, `voter_dispatch`, and the registry catch-all. Today `test-plan-review-panel` and `test-dispatch-plan-review-panel` are both full-file reruns of the same seven tests. An implementer can slice both to `panel_dispatch` (or leave overlap) and still miss `test_plan_review_cli_registry_contains_panel_verbs`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Bind explicitly: `test-dispatch-plan-review-panel` → `panel_dispatch`; `test-dispatch-plan-voters` → `voter_dispatch`; `test-plan-review-panel` → catch-all/registry only (e.g. `-k plan_review_cli_registry` or `not (...)` over the other two families).

### FINDING_4: Missing `test_checks.py` CI proof for `plan_review_panel.py` and `rendering.py` direct-target rules
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: Blocking `checks.py` expansions for `plan_review_panel.py` and `rendering.py` lack mandatory `test_checks.py` CI proof. The plan marks `rendering.py` rule assertions as if practical and only loosely requires `plan_review_panel.py` coverage if absent, while Testing strategy step 2 runs only `python/test_checks.py -k direct_targets_design`. There is no existing `test_checks.py` coverage for either path today. An implementer can merge expanded `_DIRECT_TARGET_RULES` without CI catching a wrong or incomplete target list, silently shrinking `/implement` run-relevant breadth for `plan_review_panel.py` and `rendering.py` edits after Makefile slicing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Require parametrized `_direct_targets_for` assertions for `python/plan_review_panel.py` (all three targets including `test-dispatch-plan-review-panel`) and `python/rendering.py` (must include `test-dispatch-plan-review-panel`). Add them to Testing strategy step 2 with an explicit pytest selector that runs those cases, not only `-k direct_targets_design`.

### FINDING_5: `plan_quality.py` relevant-check mapping gap after `test-design-driver` partition
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The plan omits the `plan_quality` relevant-check expansion after partitioning `test-design-driver`. After `test-design-driver` becomes the non-`design_route` slice, a `python/plan_quality.py` edit still maps only to `test-design-driver` and no longer runs `test_design_route_merges_flags_for_already_planned`, despite the plan stating `plan_quality` keeps the former full-file lifecycle breadth.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Add `test-step0b-router-flag-recovery` to the `python/plan_quality.py` and `python/test_plan_quality.py` `_DIRECT_TARGET_RULES` entry, and update `python/test_checks.py` expectations for that mapping.
