## Decision 1: Stall exit code alignment
- **Question**: Should the shell `1:stall` branch exit 0 (matching Python) when `commit_rc=0`, or also unconditionally when `commit_rc!=0`?
- **Resolution**: Change `exit 1` to `exit 0` only. The `exit "$commit_rc"` guard for non-zero commit_rc is outside the reported divergence scope; the issue specifically calls out "exits 1" (i.e., the zero-commit_rc path). Minimal change preserving existing non-zero behavior.
- **Source**: codebase (dispatch_commit_route.py:942-943 always returns 0; issue body targets the `exit 1` literal)
