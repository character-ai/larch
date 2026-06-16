### OOS_1: [OUT_OF_SCOPE] Missing targeted salvage and aggregate-alternation tests
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Plan calls for explicit pytest coverage of salvage cases **c** (empty → no salvage) and **d** (result-gate-miss → no salvage), plus aggregate-alternation invalid-ERE with the full live pattern string. Current tests cover main paths (salvage success, format-gate-miss drop, generic invalid `[`) but not those named cases. Edge review notes the aggregate-alternation behavior is effectively pinned by the generic `--require-result-pattern` invalid-ERE test (`[`), but the named acceptance artifact is still missing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add three small targeted tests so regressions in gate ordering or `posix_ere_to_python` on the aggregate alternation are caught.
  - From cursor-specialist-edge-cases-output.txt: the plan calls for a dedicated invalid-ERE test on the aggregate alternation pattern; coverage is effectively provided by the generic `--require-result-pattern` invalid-ERE test (`[`), not a pattern-specific case. Behavior is pinned; only the named acceptance artifact is missing.


### OOS_2: [OUT_OF_SCOPE] No test for `dyn-*` vs static slot `DYNAMIC_DISPATCH_OK` split
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: No test exercises the `dyn-*` → `DYNAMIC_DISPATCH_OK` vs static slot split. Logic at `python/agent_waterfall.py:703-706` mirrors bash, but the split is untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: One two-slot fixture with `dyn-foo` and a static slot where only the dynamic slot fails phase 3.


