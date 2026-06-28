### OOS_1: [OUT_OF_SCOPE] Non-contiguous title regression test uses contiguous fixture
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: important
- **Concern**: `test_title_noncontiguous_stays_under_256_chars` (`python/test_audit_runs.py:36-41`) builds a contiguous `range(5000, 6138)` list, so it exercises the contiguous `#{first}-#{last}` branch rather than the non-contiguous compact formatter at scale. A regression that restores comma-join for gapped lists would not be caught; the test name misleads maintainers about which branch is covered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Build gappy 300/1138-element pr_list (e.g. evens only) and assert len(title) <= 256 on the non-contiguous path
  - From cursor-specialist-correctness: Rename or fix fixture to match name
  - From cursor-specialist-edge-cases: Use a gapped 1138-PR list (e.g. even-only numbers) and assert both `len(title) <= 256` and the compact format string.
  - From cursor-specialist-testing: Rename (e.g. `test_title_large_contiguous_batch_stays_under_256_chars`) or use a gapped PR list if the intent is the non-contiguous formatter.

### OOS_2: [OUT_OF_SCOPE] Suffix wording uses `(N total)` instead of plan's `(N PRs)`
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: `python/larch/issue/audit_runs.py:89` renders gapped batches with `(N total)` rather than the plan's `(N PRs)`. No functional breakage; minor plan wording drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Use (N PRs) or document total in SKILL.md

### OOS_3: [OUT_OF_SCOPE] No defensive 256-char clamp or `TRACKING_TITLE_MAX_LEN` reuse
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: nit
- **Concern**: `python/larch/issue/audit_runs.py:71-91` does not implement the plan's optional hard 256-char clamp or reuse `config.TRACKING_TITLE_MAX_LEN` / the truncation pattern from `tracking_issue.py`. Normal `pacific-timestamp` skill output stays short; risk is mainly for unbounded `--timestamp` CLI callers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Optionally clamp to config.TRACKING_TITLE_MAX_LEN at title emission
  - From cursor-specialist-edge-cases: Add a fail-closed clamp or length assertion using `TRACKING_TITLE_MAX_LEN` if you want parity with tracking-issue title handling.
  - From cursor-specialist-testing: Add `title = title[:256]` (or fail closed) as belt-and-suspenders if direct CLI use is a concern.

### OOS_4: [OUT_OF_SCOPE] Gapped batch title overstates numeric PR span
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: `python/larch/issue/audit_runs.py:88-89` renders gapped batches as `PRs #1-#6 (4 total)`, which overstates the numeric span (implies #3–#5 are included). Intentional tradeoff per the plan; full list remains in `audited_prs` frontmatter. Informational for human readers only.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_5: [OUT_OF_SCOPE] New audit-runs tests not listed in shard assignments
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: Four new tests in `python/test_audit_runs.py:26-46` are not listed in `python/shard-assignments.json`. Unassigned nodeids still run via round-robin per `docs/linting.md`; shard-balancing hygiene only, not a functional coverage gap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Refresh assignments on the next rebalance pass.

