# Review Round 1

- Mode: `diff`
- 2 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: correctness: scripts/test-implement-structure.sh stale raw git add pathspec require
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: blocking
- **Concern**: Structural harness `scripts/test-implement-structure.sh` still requires the raw `git add --pathspec-from-file` call that this branch intentionally removed from `python/review_and_fix.py`. `make test-implement-structure` (and `make lint`) fails because the module no longer contains the required literal. Replace the stale require with the planned forbid and keep the pathspec-only commit requirement via `commit_main`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_2: correctness: python/git.py lsof probe errors treated as no lock holder
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `python/git.py` treats `lsof` probe failures with empty stdout as no lock holder. On Darwin without `/proc`, `lsof` exit 1 with "Operation not permitted" can let `_try_remove_stale_index_lock` unlink an active 0-byte `.git/index.lock`. Return `None` for `lsof` errors except known clean no-holder output, then use repo-scoped fallback or fail closed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt: Address the concern above.


