# Review Round 3

- Mode: `diff`
- 8 accepted, 12 rejected (5 neutral)

## Accepted Findings

### FINDING_1: CLI KV emitters allow multiline value injection
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: New `*_cli.py` modules print `KEY=value` contract lines without rejecting newlines, unlike the bash/logging helpers. Multiline `gh`/`git` stderr in fields such as `ERROR` or `PUSH_ERROR` can emit extra apparent KVs and confuse orchestrators parsing stdout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_10: Rebase force-push retry does not preserve the original lease OID
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `rebase_push` delegates retry handling without pinning the expected remote OID from before the first push. If another runner advances the remote branch after an initial lease failure, a later retry can overwrite that concurrent push.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_11: `ci decide` accepts malformed decision inputs
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `ci decide` can treat invalid values such as malformed `--conflicted`, invalid status strings, or bad counters as valid decision inputs, producing merge actions instead of usage failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_12: `phantom.check_phantom_dirty` still shells to an absorbed script
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: The Python phantom dirty check wraps `scripts/check-phantom-dirty.sh` instead of porting the logic. Once the script is deleted, the Python CLI can silently report `unknown` rather than probing correctly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_15: `gather_status` stops too early on `gh pr view` failures
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: When `gh.pr_view` raises, `gather_status` returns early and skips fetch/check-status/behind-count probes. A transient PR-view outage can leave failed checks reported as pending until the poll budget exhausts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_18: `check_main_sync` lacks plan-mandated CLI parity tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: There is no pytest coverage for `check_main_sync` or the `git check-main-sync` CLI despite planned exit `0/1/2` parity. Contract drift could let preflight or `/implement` mishandle blocked local-main or probe-error states.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_19: Behind-count probe failures are converted to pending
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `gather_status` converts behind-count probe failures into `CI_STATUS=pending` with `BEHIND_COUNT=0` instead of preserving the already-classified checks status. A passing PR with transient `git rev-list` failure can keep waiting until timeout rather than proceed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_9: `create_branch` confuses tags/remote refs with local branches
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `create_branch` checks `try_rev_parse(branch)` instead of verifying `refs/heads/<branch>`. A tag or remote-tracking ref with the target name can make the Python CLI report `exists` when the bash helper would create the missing local branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.


