### FINDING_1: GNU-only `find -printf` breaks macOS local runs
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: Post-coder-head and 0444 mode checks treat `find -printf` as portable. `find -printf` is GNU-only; on macOS (common for this repo), `test-review-and-fix.sh` can fail spuriously when developers run the harness locally.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Pin the existing dual-stat idiom used elsewhere (`stat -c %a` OR `stat -f %Lp`, e.g. `scripts/test-relevant-checks-byte-budget.sh:23-26`); do not rely on `find -printf` alone


