### [Plan Review] FINDING_3

### FINDING_3: Invalid primary candidates must stop `origin` fallback
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: The detailed resolver does not explicitly lock evaluation order. A non-empty primary `gh` candidate that fails slug validation must map to `invalid-repo` and must not be replaced by a valid `origin` result or collapsed into `could not determine repo`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In `python/larch/git/gh.py`, document and implement: after primary `gh`, if stdout is non-empty and fails `validate_repo_slug`, record `invalid` and stop; attempt `origin` only when primary produced no usable candidate (failed or empty). Add a `test_gh.py` case for non-empty invalid primary with a valid `origin` remote.

