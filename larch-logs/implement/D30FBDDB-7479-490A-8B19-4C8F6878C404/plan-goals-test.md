## Goal
Implement issue #5322: [IMPLEMENTING] [OOS] Aggregated rollup of 2 capped OOS items.

## Implementation Plan
## Out-of-Scope Observation

**Surfaced by**: Combined: capped per-run rollup

**Phase**: implement

**Vote tally**: N/A — capped rollup of 2 entries


## Description

Cap 1 (OOS_ISSUES_PER_RUN_CAP) exceeded; the following 2 items were rolled up by the per-run OOS issue cap. Each rolled-up item's full body is preserved verbatim below:
  - **[OUT_OF_SCOPE] correctness: dispatch.lock OSError misreports permission failures as contention**: [Files: python/implement_dispatch.py:1509-1513]
    ### OOS_1: [OUT_OF_SCOPE] correctness: dispatch.lock OSError misreports permission failures as contention
    - **Reviewer(s)**: cursor-specialist-correctness-output.txt
    - **Severity**: nit
    - **Concern**: `run_dispatch_main` reports every dispatch-lock `OSError` as concurrent dispatch contention, including permission failures while opening `dispatch.lock`. A tmpdir with a non-writable `dispatch.lock` path exits 2 with "another dispatch is already running" even though no concurrent dispatch exists, which can mislead operators (`python/implement_dispatch.py:1509-1513`).
    - **Suggested revisions (informational for voters; coder decides)**:
      - Branch on `errno` or separate open and `flock` failures so only `EAGAIN` / `EWOULDBLOCK` emits the concurrent-dispatch message.
  - **[OUT_OF_SCOPE] security: oos.py is_security_tagged misses space-separated Focus area**: [Files: python/oos.py python/oos.py:19-21 python/oos.py:47-61]
    ### OOS_2: [OUT_OF_SCOPE] security: oos.py is_security_tagged misses space-separated Focus area
    - **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
    - **Severity**: important
    - **Concern**: `python/oos.py` `is_security_tagged` still uses a `focus-area`-only `_FOCUS_AREA_FIELD_RE`, while `voting.is_security_block` was updated for space-separated `Focus area`. The `oos serialize` path can misclassify `- **Focus area**: security` blocks as non-security and write them to public output (`python/oos.py:19-21`, `python/oos.py:47-61`). `oos.py` is unchanged on this branch; the plan targets `voting.is_security_block` / `plan_review_tally`.
    - **Suggested revisions (informational for voters; coder decides)**:
      - Align `_FOCUS_AREA_FIELD_RE` with `voting.py`, for example `focus[- ]area`, or delegate to `voting.is_security_block`.
      - Add an `oos serialize` regression test mirroring `test_is_security_block_space_separated_focus_area`.

---
*This issue was automatically created by the larch `/implement` workflow from an out-of-scope observation surfaced during the workflow.*

## Test plan
(no test plan section in plan-file)
