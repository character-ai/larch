### OOS_1:
- **Description**: [OUT_OF_SCOPE] Prefer importable `run_logs.larch_log_write_round_main` over shelling `write-implement-round-meta.sh` / `run-log write-round` when already in Python. Scenario: `python/cli.py run-log write-round` is importable via `run_logs.py`; keeping `proc.run` subprocess hops adds avoidable failure modes but does not block C2 if parity is preserved
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/review_and_fix.py:55-56
- **Phase**: design

