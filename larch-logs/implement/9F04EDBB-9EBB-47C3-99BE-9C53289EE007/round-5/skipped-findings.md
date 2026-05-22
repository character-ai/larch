### FINDING_8: find-lock-issue.sh header omits exit code 6
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: File header “Exit codes” lists `0,2,3,4,5` but `_require_plan_block_before_lock` can exit **6** (`PLAN_PROBE_FAILED`). Integrators relying on the header may mishandle **6**.
- **Suggested revision**: Document exit **6** in the header (aligned with `find-lock-issue.md`).



