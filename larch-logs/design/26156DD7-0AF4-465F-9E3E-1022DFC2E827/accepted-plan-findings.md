### FINDING_1: Unverified triage verdicts still drive deep queue and reports
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: major
- **Concern**: Unverified legacy triage verdicts can still influence deep-routing, sampling, and Stage 3 reporting. The plan fixes cache-skip behavior, but downstream consumers still read `record.triage_verdict` / `triage_needs_deep` without a verification gate, so fabricated or stale triage rows can remain authoritative until overwritten.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In _priority_deep_candidates, the sample pool, and _final_verdict, treat triage_verdict/triage_needs_deep as absent unless _triage_complete(record, refresh=...) is true (or triage_evidence_verified is true). Add tests that unverified ledger rows do not enqueue deep work and do not surface triage verdicts in render_report.
  - From Cursor-Innovation: Gate deep priority, sampling pool, and `_final_verdict` on `triage_evidence_verified` (or `_triage_complete(..., "triage")`); thread the flag through `_upsert_record`; update `test_deep_queue_priority_cap_and_model_alias` and add a report/deep-queue test for unverified legacy rows.
  - From Cursor-Pragmatic: Apply the same verified-triage gate in `_final_verdict` and `_priority_deep_candidates`: treat records with `triage_evidence_verified=False` (or not `_triage_complete(..., "triage", ...)`) as having no triage verdict for verdict/deep purposes, matching the "not yet triaged" fallback.
  - From Cursor-Requirements: Require triage_evidence_verified before any consumer treats record.triage_verdict as authoritative: gate _priority_deep_candidates and the sample pool, and have _final_verdict ignore unverified triage fields (fall through to mechanical or NEEDS_DEEP). Add tests for report and deep-queue behavior with legacy unverified triage rows.
  - From Codex-Requirements: Gate every triage verdict consumer on triage_evidence_verified. Use a helper for usable triage data in pending triage, _priority_deep_candidates, sample selection, and _final_verdict, while preserving independent deep_verdict handling.


### FINDING_2: Triage schema omits evidence_token
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Cursor-Requirements, Codex-Requirements
- **Severity**: major
- **Concern**: The strict triage row schema and required-field enumeration still omit `evidence_token`, even though the agent contract and ingest logic require it. That mismatch can cause token-bearing rows to be rejected as unexpected, or allow token-free rows to keep parsing if `_strict_keys` is left at the old five-field allowlist.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add evidence_token to the TriageIngest dataclass, the _parse_triage_row allowed-key set, and the plan's required-field enumeration so schema validation and bundle-file validation stay aligned.
  - From Codex-Arch: Add evidence_token to TriageIngest and the allowed triage fields, or move token capture outside the strict row schema before validation.
  - From Cursor-Innovation: Add evidence_token to the `TriageIngest` / `_parse_triage_row` required-field list and `_strict_keys` allowlist in the plan and implementation.
  - From Cursor-Requirements: Add evidence_token to the required field list for TriageIngest and _parse_triage_row, and extend _strict_keys to the six-key set {issue, verdict, missing_items, reason, needs_deep, evidence_token}.
  - From Codex-Requirements: Add evidence_token: str to TriageIngest and to the strict key set, validate it as a non-empty string, then compare that parsed value with the file-derived token.


