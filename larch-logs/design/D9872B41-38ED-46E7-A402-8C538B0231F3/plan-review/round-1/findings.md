### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: docs/linting.md:264
- **Concern**: Plan asserts linting catalog has no test-merge-parity row and needs no docs edit, but line 264 documents make test-merge-parity on test-harnesses-5. Scenario: Makefile-only removal leaves a stale harness table row; operators follow docs/linting.md to a removed target
- **Proposed resolution**: Add ### UPDATED: docs/linting.md to delete the make test-merge-parity table row (or point parity coverage at make py-test / python-tests); fix Edge cases and Acceptance; add a linting.md spot-check to Testing strategy

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:74
- **Concern**: The proposed scan-input bullet overclaims that scan-path error detail is passed through redact.redact(), but python/report_tokens_scan.py only redacts GitHub repo-resolution detail; _warn paths for invalid JSON, symlink skips, missing files, and run-dir resolution print raw paths/exceptions.. Scenario: SECURITY.md would document a stronger redaction boundary than the implementation provides, so maintainers could rely on a false guarantee for scan warnings emitted from untrusted larch-logs content.
- **Proposed resolution**: Narrow the new bullet to the actual contract: scan warnings skip untrusted artifacts and may include local file paths, while GitHub repo-resolution/public issue egress details are redacted; do not claim all scan-path error detail is redacted unless this PR also changes _warn callers to redact.

### FINDING_3:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: docs/linting.md:264
- **Concern**: Stale harness-catalog row after target removal. Scenario: Plan omits docs/linting.md because Edge cases claims the target is not cataloged; line 264 still documents make test-merge-parity as a test-harnesses-5 lint prerequisite after the Makefile target is deleted
- **Proposed resolution**: Add a docs/linting.md update (remove or retarget the row) and fix the plan Edge cases assertion so operators are not sent to a removed target

### FINDING_4:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: docs/linting.md:263-265
- **Concern**: Finding 1: Plan removes the Makefile target but leaves a documented user-facing target row. Scenario: The plan says docs/linting.md does not enumerate test-merge-parity, but line 264 documents make test-merge-parity as a lint prerequisite; after the proposed Makefile deletion, following the docs gives No rule to make target test-merge-parity
- **Proposed resolution**: Include docs/linting.md in the plan and delete the test-merge-parity row, or replace it with a note that python/test_merge_bash_parity.py is covered by make py-test

### FINDING_5:
- **Reviewer(s)**: Codex-Edge
- **Severity**: latent
- **Focus area**: security
- **Location**: python/report_tokens_scan.py:31-43; SECURITY.md:74
- **Concern**: Finding 2: Proposed SECURITY.md bullet overstates scan-path redaction. Scenario: The plan says scan-path error detail is passed through redact.redact(), but _warn and _json_file print JSON/OSError warning detail and paths directly; the new Trust Model text would document a stronger guarantee than the code provides
- **Proposed resolution**: Narrow the SECURITY.md addition by removing the blanket error-detail redaction claim, or limit it to the repo-resolution/egress paths that actually call redact.redact()

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: docs/linting.md:264
- **Concern**: Plan falsely claims the harness catalog omits test-merge-parity and skips docs edits. Scenario: After Makefile removal, line 264 still documents make test-merge-parity as a lint prerequisite; operators get No rule to make target
- **Proposed resolution**: Add docs/linting.md to Files to modify: delete the test-merge-parity table row (or one sentence under test-merge-pr that parity runs via make py-test / python-tests CI)

### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: docs/linting.md:264
- **Concern**: Plan says no docs update is needed, but docs/linting.md still documents make test-merge-parity as a lint shard prerequisite while the plan removes that Makefile target.. Scenario: After the PR lands, contributors following docs/linting.md run make test-merge-parity and get no rule to make target; the row also falsely claims make lint still runs it via test-harnesses-5.
- **Proposed resolution**: Add the minimum docs edit: delete the docs/linting.md row for make test-merge-parity, or rewrite it to point at make py-test if a parity note must remain.

### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: docs/linting.md:264
- **Concern**: Plan denies linting.md lists test-merge-parity but the harness catalog row exists. Scenario: After Makefile removal operators following docs/linting.md still see a valid make target that no longer exists
- **Proposed resolution**: Add docs/linting.md to Files to modify: remove the make test-merge-parity table row; correct plan Edge cases at plan.txt:81-82

### FINDING_9:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: docs/linting.md:264
- **Concern**: Plan removes make test-merge-parity but leaves its documented Makefile target row. Scenario: The PR would leave docs telling users to run a removed target, and the row still claims it is a test-harnesses-5 prerequisite
- **Proposed resolution**: Add docs/linting.md to the plan and delete the test-merge-parity row, or replace it with the existing py-test coverage note if that table needs to mention the parity test

### FINDING_10:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:74; python/report_tokens_scan.py:35-42,243-259
- **Concern**: Planned Trust Model bullet overstates scan error redaction. Scenario: python/report_tokens_scan.py redacts GitHub repo-resolution details, but JSON/read-dir warnings print raw exception and path details; a SECURITY.md claim that error detail is passed through redact.redact() would be false
- **Proposed resolution**: Keep the change doc-only and narrow that sentence to GitHub repo resolution errors, or remove the broad error-detail redaction claim unless runtime redaction is also intentionally added

### FINDING_11:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: docs/linting.md:264
- **Concern**: Plan omits linting-catalog cleanup for removed `test-merge-parity` target. Scenario: Edge cases claim `docs/linting.md` does not enumerate `test-merge-parity` and that no docs update is needed (plan lines 81-82), but the harness table still documents `make test-merge-parity` on shard 5. After Makefile removal, operators and `scripts/test-harness-shards-coverage.md` rename guidance still point at a nonexistent `make lint` prerequisite.
- **Proposed resolution**: Add `### UPDATED: docs/linting.md` — delete the `make test-merge-parity` row (line 264). Optionally add one clause on the `test-merge-pr` row that `python/test_merge_bash_parity.py` runs via `make py-test` / the `python-tests` CI job. Extend Acceptance/Testing with a catalog spot-check.

### FINDING_12:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: docs/linting.md:264
- **Concern**: Plan omits stale docs update for removed Makefile target. Scenario: After deleting test-merge-parity, docs/linting.md still tells users to run make test-merge-parity, which will fail and contradict the plan's claim that no docs enumerate it
- **Proposed resolution**: Add docs/linting.md to UPDATED and remove the test-merge-parity table row alongside the Makefile deletion

### FINDING_13:
- **Reviewer(s)**: Cursor-dyn-ci-shard-contract
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: docs/linting.md:264
- **Concern**: Plan edge cases claim no file outside Makefile references test-merge-parity and docs/linting.md does not enumerate it; repo has a harness-catalog row documenting make test-merge-parity on shard 5. Scenario: Makefile-only removal passes listed gates but leaves a documented target that no longer exists; operators following docs/linting.md hit no rule to make target
- **Proposed resolution**: Add ### UPDATED: docs/linting.md to delete the test-merge-parity table row and fix plan.txt edge-case lines 79-82

### FINDING_14:
- **Reviewer(s)**: Codex-dyn-ci-shard-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: docs/linting.md:263-265
- **Concern**: The plan says no non-log references remain, but docs/linting.md still documents make test-merge-parity as a test-harnesses-5 prerequisite. Scenario: After the target is removed from Makefile, the linting docs tell operators to run a deleted target and describe stale shard membership
- **Proposed resolution**: Delete the docs/linting.md row for make test-merge-parity as part of the same minimum-change removal

### FINDING_15:
- **Reviewer(s)**: Codex-dyn-ci-shard-contract
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: .github/workflows/requirements-test-harnesses.txt:1-5; .github/workflows/ci.yaml:166-171; scripts/test-relevant-checks.sh:141-192,534-545
- **Concern**: The plan keeps the test-harness pytest pin based on scripts/test-relevant-checks.sh, but that harness stubs pytest instead of requiring the installed package. Scenario: After test-merge-parity is removed, the test-harnesses CI job still installs pytest across the shard matrix and carries comments about Python parity harnesses with no remaining harness consumer
- **Proposed resolution**: Remove pytest==9.0.3 from .github/workflows/requirements-test-harnesses.txt and update the related comments to PyYAML-only; keep python/requirements-test.txt for make py-test

### FINDING_16:
- **Reviewer(s)**: Codex-dyn-ci-shard-contract
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/test-harness-shards-coverage.sh:231-272; Makefile:4,83,372-373
- **Concern**: The planned validation overstates test-harness-shards-coverage: it checks shard-bound targets missing from .PHONY, not extra stale .PHONY tokens. Scenario: If the recipe and shard prerequisite are deleted but Makefile:4 still lists test-merge-parity, the listed gates can pass while the Makefile removal is incomplete
- **Proposed resolution**: Add a cheap post-edit grep spot-check for test-merge-parity in Makefile and the touched docs/CI harness files, or revise the testing notes so they do not claim the coverage gate catches stale .PHONY entries

### FINDING_17:
- **Reviewer(s)**: Cursor-dyn-trust-boundary-evidence
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:36-44 (planned); python/report_tokens_scan.py:31-33,77-83,192-226
- **Concern**: Planned bullet overclaims that scan-path error detail is always redacted. Scenario: Repo-resolution failures are redacted, but `_warn()` stderr (invalid JSON, symlink skips, manifest/token skips) is printed verbatim; operators may treat SECURITY.md as guaranteeing redacted scan diagnostics
- **Proposed resolution**: Narrow prose to repo-slug/`gh` resolution errors (lines 77-83), or say scan warnings are not redacted and point to egress redaction for public output

### FINDING_18:
- **Reviewer(s)**: Codex-dyn-trust-boundary-evidence
- **Severity**: important
- **Focus area**: correctness
- **Location**: SECURITY.md:68-74; python/report_tokens_scan.py:95-123,192-226; python/test_report_tokens_scan.py:145-157
- **Concern**: Planned malformed/non-object JSON wording is broader than the scanner behavior.. Scenario: Manifest and token-report malformed/non-object JSON skip a record, but malformed timing-report/run-params JSON only makes workflow unknown and the record remains parseable; the planned bullet would document all malformed JSON as skipped.
- **Proposed resolution**: Qualify the SECURITY.md bullet: manifest/token-report failures skip that run, while workflow auxiliary JSON is ignored for classification and falls back to unknown.

### FINDING_19:
- **Reviewer(s)**: Codex-dyn-trust-boundary-evidence
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:68-74; python/report_tokens_scan.py:31-43,50-59,69-84,243-263
- **Concern**: Planned error-detail redaction wording overclaims the scan path.. Scenario: Only GitHub repo-resolution errors pass detail through redact.redact; _warn paths for JSON read/parse errors, repo-root failure details, and run-dir containment/read errors print raw local stderr.
- **Proposed resolution**: Replace the broad error-detail claim with a narrow one: repo slug lookup diagnostics are redacted; scan warnings are local stderr and may include repo-local paths or parser/OS error text.

### FINDING_20:
- **Reviewer(s)**: Codex-dyn-trust-boundary-evidence
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:74; python/report_tokens_issue.py:40-46,87-93; python/gh.py:149-163,829-843; python/redact.py:310-317
- **Concern**: The planned cross-reference preserves a stale public-egress implementation claim.. Scenario: /report-tokens issue bodies are redacted by python/redact.py via redact.redact before gh.issue_create is called with redact_body=False; documenting this as scripts/redact-secrets.sh once sends reviewers to the wrong live boundary.
- **Proposed resolution**: Update the existing public-issue-boundary wording or the new cross-reference to say the Python redactor runs once, with parity/backstop semantics for scripts/redact-secrets.sh if that is the intended guarantee.
