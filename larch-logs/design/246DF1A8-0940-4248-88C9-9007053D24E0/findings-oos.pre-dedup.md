### OOS_1: [OUT_OF_SCOPE] `git check-phantom-dirty` CLI verb remains after `check-phantom-dirty.sh` deletion; only `lib-phantom-probe.sh` consumed the bash script and it migrates to `git phantom-probe`.
- **Description**: [OUT_OF_SCOPE] `git check-phantom-dirty` CLI verb remains after `check-phantom-dirty.sh` deletion; only `lib-phantom-probe.sh` consumed the bash script and it migrates to `git phantom-probe`.. Scenario: No runtime breakage: `phantom.py` calls `check_phantom_dirty()` in-process; pytest keeps the verb tested. Extra surface is maintenance-only.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/cli.py:426-427
- **Phase**: design



