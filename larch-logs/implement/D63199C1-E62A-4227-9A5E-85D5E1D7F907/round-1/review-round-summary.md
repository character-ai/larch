# Review Round 1

- Mode: `diff`
- 3 accepted, 2 rejected (1 neutral)

## Accepted Findings

### FINDING_1: PR create diagnostics were truncated from `create-pr.sh` to `create-sh`
- **Reviewer(s)**: codex-specialist-security-output.txt, codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-cli-surface-regression-output.txt
- **Severity**: latent
- **Concern**: `python/pr.py:381-392` changed migrated `pr create` stderr script-name tokens from the legacy `create-pr.sh` prefix to `create-sh`, affecting invalid repo, detached HEAD, and unreadable body-file error paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-security-output.txt: Restore the original string literals from the deleted companion modules.
  - From codex-specialist-correctness-output.txt: Restore all affected literals in create_main to create-pr.sh.
  - From codex-specialist-edge-cases-output.txt: Restore create-pr.sh in the repo validation and stderr messages.
  - From codex-specialist-testing-output.txt: Restore create-pr.sh in these diagnostics and add a focused pr create error-path test.
  - From dyn-cli-surface-regression-output.txt: Change all three sites back to `create-pr.sh` (including `script="create-pr.sh"` at line 381); add focused tests for invalid `--repo`, detached HEAD, and missing body file asserting the `create-pr.sh:` stderr prefixes.


### FINDING_2: Push branch unknown-argument diagnostics were truncated from `git-push.sh` to `git-sh`
- **Reviewer(s)**: codex-specialist-security-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-cli-surface-regression-output.txt
- **Severity**: latent
- **Concern**: `python/push.py:206-209` changed the migrated `push branch` unknown-argument stderr prefix from `git-push.sh` to `git-sh`, breaking bash-parity diagnostics for that CLI error path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-security-output.txt: Restore the original string literals from the deleted companion modules.
  - From codex-specialist-correctness-output.txt: Restore the original literal strings git-push.sh and git-force-push.sh.
  - From cursor-specialist-edge-cases-output.txt: Restore the exact stderr strings from deleted push_cli.py (git-push.sh: unknown argument: … and git-force-push.sh: not on a named branch).
  - From codex-specialist-edge-cases-output.txt: Restore the exact old prefixes at both error sites.
  - From codex-specialist-testing-output.txt: Restore the original diagnostic strings and add stderr assertions for these migrated error paths.
  - From dyn-cli-surface-regression-output.txt: Restore `git-push.sh:` in `branch_main` (line 208) to match deleted `push_cli.py` and `scripts/git-push.sh`; add a pytest that calls `push.branch_main(["--bogus"])` and asserts stderr contains `git-push.sh: unknown argument`.


### FINDING_3: Push force detached-head diagnostics were truncated from `git-force-push.sh` to `git-force-sh`
- **Reviewer(s)**: codex-specialist-security-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-cli-surface-regression-output.txt
- **Severity**: latent
- **Concern**: `python/push.py:230-231` changed the migrated `push force` detached-head stderr prefix from `git-force-push.sh` to `git-force-sh`, breaking bash-parity diagnostics for that CLI error path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-security-output.txt: Restore the original string literals from the deleted companion modules.
  - From codex-specialist-correctness-output.txt: Restore the original literal strings git-push.sh and git-force-push.sh.
  - From cursor-specialist-edge-cases-output.txt: Restore the exact stderr strings from deleted push_cli.py (git-push.sh: unknown argument: … and git-force-push.sh: not on a named branch).
  - From codex-specialist-edge-cases-output.txt: Restore the exact old prefixes at both error sites.
  - From codex-specialist-testing-output.txt: Restore the original diagnostic strings and add stderr assertions for these migrated error paths.
  - From dyn-cli-surface-regression-output.txt: Restore `git-force-push.sh:` at line 231; add a test stubbing `git.force_push_recovery` to return `status="detached_head"` and assert stderr equals the bash-aligned prefix.


