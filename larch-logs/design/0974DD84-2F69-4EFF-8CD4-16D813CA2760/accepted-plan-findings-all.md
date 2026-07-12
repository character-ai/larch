### FINDING_1: Preserve separate delta-enumeration and patch-match refs
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-dyn-Snapshot Contract Reviewer, Codex-dyn-Snapshot Contract Reviewer
- **Severity**: major
- **Concern**: The shared tracked-delta helper must retain separate refs for enumerating tracked paths and matching snapshot patches. Pre-coder collection can enumerate against a post-coder `diff_base` while matching against the earlier `snapshot_head`; collapsing these refs can misclassify pre-existing dirty files or real coder deltas.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Specify the shared tracked-delta helper takes `diff_ref` and optional `patch_match_ref` (default equals `diff_ref`). Keep pre-coder facade forwarding `snapshot_head`; self-review passes one ref for both.
  - From Cursor-Pragmatic: Add to Approach that the shared tracked-delta helper takes `enumerate_ref` and `patch_match_ref`; self-review passes one ref, pre-coder facade passes `diff_base` and `compare_head` from the existing `snapshot_head` kwarg.
  - From Cursor-dyn-Snapshot Contract Reviewer: Keep snapshot_head (or patch_compare_ref) as an optional parameter on the shared tracked-delta helper; pre-coder facade passes snapshot_head when diff_base is post-coder-head; self-review passes pre_head only
  - From Codex-dyn-Snapshot Contract Reviewer: Document and implement `patch_compare_ref` / `snapshot_head` on the shared helper; pre-coder facade wires it from `_collect_round_stage_paths`; self-review leaves it unset.


### FINDING_3: Add an executable self-review artifact-path test
- **Reviewer(s)**: Codex-Innovation, Codex-dyn-Snapshot Contract Reviewer
- **Severity**: minor
- **Concern**: Existing tests do not exercise a nonempty self-review capture through the shared root/prefix path builder, so an incorrect root or `pre-self-review` prefix could silently produce no stage paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add a test that captures a self-review snapshot with a tracked path, asserts its artifact paths, and verifies baseline exclusion plus new-edit collection 1.
  - From Codex-dyn-Snapshot Contract Reviewer: Add a focused git-fixture test covering staged-only, unstaged-only, and pre-existing delta exclusion for both snapshot facades


### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/review/snapshot.py:936-955
- **Concern**: [SCOPE-REDUCTION] Do not widen self-review tracked discovery to `_tracked_paths_vs_ref`. Scenario: Self-review today uses only `git diff --name-only <pre_head>`. The plan converges on `_tracked_paths_vs_ref`, which also scans `--cached`, so staged-only post-snapshot edits become deltas. That breaks issue acceptance ("behavior otherwise unchanged") and is not required for parameterization. Existing tests mock `_self_review_delta_paths`, so CI can stay green while commit scope changes.
- **Proposed resolution**: Parameterize probe policy per family: self-review keeps worktree-only listing; pre-coder keeps the dual worktree+cached union. Share path/patch/inventory helpers, not identical delta discovery.


### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/review/snapshot.py:936-955
- **Concern**: [SCOPE-REDUCTION] Do not converge self-review tracked enumeration to `_tracked_paths_vs_ref`. Scenario: Self-review today uses only `git diff --name-only pre_head`. `_tracked_paths_vs_ref` also unions `git diff --cached --name-only pre_head`. After snapshot, index-only drift vs `pre_head` can enter `_self_review_delta_paths` and change `_collect_self_review_stage_paths` / commit-route output while existing tests mostly monkeypatch delta helpers. Conflicts with acceptance that self-review flow behaves identically.
- **Proposed resolution**: In Drift convergence, keep self-review enumeration on the single worktree probe behind its facade; share patch capture/match/inventory helpers only, or add an explicit parity guard and staged-index regression coverage before switching probes.


### FINDING_1: Injectable path enumeration for shared delta classification
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: The shared delta classifier must accept caller-supplied path enumeration rather than ref strings that always map to `_tracked_paths_vs_ref`; otherwise self-review may reintroduce the cached probe and alter commit-route staging.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Define the shared classifier as inventory-set plus patch-match loop over a caller-supplied path list (or `enumerate_paths` callback). Keep `patch_match_ref` as the head passed to patch matching. Pre-coder supplies `_tracked_paths_vs_ref(diff_base)`; self-review supplies worktree-only `git diff --name-only <pre_head>`.


