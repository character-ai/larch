### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/issue/analyze_bugs.py:840-857,1151-1154
- **Concern**: Unverified triage verdicts still drive deep queue, sampling, and report. Scenario: Plan adds triage_evidence_verified and re-queues unverified rows for triage, but _priority_deep_candidates, the FIXED_CLEAR/FIXED_LIKELY sample pool, and _final_verdict still read record.triage_verdict without a verification gate. Legacy fabricated SUSPECT/NEEDS_DEEP rows can enter the deep queue in the same run; fabricated FIXED_CLEAR/LIKELY rows can still appear in the Stage 3 report.
- **Proposed resolution**: In _priority_deep_candidates, the sample pool, and _final_verdict, treat triage_verdict/triage_needs_deep as absent unless _triage_complete(record, refresh=...) is true (or triage_evidence_verified is true). Add tests that unverified ledger rows do not enqueue deep work and do not surface triage verdicts in render_report.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/issue/analyze_bugs.py:998-1016
- **Concern**: Plan omits evidence_token from the strict triage row field list. Scenario: The agent and ingest sections require evidence_token, but the TriageIngest/_parse_triage_row bullet list names only the original five fields. An implementer following that list can leave _strict_keys unchanged, so rows without evidence_token still parse and the file-read gate never runs.
- **Proposed resolution**: Add evidence_token to the TriageIngest dataclass, the _parse_triage_row allowed-key set, and the plan's required-field enumeration so schema validation and bundle-file validation stay aligned. ## Findings ### 1. [correctness] `python/larch/issue/analyze_bugs.py:840-857, 1151-1154` — Unverified triage verdicts still drive deep queue, sampling, and report The plan closes the cache-skip hole with `triage_evidence_verified` and `_triage_complete`, but it does not update downstream consumers that already read `record.triage_verdict`. if record and record.triage_verdict == "SUSPECT": by_priority.append((1, bundle, record, "triage")) elif record and (record.triage_verdict == "NEEDS_DEEP" or record.triage_needs_deep): by_priority.append((2, bundle, record, "triage")) if record and record.triage_verdict: if record.triage_verdict in {"SUSPECT", "NEEDS_DEEP"} or record.triage_needs_deep: return "NEEDS_DEEP", record.triage_reason, record.triage_missing_items, record.sampled return record.triage_verdict, record.triage_reason, record.triage_missing_items, record.sampled Legacy fabricated rows can still enqueue expensive deep work and color the report before token-verified retriage completes. Gate these paths on `_triage_complete` / `triage_evidence_verified`, same as pending-triage selection. ### 2. [correctness] `python/larch/issue/analyze_bugs.py:998-1016` — Plan omits `evidence_token` from the strict triage row field list The plan requires `evidence_token` in agent JSONL and ingest validation, but the `TriageIngest` / `_parse_triage_row` enumeration lists only `issue`, `verdict`, `missing_items`, `reason`, and `needs_deep`. That mismatch is an implementation footgun: `_strict_keys` may stay at five fields and ingest will keep accepting token-free rows. Add `evidence_token` to the dataclass, strict keys, and the plan's required-field list. --- **Prior-round note:** Accepted findings 1–4 look addressed in the plan. I did not re-raise rejected FINDING_5 or OOS_2, and I did not duplicate OOS_1.



### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: plan.txt:45-55
- **Concern**: The triage row schema omits `evidence_token` even though later ingest logic requires `parsed.evidence_token`.. Scenario: As written, `_parse_triage_row` would reject any token-bearing row as having an unexpected field, so proof-of-read validation can never accept valid triage output.
- **Proposed resolution**: Add `evidence_token` to `TriageIngest` and the allowed triage fields, or move token capture outside the strict row schema before validation.



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/issue/analyze_bugs.py:824-867,1146-1157
- **Concern**: Unverified triage verdicts still drive deep queue and Stage 3 report. Scenario: Plan adds `_triage_complete` for cache skip only. `_priority_deep_candidates` still keys off `record.triage_verdict` / `triage_needs_deep`, and `_final_verdict` still returns unverified triage fields. Legacy rows with `stages_complete: ["triage"]` but `triage_evidence_verified=False` (or fabricated pre-token rows) can still queue deep work and render FIXED_CLEAR/SUSPECT in the report while the same `ledger_compute` call re-queues them for triage.
- **Proposed resolution**: Gate deep priority, sampling pool, and `_final_verdict` on `triage_evidence_verified` (or `_triage_complete(..., "triage")`); thread the flag through `_upsert_record`; update `test_deep_queue_priority_cap_and_model_alias` and add a report/deep-queue test for unverified legacy rows.



### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/issue/analyze_bugs.py:998-1016
- **Concern**: `_parse_triage_row` field list omits `evidence_token`. Scenario: Under `### UPDATED: python/larch/issue/analyze_bugs.py`, the required-field bullet list names only five triage keys, but ingest and the agent contract require `evidence_token`. Implementers can ship `_strict_keys` still set to the old five-field allowlist, so valid rows reject or the gate is skipped.
- **Proposed resolution**: Add `evidence_token` to the `TriageIngest` / `_parse_triage_row` required-field list and `_strict_keys` allowlist in the plan and implementation.



### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: .claude/skills/analyze-bugs/SKILL.md:74,plan edge cases
- **Concern**: Prior FINDING_1 fix is incomplete for token-only orchestrator coaching. Scenario: Skill anti-relay rules forbid passing `evidence_token`, but ingest only checks that the echoed token matches the bundle file. The orchestrator has `Read` in `allowed-tools` and can open bundle markdown, then coach a toolless or lazy triage Task to echo the token without reading evidence. Fabricated verdicts still ingest. The plan edge case implies ingest catches orchestrator relay; token-only coaching passes.
- **Proposed resolution**: Revise edge-case prose to state the trust boundary explicitly (ingest proves bundle-file token match, not triage-agent Read). If that boundary is unacceptable, add a follow-on attestation path; do not claim ingest fails closed on orchestrator token relay. ### 1. [correctness] Unverified triage verdicts still drive deep queue and report (`python/larch/issue/analyze_bugs.py:824-867`, `1146-1157`) The plan’s `triage_evidence_verified` bit and `_triage_complete` helper fix cache skip in `ledger_compute` line 970, but they do not touch `_priority_deep_candidates` or `_final_verdict`. Today, a ledger row with `triage_verdict: "SUSPECT"` and `stages_complete: ["triage"]` schedules deep work (`test_deep_queue_priority_cap_and_model_alias` depends on this). After the plan lands, legacy fabricated rows would be re-queued for triage while still promoting stale SUSPECT/FIXED_CLEAR into the deep queue and Stage 3 report. Extend the plan to gate those consumers on verified triage, not only cache completion. ### 2. [correctness] `_parse_triage_row` required-field list omits `evidence_token` (`python/larch/issue/analyze_bugs.py:998-1016`) The plan’s analyze_bugs section lists five required ingest fields and omits `evidence_token`, even though the agent prompt and ingest validation sections require it. Current `_strict_keys` rejects any extra key, so this omission is an easy implementation footgun. ### 3. [risk-integration] Token-only orchestrator coaching still bypasses agent-read proof (`.claude/skills/analyze-bugs/SKILL.md`, plan edge cases) Round 1 FINDING_1 is only partially closed: skill rules ban relay, but ingest cannot distinguish an agent-read token from an orchestrator-coached one. That matches minimum-change if documented; the plan should not imply ingest catches orchestrator relay. The observed production bug (toolless agent, zero reads) is fixed by `tools: [Read]` plus fail-closed prompt language; token coaching is a separate, softer trust boundary.



### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/issue/analyze_bugs.py:824-867,1146-1157
- **Concern**: Legacy unverified triage verdicts still drive report and deep routing. Scenario: Plan adds `triage_evidence_verified` and `_triage_complete` only for pending-triage cache skip via `_complete(..., "triage", ...)`, but `_final_verdict` and `_priority_deep_candidates` still read `record.triage_verdict` / `triage_needs_deep` whenever a ledger row exists. A pre-token fabricated `FIXED_CLEAR` row therefore still renders as confirmed in Stage 3 and can skew deep selection until a successful re-ingest overwrites it; if re-triage ingest rejects all rows, the poisoned verdict remains on the report path.
- **Proposed resolution**: Apply the same verified-triage gate in `_final_verdict` and `_priority_deep_candidates`: treat records with `triage_evidence_verified=False` (or not `_triage_complete(..., "triage", ...)`) as having no triage verdict for verdict/deep purposes, matching the "not yet triaged" fallback.



### FINDING_8:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/issue/analyze_bugs.py:998-1016
- **Concern**: Plan omits evidence_token from the strict triage JSONL schema it assigns to TriageIngest and _parse_triage_row. Scenario: The plan adds a required evidence_token field in the agent contract and ingest compares parsed.evidence_token, but the _parse_triage_row bullet still lists only issue, verdict, missing_items, reason, and needs_deep. Today _strict_keys rejects any extra key, so rows that include evidence_token would fail parsing before token validation runs.
- **Proposed resolution**: Add evidence_token to the required field list for TriageIngest and _parse_triage_row, and extend _strict_keys to the six-key set {issue, verdict, missing_items, reason, needs_deep, evidence_token}.



### FINDING_9:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/issue/analyze_bugs.py:824-867,1146-1157
- **Concern**: FINDING_4 fix is incomplete: triage_evidence_verified gates cache skip only, not downstream verdict consumers. Scenario: The plan wires triage_evidence_verified into _triage_complete for pending-triage selection, but _priority_deep_candidates, the --sample pool, and _final_verdict still read record.triage_verdict without checking triage_evidence_verified. Legacy fabricated SUSPECT or FIXED_CLEAR rows can still enter the Stage 2 deep queue, calibration sample, and Stage 3 report even while cache skip is fixed.
- **Proposed resolution**: Require triage_evidence_verified before any consumer treats record.triage_verdict as authoritative: gate _priority_deep_candidates and the sample pool, and have _final_verdict ignore unverified triage fields (fall through to mechanical or NEEDS_DEEP). Add tests for report and deep-queue behavior with legacy unverified triage rows.



### FINDING_10:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/issue/analyze_bugs.py:118-124,998-1016
- **Concern**: Plan omits evidence_token from the strict triage ingest schema. Scenario: The agent is required to emit evidence_token, but the planned _parse_triage_row exact field list still contains only issue, verdict, missing_items, reason, and needs_deep. A token-bearing row would be rejected as having unexpected fields, or parsed.evidence_token would not exist for validation.
- **Proposed resolution**: Add evidence_token: str to TriageIngest and to the strict key set, validate it as a non-empty string, then compare that parsed value with the file-derived token.



### FINDING_11:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/issue/analyze_bugs.py:824-867,1146-1154
- **Concern**: Unverified legacy triage verdicts still feed deep routing and final reports. Scenario: The plan requeues legacy triage rows, but existing consumers read record.triage_verdict directly. If a pre-token fabricated FIXED_CLEAR remains and the new triage ingest rejects or produces no replacement, Stage 3 can still report it as fixed. Fabricated SUSPECT or NEEDS_DEEP rows can also affect deep queue routing.
- **Proposed resolution**: Gate every triage verdict consumer on triage_evidence_verified. Use a helper for usable triage data in pending triage, _priority_deep_candidates, sample selection, and _final_verdict, while preserving independent deep_verdict handling.



