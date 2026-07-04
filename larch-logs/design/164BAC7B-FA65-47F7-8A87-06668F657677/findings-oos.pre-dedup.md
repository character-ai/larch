### OOS_1: Absolute pass-through weakens the prior pseudo-absolute input hardening
- **Description**: Absolute pass-through weakens the prior pseudo-absolute input hardening. Scenario: After the fix, `run-log write --input-file /etc/passwd` reads the real file if it exists; previously the path was rebased under `IMPLEMENT_TMPDIR` and usually failed closed. Trusted today, but widens the CLI surface
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: security
- **Location**: python/larch/report/run_log_batch.py:114-115
- **Phase**: design



