### [Plan Review] FINDING_3

### FINDING_3: OID polling must compare against post-recovery HEAD
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: Replacing the post-force-push HEAD re-read with an OID poll risks comparing GitHub against a stale pre-recovery local OID unless the helper explicitly re-reads HEAD after recovery. That can exhaust retries or match the wrong commit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: State `_poll_head_oid_match` re-reads `git.try_rev_parse(..., "HEAD")` on every attempt (do not compare against the pre-recovery `local_head`), or keep an explicit post-recovery `rev-parse` before calling the helper; add/extend `test_merge.py` poll coverage to assert the post-push HEAD is what gets compared.


### [Plan Review] FINDING_6

### FINDING_6: Python stderr breadcrumbs need documented shapes and tests
- **Reviewer(s)**: Codex-dyn-contract-drift
- **Severity**: important
- **Concern**: Adding generic Python `ship.py` and `ci_monitor.py` stderr breadcrumbs without pinning the documented stderr grammar can let tests pass with arbitrary text while operators or consumers grepping documented progress shapes miss liveness or keep expecting old behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-contract-drift: Specify that Python breadcrumbs reuse the documented prefixes/shapes and assert them exactly in python/test_ship.py and python/test_ci_monitor.py, or update the docs to declare the Python-specific stderr grammar while keeping stdout JSON-only


### [Plan Review] FINDING_7

### FINDING_7: Volatile allowlist must not match substantive audit batches
- **Reviewer(s)**: Cursor-dyn-run-log-invariants
- **Severity**: important
- **Concern**: If the volatile allowlist is implemented as a broad pattern such as any `*.ndjson` under the run directory, substantive audit files like execution issues or review findings could be skipped and omitted from the PR tree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-run-log-invariants: Name explicit basename allowlist only; never match execution-issues.ndjson round-* artifacts manifest.json plan-goals-test.md session-transcript.jsonl; add a negative test_run_logs.py case where execution-issues.ndjson-only delta must commit### OOS_1:
- **Description**: No contract doc update for python volatile-only skip or merge-time pre-flush removal. Scenario: Operators and completeness tooling docs still describe only bash refresh-run-logs commit behavior; Phase 7 python cutover behavior is undocumented in the run-log authority doc
- **Reviewer**: Cursor-dyn-run-log-invariants
- **Severity**: latent
- **Focus area**: architecture
- **Location**: docs/run-logs.md:363-383, python/README.md:20-24
- **Phase**: design


