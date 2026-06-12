# Review Round 1

- Mode: `diff`
- 5 accepted, 2 rejected (2 neutral)

## Accepted Findings

### FINDING_1: Python sidecar ingestion silently ignores CLI failures
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, dyn-risk-integration-output.txt
- **Severity**: important
- **Concern**: `ingest_launcher_token_sidecar` does not check `token append-record` or `token record-vendor-sidecar` return codes. It can return `True` even when ingestion failed, leaving NDJSON or active-ledger accounting incomplete with no operator-visible warning.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, dyn-risk-integration-output.txt: Address the concern above.


### FINDING_2: Design sidecar ingestion can write the wrong active ledger
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Design sidecar ingestion can write the active ledger under `IMPLEMENT_TMPDIR` when both tmpdir environment variables are set. That lets `codex_plan_draft` rows miss live `/design` cost lines while NDJSON append succeeds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_4: Golden fixtures duplicate shipped default pricing constants
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Design and implement golden fixtures still pin shipped default per-bucket rate tables outside the single allowed default-rate snapshot. Future default-rate changes can leave stale literals in fixtures and render tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_5: Pricing override ladder tests are missing
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Planned regression tests for bucketed versus blended pricing override order are missing. Regressions in `LARCH_TOKEN_RATE_PER_M` handling may ship undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_6: Sidecar ingestion regression coverage is incomplete
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-risk-integration-output.txt
- **Severity**: important
- **Concern**: Planned tests for the shared Python sidecar ingestion helper and its CI monitor, rebase, ship, and launcher call sites are missing or incomplete. Regressions in parsing, deduplication, stale-sidecar clearing, `MODEL=`, `TOKEN_RECORD=`, or tmpdir export can drop or double-count costs without CI signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-risk-integration-output.txt: Address the concern above.


