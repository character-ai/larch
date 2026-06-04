### FINDING_1: Removed `test-merge-parity` target remains documented in linting catalog
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge, Codex-Edge, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-ci-shard-contract, Codex-dyn-ci-shard-contract
- **Severity**: important
- **Concern**: The plan removes the `make test-merge-parity` Makefile target while incorrectly claiming `docs/linting.md` does not enumerate it. The linting catalog still documents the target, so users following the docs would hit a removed target and stale shard/prerequisite information.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add ### UPDATED: docs/linting.md to delete the make test-merge-parity table row (or point parity coverage at make py-test / python-tests); fix Edge cases and Acceptance; add a linting.md spot-check to Testing strategy
  - From Cursor-Edge: Add a docs/linting.md update (remove or retarget the row) and fix the plan Edge cases assertion so operators are not sent to a removed target
  - From Codex-Edge: Include docs/linting.md in the plan and delete the test-merge-parity row, or replace it with a note that python/test_merge_bash_parity.py is covered by make py-test
  - From Cursor-Innovation: Add docs/linting.md to Files to modify: delete the test-merge-parity table row (or one sentence under test-merge-pr that parity runs via make py-test / python-tests CI)
  - From Codex-Innovation: Add the minimum docs edit: delete the docs/linting.md row for make test-merge-parity, or rewrite it to point at make py-test if a parity note must remain.
  - From Cursor-Pragmatic: Add docs/linting.md to Files to modify: remove the make test-merge-parity table row; correct plan Edge cases at plan.txt:81-82
  - From Codex-Pragmatic: Add docs/linting.md to the plan and delete the test-merge-parity row, or replace it with the existing py-test coverage note if that table needs to mention the parity test
  - From Cursor-Requirements: Add `### UPDATED: docs/linting.md` — delete the `make test-merge-parity` row (line 264). Optionally add one clause on the `test-merge-pr` row that `python/test_merge_bash_parity.py` runs via `make py-test` / the `python-tests` CI job. Extend Acceptance/Testing with a catalog spot-check.
  - From Codex-Requirements: Add docs/linting.md to UPDATED and remove the test-merge-parity table row alongside the Makefile deletion
  - From Cursor-dyn-ci-shard-contract: Add ### UPDATED: docs/linting.md to delete the test-merge-parity table row and fix plan.txt edge-case lines 79-82
  - From Codex-dyn-ci-shard-contract: Delete the docs/linting.md row for make test-merge-parity as part of the same minimum-change removal

### FINDING_2: SECURITY.md overclaims scan warning redaction
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Codex-Pragmatic, Cursor-dyn-trust-boundary-evidence, Codex-dyn-trust-boundary-evidence
- **Severity**: important
- **Concern**: The planned SECURITY.md wording claims scan-path error detail is passed through `redact.redact()`, but only GitHub repo-resolution/public egress paths appear redacted. Scanner warnings for invalid JSON, symlinks, missing files, containment/read failures, and local path/exception details can print raw local stderr.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Narrow the new bullet to the actual contract: scan warnings skip untrusted artifacts and may include local file paths, while GitHub repo-resolution/public issue egress details are redacted; do not claim all scan-path error detail is redacted unless this PR also changes _warn callers to redact.
  - From Codex-Edge: Narrow the SECURITY.md addition by removing the blanket error-detail redaction claim, or limit it to the repo-resolution/egress paths that actually call redact.redact()
  - From Codex-Pragmatic: Keep the change doc-only and narrow that sentence to GitHub repo resolution errors, or remove the broad error-detail redaction claim unless runtime redaction is also intentionally added
  - From Cursor-dyn-trust-boundary-evidence: Narrow prose to repo-slug/`gh` resolution errors (lines 77-83), or say scan warnings are not redacted and point to egress redaction for public output
  - From Codex-dyn-trust-boundary-evidence: Replace the broad error-detail claim with a narrow one: repo slug lookup diagnostics are redacted; scan warnings are local stderr and may include repo-local paths or parser/OS error text.

### FINDING_3: Test-harness pytest dependency may remain unnecessarily pinned
- **Reviewer(s)**: Codex-dyn-ci-shard-contract
- **Severity**: latent
- **Concern**: The plan keeps the test-harness pytest pin because of `scripts/test-relevant-checks.sh`, but that harness stubs pytest rather than requiring the installed package. Removing `test-merge-parity` may leave the test-harness CI shard installing pytest and carrying Python parity comments without a remaining harness consumer.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-ci-shard-contract: Remove pytest==9.0.3 from .github/workflows/requirements-test-harnesses.txt and update the related comments to PyYAML-only; keep python/requirements-test.txt for make py-test

### FINDING_4: Planned validation overstates what shard coverage catches
- **Reviewer(s)**: Codex-dyn-ci-shard-contract
- **Severity**: latent
- **Concern**: The plan suggests `test-harness-shards-coverage` would catch incomplete Makefile cleanup, but that coverage checks shard-bound targets missing from `.PHONY`, not stale extra `.PHONY` entries. The recipe and shard prerequisite could be deleted while `test-merge-parity` remains in `.PHONY`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-ci-shard-contract: Add a cheap post-edit grep spot-check for test-merge-parity in Makefile and the touched docs/CI harness files, or revise the testing notes so they do not claim the coverage gate catches stale .PHONY entries

### FINDING_5: SECURITY.md malformed JSON wording is broader than scanner behavior
- **Reviewer(s)**: Codex-dyn-trust-boundary-evidence
- **Severity**: important
- **Concern**: The planned SECURITY.md text appears to say all malformed/non-object JSON is skipped, but scanner behavior differs by artifact: manifest and token-report failures skip a run, while workflow auxiliary JSON failures only fall back to unknown classification and can leave the record parseable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-trust-boundary-evidence: Qualify the SECURITY.md bullet: manifest/token-report failures skip that run, while workflow auxiliary JSON is ignored for classification and falls back to unknown.

### FINDING_6: Public egress cross-reference points to stale redaction boundary
- **Reviewer(s)**: Codex-dyn-trust-boundary-evidence
- **Severity**: important
- **Concern**: The planned SECURITY.md cross-reference preserves a stale claim that public issue body redaction is handled by `scripts/redact-secrets.sh`, while the live `/report-tokens` issue path redacts through `python/redact.py` before calling `gh.issue_create` with `redact_body=False`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-trust-boundary-evidence: Update the existing public-issue-boundary wording or the new cross-reference to say the Python redactor runs once, with parity/backstop semantics for scripts/redact-secrets.sh if that is the intended guarantee.
