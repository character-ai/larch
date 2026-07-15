### OOS_1: [OUT_OF_SCOPE] Sibling-site symbols reject dotted or hyphenated names
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-schema-provenance
- **Severity**: minor
- **Concern**: `SIBLING_SITE_RE` accepts only a narrow symbol format, rejecting natural dotted or hyphenated targets such as `path:Class.method`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-schema-provenance: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### OOS_2: [OUT_OF_SCOPE] Missing ingestion-backed class-open test
- **Reviewer(s)**: dyn-dyn-schema-provenance
- **Severity**: minor
- **Concern**: The #6632-shaped test passes a hand-built ledger row directly to `render_report`, leaving ingest-time key validation, schema stamping, and refresh behavior only partially exercised.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-schema-provenance: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_3: [OUT_OF_SCOPE] Missing report fixture matrix
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Plan-listed fixtures for triage-only risk, deep precedence, and legacy suppression are absent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_4: [OUT_OF_SCOPE] Missing legacy triage ledger-ingest test
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Legacy triage JSONL is covered only at parse level, not through `ledger_ingest`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false
