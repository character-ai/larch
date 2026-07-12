### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/review/snapshot.py:472-494
- **Concern**: The shared delta classifier must take injectable path enumeration, not ref strings that always map to `_tracked_paths_vs_ref`. Scenario: The plan gives self-review `enumerate_ref=pre_head` and pre-coder `enumerate_ref=diff_base`, but only pre-coder may use `_tracked_paths_vs_ref`. A shared helper keyed only on refs will reintroduce the cached probe for self-review and change commit-route staging despite the probe-policy guardrails.
- **Proposed resolution**: Define the shared classifier as inventory-set plus patch-match loop over a caller-supplied path list (or `enumerate_paths` callback). Keep `patch_match_ref` as the head passed to patch matching. Pre-coder supplies `_tracked_paths_vs_ref(diff_base)`; self-review supplies worktree-only `git diff --name-only <pre_head>`.



### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/review/snapshot.py:913-929
- **Concern**: Keep safe-patch-name collision checks when self-review adopts `_snapshot_inventory()`. Scenario: `_snapshot_inventory()` rejects duplicate raw path lines only. Today both families reject distinct tracked paths that encode to the same patch filename via `_safe_patch_name`. Dropping that check while reusing `_snapshot_inventory()` can make patch reads target the wrong artifact and misclassify deltas.
- **Proposed resolution**: In the self-review facade (and pre-coder validation), keep the existing safe-name collision guard after `_snapshot_inventory()` on tracked inventories; do not treat inventory parsing alone as sufficient patch-collision protection.



### FINDING_3:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: plan.txt:3-41
- **Concern**: The prior accepted executable-test fix is incomplete because its test file lacks a firm heading. Scenario: Plan coverage can pass when the mandated artifact-path regression test is omitted
- **Proposed resolution**: Add `### UPDATED: python/tests/review/test_review_and_fix.py` for the planned test changes



