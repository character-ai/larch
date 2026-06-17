### OOS_1:
- **Description**: Probe timeouts are still non-retryable. Scenario: Cold-start or slow Codex exec can still hit LARCH_PROBE_TIMEOUT_SECONDS and emit probe-failed with no transient retry; part of the reported intermittency remains
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/agents.py:857-858,874-875
- **Phase**: design
- **Filed URL**: https://github.com/character-ai/larch/issues/4624
