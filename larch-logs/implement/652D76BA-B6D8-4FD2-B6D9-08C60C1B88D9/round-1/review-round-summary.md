# Review Round 1

- Mode: `diff`
- 2 accepted, 4 rejected (2 neutral)

## Accepted Findings

### FINDING_3: Trailing-slash `PWD` basename differs from bash `basename "$PWD"`
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `os.path.basename(PWD)` does not match bash `basename "$PWD"` when `PWD` has a trailing slash (e.g. `PWD=<OPERATOR_REPO_PATH>/` derives `_` in Python but `larch4` in retired bash). That changes `CLONE_TAG_FULL` and `EXPECTED_TMPDIR_BASENAME_PREFIX`, weakening or breaking tmpdir prefix verification.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Implement POSIX basename behavior on encoded PWD bytes before sanitizing and truncating.
  - From codex-specialist-edge-cases-output.txt: Strip trailing slashes with POSIX basename semantics before byte sanitization, preserving / and empty fallback behavior.


### FINDING_4: `step-8-ship.sh` runs clone-tag before Python version guard
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `skills/implement/scripts/step-8-ship.sh` invokes `python/cli.py implement clone-tag` (lines 61–64) before `step-8-python-guard.sh`. On a stale Python runtime (e.g. 3.9 or 3.10), `cli.py` can exit with a non-contract rc and stdout that is not the single STALLED JSON object Step 8 recovery routing expects, instead of the documented guard-driven STALLED JSON / exit 4 contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Move the clone-tag CLI call after step-8-python-guard.sh succeeds and before ship pr.
  - From codex-specialist-edge-cases-output.txt: Run step-8-python-guard.sh before invoking implement clone-tag, then capture/eval clone-tag before ship pr.
  - From codex-specialist-testing-output.txt: Move the guard before clone-tag and add a wrapper-level stale-Python test


