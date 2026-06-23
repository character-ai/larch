## Goal
Implement issue #5206: [IMPLEMENTING] [OOS] [OUT_OF_SCOPE] Parallel python/cli.py implement step-5-resume calls commit-fixes --stage-all with no COMMIT_OUTCOME allowlist, porcelain gate, or deferred KV relay.

## Implementation Plan
## Out-of-Scope Observation

**Surfaced by**: Cursor-Innovation
**Phase**: design
**Vote tally**:

## Description

[OUT_OF_SCOPE] Parallel `python/cli.py implement step-5-resume` calls `commit-fixes --stage-all` with no `COMMIT_OUTCOME` allowlist, porcelain gate, or deferred KV relay. Active `/implement` uses `step-5-resume.sh`, so this is not on the hot path today. If a future caller switches to the Python verb, it can resume `review-and-fix step5` after a failed or unverified commit phase.. Scenario: Align `step5_resume_main` with the hardened `step-5-resume.sh` contract, or document and test that the Python verb is not a supported caller until parity exists.

---
*This issue was automatically created by the larch `/implement` workflow from an out-of-scope observation surfaced during the workflow.*

## Test plan
(no test plan section in plan-file)
