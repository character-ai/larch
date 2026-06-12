### OOS_1:
- **Description**: Item 3 legacy-guard verification dropped from executable plan. Scenario: Approved outline lists verify legacy-guard correctness for bug-body, bug-comment, and issue-input-file. Production already hard-fails unless LARCH_STALL_RECOVERY_TEST_LEGACY_SURFACES is set. Plan includes no verification step or regression test for that guard.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/implement/scripts/stall-recovery-report.sh:2241-2251
- **Phase**: design

### OOS_1:
- **Description**: [OUT_OF_SCOPE] Plan centralizes CI wait bail tokens in config.py but ci-wait.sh still hardcodes the same five string literals with no mechanical cross-file enforcement. Scenario: After a future rename or typo fix in config.CI_WAIT_BAIL_* only, ci-wait.sh can keep emitting the old token; stall-recovery lint reads config.STALL_RECOVERY_RUNTIME_BAIL_TOKENS not ci-wait.sh assignments, and relevant-checks.sh has no bail-token parity hook, so drift may not surface until a consumer breaks or tests are manually updated
- **Reviewer**: Cursor-dyn-shell-python-drift
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/ci-wait.sh:134-195 python/config.py:21-40
- **Phase**: design

