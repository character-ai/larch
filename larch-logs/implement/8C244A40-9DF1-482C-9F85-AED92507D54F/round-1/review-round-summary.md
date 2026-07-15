# Review Round 1

- Mode: `diff`
- 5 accepted, 2 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Legacy deep ingest suppresses current triage risk
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-schema-provenance
- **Severity**: major
- **Concern**: A legacy deep-ingest row sets record-wide `legacy_schema`, causing valid current-schema triage introduced-risk data and class-open sibling data to be ignored. Schema validity must be tracked per stage rather than allowing legacy deep data to downgrade the entire record.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-schema-provenance: Address the concern above.


### FINDING_5: Missing ingestion-backed #6632 acceptance coverage
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: The class-open acceptance path is not tested end to end through triage and deep `ledger_ingest`; hand-built ledger fixtures could allow ingestion, serialization, report, or follow-up wiring regressions to pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_6: Missing current-schema deep-ingest serialization coverage
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: major
- **Concern**: No successful `ledger_ingest` test verifies persistence and reload of current deep-schema fields or `legacy_schema` propagation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


### FINDING_7: Missing focused report-precedence fixtures
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing
- **Severity**: minor
- **Concern**: Report fixtures do not independently cover triage-only introduced risk, deep-over-triage precedence, legacy suppression, none-found omission, and class-open-only follow-up behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.


### FINDING_8: Missing cross-language introduced-risk fixture
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The cross-language fixture does not connect verifier introduced-risk output to bundle evidence and its Grep-tied reason.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
