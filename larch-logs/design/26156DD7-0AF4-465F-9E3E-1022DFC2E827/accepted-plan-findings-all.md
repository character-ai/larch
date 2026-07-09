### FINDING_1: Stage 1 still allows token relay through the orchestrator
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-dyn-Evidence Ingest Guard
- **Severity**: major
- **Concern**: Stage 1 dispatch can still smuggle `MANIFEST_PATH`, bundle contents, or `evidence_token` values into the triage prompt, so `bug-fix-triage` can emit schema-valid rows without reading bundle evidence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add orchestrator rules parallel to the inline ban: Task prompt carries only the triage batch path; do not pass MANIFEST_PATH, bundle bodies, bundle_path lists, or evidence_token hints; only the triage agent may obtain tokens via Read of bundle files
  - From Cursor-Pragmatic: Add Stage 1 rules: Task prompt carries only the triage batch path plus read instructions; forbid MANIFEST_PATH, manifest JSON, bundle markdown, and any evidence_token values in the prompt; forbid orchestrator Read of manifest or bundle files during triage dispatch.
  - From Cursor-dyn-Evidence Ingest Guard: Add explicit Stage 1 rules: never pass MANIFEST_PATH, evidence_token values, or inlined bundle markdown to bug-fix-triage; Task input is only the triage batch path plus read-batch/read-bundle instructions


### FINDING_2: Bundle markdown needs one canonical evidence-token line
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: minor
- **Concern**: Bundle markdown does not pin a single machine-readable `evidence_token` line, so readers and ingest can disagree on which substring counts as the proof token.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Define one machine-stable line near the top (for example `Evidence token: <token>`), generate it in build_bundle_record, and update the agent strict JSONL example to include `evidence_token` with that exact value
  - From Cursor-Innovation: Fix one line near bundle top, e.g. Evidence token: <token>, document it in bug-fix-triage.md and share the same parser in build_bundle_record and ledger_ingest
  - From Cursor-Pragmatic: In `build_bundle_record`, add one stable near-top line `evidence_token: <token>`; mirror the same label in `.claude/agents/bug-fix-triage.md`; add a unit test that the bundle file contains that line and matches `BundleRecord.evidence_token`.
  - From Cursor-Requirements: Pin one line near the top of each bundle (e.g. Evidence token: <nonce>) and document the same extraction rule in bug-fix-triage.md and the ingest parser


### FINDING_3: Ingest still trusts manifest-stored proof tokens
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation, Cursor-Requirements, Codex-Requirements, Cursor-dyn-Evidence Ingest Guard, Codex-dyn-Evidence Ingest Guard
- **Severity**: major
- **Concern**: Persisting `evidence_token` in `manifest.json`, and comparing ingest against that manifest copy, lets a Read-capable triage agent or orchestrator recover the token without opening bundle markdown, which defeats the proof-of-read gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Keep the token out of any triage-visible file. Store the coordinator copy in private state or a non-derivable sidecar, and compare ingest against that private source.
  - From Cursor-Innovation: Add _extract_evidence_token(bundle_text) used by ledger_ingest; reject rows when the token is missing from bundle_path, mismatched, or bundle_path is unreadable; keep manifest evidence_token absent or non-authoritative
  - From Cursor-Requirements: Validate against the token parsed from bundle.bundle_path on disk at ingest time; keep the nonce only in bundle markdown (omit it from manifest issues[] or treat the manifest field as non-authoritative)
  - From Codex-Requirements: Keep the raw token out of predictable triage-readable files. Store only a token hash in the manifest and compare hash(parsed.evidence_token), or parse the expected token from bundle_path during ingest.
  - From Cursor-dyn-Evidence Ingest Guard: Omit evidence_token from serialized manifest.json; at ingest parse the expected token from each bundle markdown on disk via bundle.bundle_path and compare parsed.evidence_token to that file-derived value only
  - From Codex-dyn-Evidence Ingest Guard: Do not serialize `evidence_token` into `manifest.json`. Validate against the bundle file itself, or keep the proof token in a coordinator-only sidecar whose path is never derivable from the triage batch path


### FINDING_4: Ledger cache still trusts pre-token triage rows
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Concern**: Existing triage ledger entries are still accepted by cache key alone, so fabricated pre-token rows can suppress retriage even after the new proof check lands.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add a provenance bit or token-era version to triage ledger records and treat legacy rows as unverified, or invalidate and recompute triage for rows that lack the new proof field.


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


