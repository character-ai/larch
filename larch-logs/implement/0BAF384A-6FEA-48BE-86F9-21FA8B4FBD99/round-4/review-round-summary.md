# Review Round 4

- Mode: `diff`
- 16 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Closed-window cutoff uses UTC date
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `python/issue_create.py` uses a UTC calendar date for the closed-window cutoff, while the bash behavior used local `date.today()`. A US evening run can include or exclude the wrong closed issue around the 90-day boundary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_11: Forked-repo setup writes diagnostics to stdout
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `forked-repo setup` now prints remote diagnostics to stdout. Callers expecting stdout to contain only machine-readable `SETUP_FORKED_REPO_RESULT` KVs can break.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_12: Issue-create fallback can leave orphan issues without rollback warning
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: After post-create id lookup failure, `issue create-one` fallback can leave a created issue open without a `ROLLBACK_FAILED` warning. Reruns can then create duplicates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_14: Body-file title semantics are documented as tested but are not covered
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `skills/issue/SKILL.md` claims `test_issue_create.py` covers `--body-file` trailing-title semantics, but the reviewer found no such pytest coverage after the shell harness deletion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_15: Sentinel skipped paths lack tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `write_sentinel` only tests `WROTE=true`. Dry-run and failure skip paths can regress their stderr grammar or stdout behavior without CI coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_16: Partial issue-detail fetch failures lack tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `fetch_issue_details` mixed success and per-issue failure behavior is untested. Phase 2 can mishandle failed candidate fetches if `FETCH_STATUS_N=failed` emission regresses while exit status remains 0.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_17: Add-blocked-by transient retry is untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: REST `add-blocked-by` retry behavior with 10s and 30s sleeps is untested. Transient GitHub API errors during dependency wiring can fail immediately without CI catching it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_18: Upgrade-larch plan-required coverage is incomplete
- **Reviewer(s)**: cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `python/test_upgrade_larch.py` is missing plan-required coverage for stdout restoration and quiet-mode routing. The cursor reviewer also identified missing sparse-allowlist and install-stamp backfill coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_19: Cleanup plan-required coverage is incomplete
- **Reviewer(s)**: cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `python/test_cleanup_skill.py` is missing cleanup fail-safe and session-count coverage. The cursor reviewer also identified missing fresh nested activity retention coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_2: Non-numeric issue IDs can pass create-one
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `issue create-one` accepts any non-empty JSON `id` as `ISSUE_ID`, but downstream dependency wiring needs a numeric REST id. A GraphQL node id can later fail `issue add-blocked-by`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_20: Alias git-state isolation coverage is missing
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `python/test_alias_skill.py` only covers plugin versus `--private` routing. It does not cover git-state isolation cases from the deleted shell harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_21: Block-issue mutation failure and success contracts lack tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `python/test_issue_block.py` lacks separate coverage for GraphQL mutation failures. The codex reviewer also identified missing clean-success coverage, so mutation errors or valid successes can emit the wrong contract without CI catching it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_3: Non-JSON successful create output can create a duplicate issue
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: If `gh issue create` exits 0 with a URL instead of JSON, `_create_fallback` can run `gh issue create` again. That can create and report a second issue instead of resolving the first issue’s id.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_4: Cleanup scans TMPDIR instead of the preserved cleanup root
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `cleanup_skill.py` scans `tempfile.gettempdir()`. With `TMPDIR=/var/folders/...`, stale `/tmp/claude-implement-*` entries may survive while unrelated matching entries under `TMPDIR` may be removed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_6: Redaction documentation and references are inconsistent
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The issue skill and redaction docs point to missing or misleading security coverage. `create-one` uses `python/redact.py`, while `scripts/redact-secrets.md` claims the shell redactor covers issue publication.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_7: Remote rollback failures can be hidden
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `restore_remote_state` ignores `git config` failures during rollback. A partial remote rewrite can survive without a recovery report except on the test-injection path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


