# Review Round 2

- Mode: `diff`
- 3 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: complexity/ruff baseline cleanup still incomplete after split
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases, codex-generalist
- **Severity**: important
- **Concern**: Split-module complexity exceptions were retargeted to new modules (`dispatch_bootstrap.py`, `dispatch_manifest.py`, `dispatch_commit_route.py`) but not removed. Matching per-file ruff complexity ignores remain in `python/ruff.toml:401-419`, and `python/complexity-baseline.json:2793-2832` still grandfathers the relocated symbols. The plan acceptance item to remove obsolete complexity-baseline rows for split functions remains unmet; the branch still ships renamed exceptions instead of eliminating the debt.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Delete the stale rows for the split functions from both baselines, then rerun the ratchet and only re-add exceptions that are still genuinely needed.
  - From codex-specialist-edge-cases: Remove the obsolete ignore and baseline entries once those functions are genuinely under threshold, or split/flatten the remaining hot spots further before landing the refactor.
  - From codex-generalist: Refactor the remaining over-threshold split functions enough to remove these baseline rows and the corresponding ruff per-file complexity ignores.


### FINDING_2: env-via-config-constant baseline stale after module split
- **Reviewer(s)**: codex-specialist-correctness, codex-generalist
- **Severity**: important
- **Concern**: The env-var ratchet baseline is stale after the split. `python3 -B python/cli.py lint env-via-config-constant` fails on moved env accesses in `python/larch/implement/dispatch_recovery.py:183`, `python/larch/implement/dispatch_step2.py:77`, and `python/larch/implement/dispatch_step2_flow.py:85-126`. Rows in `python/env-via-config-constant-baseline.json:1047-1108` / `:1091-1170` were retargeted but not corrected to match live module identities, so the baseline cleanup acceptance item is incomplete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Delete the stale rows for the split functions from both baselines, then rerun the ratchet and only re-add exceptions that are still genuinely needed.
  - From codex-generalist: Regenerate or correct `python/env-via-config-constant-baseline.json` so the live identities match the new modules, or replace the bare env literals with config constants.


### FINDING_3: subprocess-via-runner baseline stale after module split
- **Reviewer(s)**: codex-generalist
- **Severity**: important
- **Concern**: The subprocess ratchet baseline is stale after the split. `python3 -B python/cli.py lint subprocess-via-runner` fails on unbaselined calls in `python/larch/implement/dispatch_recovery.py:192-196`, `python/larch/implement/dispatch_step2.py:129-157`, and `python/larch/implement/dispatch_step2_flow.py:345-356`. Existing rows in `python/subprocess-via-runner-baseline.json:976-1001` still point at pre-split locations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generalist: Regenerate or hand-correct `python/subprocess-via-runner-baseline.json` so the rows point to the new files and qualified symbols, or route those calls through the Runner abstraction.


