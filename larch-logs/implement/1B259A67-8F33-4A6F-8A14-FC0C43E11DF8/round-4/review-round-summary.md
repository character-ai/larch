# Review Round 4

- Mode: `diff`
- 2 accepted, 2 rejected (0 neutral)

## Accepted Findings

### FINDING_6: bash ship-pr CI-fix waterfall misses failed-tier sidecar ingestion before rollback
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: When `LARCH_SHIP_PR_IMPL=bash`, a failed Codex tier can bill usage before rollback, then Cursor can win. The failed Codex sidecar may never be ingested, so totals undercount compared with the Python `ci_monitor` path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Ingest each tier's sidecar immediately after launcher return (before rollback), with per-waterfall dedup; or route bash CI-fix through agents.ingest_launcher_token_sidecar.


### FINDING_7: shell-path regression coverage is missing for ship-pr recovery sidecar ingestion
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Current tests do not cover `ship-pr.sh` recovery waterfall and `_stage_and_push_ci_fixes` token sidecar ingestion. A regression could drop active-ledger ingestion or ingest after rollback without being caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add stubbed ship-pr.sh harness or extend test_ship.py to assert append-record plus record-vendor-sidecar run exactly once per tier with IMPLEMENT_TMPDIR exported before rollback branches.


