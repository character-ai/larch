### FINDING_1:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/core/hook_anti_read_poll.py:77
- **Concern**: Prior fallback fix is incomplete: discriminator must be non-empty, not merely set. Scenario: Current Bash uses `${HOOK_ANTI_READ_POLL_DISCRIMINATOR:-}` with `-n`; an exported empty discriminator still falls back to `nosession`. The plan says "is set", which can change that bucket to `nosession-` and regress shipped partitioning.
- **Proposed resolution**: Pin `session_key` to use `HOOK_ANTI_READ_POLL_DISCRIMINATOR` only when its value is non-empty, and cover the empty-string env case where the ladder is tested.



