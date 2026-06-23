### OOS_1: [OUT_OF_SCOPE] Parallel `python/cli.py implement step-5-resume` calls `commit-fixes --stage-all` with no `COMMIT_OUTCOME` allowlist, porcelain gate, or deferred KV relay. Active `/implement` uses `step-5-resume.sh`, so this is not on the hot path today. If a future caller switches to the Python verb, it can resume `review-and-fix step5` after a failed or unverified commit phase.
- **Description**: [OUT_OF_SCOPE] Parallel `python/cli.py implement step-5-resume` calls `commit-fixes --stage-all` with no `COMMIT_OUTCOME` allowlist, porcelain gate, or deferred KV relay. Active `/implement` uses `step-5-resume.sh`, so this is not on the hot path today. If a future caller switches to the Python verb, it can resume `review-and-fix step5` after a failed or unverified commit phase.. Scenario: Align `step5_resume_main` with the hardened `step-5-resume.sh` contract, or document and test that the Python verb is not a supported caller until parity exists.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/implement_dispatch.py:471-474
- **Phase**: design
