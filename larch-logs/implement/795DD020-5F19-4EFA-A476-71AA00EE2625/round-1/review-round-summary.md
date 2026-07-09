# Review Round 1

- Mode: `diff`
- 2 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_3: state directory can be swapped after reopen
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases
- **Severity**: major
- **Concern**: `open_state_dir()` recreates the state directory by pathname after `mkdir` without proving the reopened path is still the same directory, so a same-UID rename swap can redirect writes into attacker-controlled storage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.


### FINDING_6: raw /tmp fallback fails on macOS
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: minor
- **Concern**: `_state_parent()` falls back to raw `/tmp`, but the opener rejects `/tmp` under `O_NOFOLLOW` on macOS because it is a symlink, so state persistence fails when `TMPDIR` is unset.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.


