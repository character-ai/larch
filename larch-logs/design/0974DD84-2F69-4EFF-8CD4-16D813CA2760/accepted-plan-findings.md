### FINDING_1: Injectable path enumeration for shared delta classification
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: The shared delta classifier must accept caller-supplied path enumeration rather than ref strings that always map to `_tracked_paths_vs_ref`; otherwise self-review may reintroduce the cached probe and alter commit-route staging.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Define the shared classifier as inventory-set plus patch-match loop over a caller-supplied path list (or `enumerate_paths` callback). Keep `patch_match_ref` as the head passed to patch matching. Pre-coder supplies `_tracked_paths_vs_ref(diff_base)`; self-review supplies worktree-only `git diff --name-only <pre_head>`.


