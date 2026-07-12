### [Plan Review] FINDING_3

### FINDING_3: Stage-specific ledger field names are not pinned
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Concern**: The plan calls for stage-specific `introduced_risk` and evidence-reason fields plus round-trip tests, but never names the exact `LedgerRecord` / `_record_json` keys (for example `triage_introduced_risk` vs `deep_introduced_risk` and matching evidence-reason columns). Report precedence and refresh-clear rules depend on those names.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add one plan bullet listing exact ledger key names for triage-stage and deep-stage risk plus evidence-reason fields, and require `_upsert_record`, `_record_json`, and `_ledger_record_from_mapping` to use those names consistently.


### [Plan Review] FINDING_4

### FINDING_4: Evidence-reason fields lack a defined agent JSONL source contract
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Concern**: The plan adds ledger evidence-reason fields and report rendering that prefers risk plus its evidence reason, but agent updates only require `introduced_risk`, `class_complete`, and `sibling_sites`. Ingest parsers are not told where the evidence sentence comes from, so the new report section cannot be populated deterministically.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Either add introduced_risk_evidence to triage and verifier JSONL with strict ingest validation, or drop separate evidence-reason ledger/render fields and render introduced_risk alone. Pick one contract and align agents, ingest, ledger, tests, and SKILL docs.


