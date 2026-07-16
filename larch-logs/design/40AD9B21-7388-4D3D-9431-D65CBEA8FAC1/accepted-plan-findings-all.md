### FINDING_3: Workflow `gh` authentication is unspecified
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic, Codex-Requirements
- **Severity**: major
- **Concern**: Workflow permissions alone do not authenticate `gh`, so the failure handler may be unable to create or update the tracking issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add `env: GH_TOKEN: $${{ github.token }}` only to the issue step and keep its mutation/read-back failures job-fatal.
  - From Codex-Pragmatic: Set GH_TOKEN: ${{ github.token }} on the failure-only gh step and retain the least-privilege workflow permissions
  - From Codex-Requirements: Add GH_TOKEN: ${{ github.token }} to the failure-only gh issue step environment


### FINDING_7: Pylint-normalized block extraction is underspecified
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-dyn-Ratchet Identity Auditor
- **Severity**: major
- **Concern**: Reconstructing hashes from raw source slices or an ad hoc normalizer can diverge from Pylint symilar’s stripped-line and filtering semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Specify that identity text is built from `LineSet.stripped_lines` over the matched span (same normalization pylint used), hash that joined text, and add a fixture where adding only a comment line does not change identity but adding a code line at an edge triggers growth exit 1
  - From Cursor-Pragmatic: In the plan pin one helper that rebuilds the normalized block from the merged observation using the same `stripped_lines` slice and code-line filtering symilar uses then SHA-256 prefix that bytes with a fixed separator and test it against pylint report output
  - From Cursor-dyn-Ratchet Identity Auditor: Add an explicit contract: extract normalized text per commonality from canonical LineSets with pylint's symilar filtering helpers, hash that bytes-stable text, and fail closed when the API cannot supply it.


### FINDING_8: Durable identities must be per-observation and per-pair
- **Reviewer(s)**: Cursor-Requirements, Cursor-dyn-Ratchet Identity Auditor
- **Severity**: major
- **Concern**: Merged `DuplicateCluster` objects contain aggregate spans and line counts but no per-observation text, so multi-span or transitive clusters can collapse distinct same-pair identities or assign one pair’s allowance to another.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Specify that durable identity is built from each symilar commonality (or expanded module-pair observation) with its own normalized block text and hash before/alongside `_compute_sims` grouping; keep DuplicateCluster for diagnostics only unless each observation carries its normalized text and hash.
  - From Cursor-dyn-Ratchet Identity Auditor: Build observations from canonicalized _find_common commonalities (one per sorted module pair plus normalized text), reject duplicate live (pair,hash) identities, and use merged clusters only for reporting/digest.


### FINDING_11: Shortened live blocks cannot be grandfathered by full-block hash alone
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Concern**: A still-reportable duplicate that shrinks changes its full hash, becoming new plus stale and preventing the intended shrink-only drain.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Store sufficient normalized-block comparison material or window hashes to recognize live blocks at or below the recorded allowance, while continuing to fail growth, new content, and stale rows


### FINDING_16: Failure issue updates must be scoped to duplicate-code failure
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: minor
- **Concern**: Setup or dependency failures could incorrectly create or overwrite the duplicate-code tracking issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Give the lint command a step id and run the issue update only when that step’s outcome is failure


### FINDING_1: Failure-only owner path is skipped after lint failure
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Concern**: The owner-path issue step uses an outcome-only condition, which inherits the default `success()` requirement and is therefore skipped when the duplicate-code step fails.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Require `if: ${{ failure() && steps.duplicate_code.outcome == 'failure' }}` and retain the outcome check


### FINDING_2: Baseline rows can grandfather multiple live observations
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Concern**: A single baseline row can match multiple distinct shorter live windows, allowing multiple new clusters to pass merely because they collectively represent one stored baseline observation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Require an injective baseline-to-live match; treat surplus observations as new or ambiguity errors, and add the two-window regression test

