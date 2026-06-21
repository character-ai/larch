# Review Round 3

- Mode: `diff`
- 1 accepted, 3 rejected (0 neutral)

## Accepted Findings

### FINDING_2: `test-hook-stop-fail-close.sh` missing from pre-commit `files:` regex blocks
- **Reviewer(s)**: dyn-retirement-cleanup-output.txt
- **Severity**: important
- **Concern**: This branch adds `scripts/test-hook-stop-fail-close.sh` to the residual manifest and wires `make test-hook-stop-fail-close`, but the path is missing from all three duplicated `files:` regex blocks in `.pre-commit-config.yaml` (siblings `test-hook-anti-read-poll`, `test-hook-bg-poll-guard`, and `test-hook-progress-report` are present). Pre-commit `shellcheck` / `bash-syntax-check` / `lint-bash32` therefore will not run on commits that touch only that harness, even though docs and `docs/linting.md` describe pre-commit and CI as scanning the same residual set.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-retirement-cleanup-output.txt: Add `scripts/test-hook-stop-fail-close.sh` to each pre-commit `files:` regex, or better, stop hand-maintaining the regex and drive pre-commit file selection from `python/cli.py residual-bash paths` (the wrappers already support manifest enumeration on zero-arg runs).


