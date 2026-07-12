### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/issue/analyze_bugs.py:795-819
- **Concern**: Marker-chain detection has no evidence path for in-window ledger-only issues. Scenario: The plan requires marker-based Fix chains and persists marker references only during prefetch/metadata upsert for manifest-selected issues, while git hydration covers fix_time/touched_files/added_lines but not title/body or marker references. Historical in-window ledger rows that are not in the current manifest cannot produce marker edges, so marker chains such as those cited in the feature stay invisible until every issue is re-selected after deploy.
- **Proposed resolution**: Extend coordinator metadata for the in-window corpus: persist derived marker_references (and any needed stripped-body hash) on ledger rows during the metadata upsert pass for all canonical in-window issues, not only manifest-selected ones; or document and test an explicit bounded issue-text backfill for ledger rows missing marker_references before marker-edge construction.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/issue/analyze_bugs.py:795-819
- **Concern**: Canonical per-issue selection needs file-order ledger scanning, not load_ledger alone. Scenario: Step 3 requires choosing one analytics record per issue with updated_at and last valid append-order tie-breaking across multiple cache keys. load_ledger collapses to one row per cache_key and drops cross-key append-order evidence, so tied or legacy updated_at=0 rows can pick the wrong fix SHA and miscompute chains, chronic zones, churn, and risk routing.
- **Proposed resolution**: Add an analytics-corpus loader that scans ledger.jsonl in file order, keeps all valid rows grouped by issue, then applies the documented canonical winner; reserve load_ledger for cache-key upserts and ingest paths.



### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/issue/analyze_bugs.py:795-819
- **Concern**: Canonical selection cannot implement the required last-valid-append tie-break with the planned ledger representation. Scenario: `load_ledger` currently returns only a cache-key dictionary and discards append order. When two valid records for one issue have equal `updated_at` values, the analytics view cannot deterministically choose the last appended record, so stale fix metadata or verdicts may drive chains, churn, chronic zones, or routing.
- **Proposed resolution**: Preserve valid append order in the loaded ledger corpus, or persist and load an explicit append sequence, then use it for the specified canonical-record tie-break.



### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/issue/analyze_bugs.py:681-700
- **Concern**: The snapshot design lacks collision-safe run identity and persisted predecessor identity. Scenario: `run_id` and `generated_at` currently use seconds. Two runs started in the same second can reuse one run directory and overwrite its manifest or snapshot. Also, the plan requires the same predecessor on every rerender but does not store the selected predecessor in `run-state.json`; later rerenders must rediscover it. This can change deltas or destroy the active run state.
- **Proposed resolution**: Use a collision-safe run identifier and persist the selected predecessor run identity in `run-state.json`; reuse that persisted predecessor during rerender.



### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/issue/analyze_bugs.py:1
- **Concern**: Churn threshold is not defined in the approach. Scenario: The issue requires a file to count as churned only when it appears in 3 or more unique fix commits inside the trailing 7-day window. Step 1 only says to compute churn from unique fix commits in that window, so an implementation can treat every touched file as churned or use the wrong cutoff.
- **Proposed resolution**: State explicitly that churned files are those touched by at least three distinct fix commits within the manifest-anchored 7-day window, and keep the existing deduplication-by-fix-commit rule.



### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/issue/analyze_bugs.py:1283
- **Concern**: Since-last-run "verified issues" has no contract. Scenario: Step 6 and Step 7 store and diff "verified issues" and "newly verified issues," but the plan never defines verified. One run can count evidence-token triage only, deep-complete only, or any final verdict, which changes delta text and snapshot identity across rerenders.
- **Proposed resolution**: Define verified once: for example, manifest-selected issues whose current canonical ledger record has evidence-verified triage and/or a completed deep stage for the active cache key. Use that same predicate for run-state storage and Since-last-run rendering.



### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/issue/analyze_bugs.py:1030
- **Concern**: Dropped deep candidates lack a named durable reason store. Scenario: Step 4 requires persisting every cap-dropped candidate with its routing reason while keeping stdout KVs unchanged. `ledger-summary.json` still only defines `DEEP_TRUNCATED_ISSUES` as bare issue IDs, and stderr warnings are not durable audit evidence.
- **Proposed resolution**: Extend the existing `ledger-summary.json` sidecar with a structured dropped-candidate list such as issue id plus promotion reason, keep `DEEP_TRUNCATED_ISSUES` stdout-compatible, and include the new field in golden/fixture coverage.



### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/issue/analyze_bugs.py:1329
- **Concern**: [SCOPE-REDUCTION] Chronic zones section adds churned-file detail beyond the spec. Scenario: Required design item 3 defines the churn metric, but item 8 limits the Chronic zones section to zone, bug count, and member issues. Step 6 also forces churned-file detail into that section and the golden fixture, adding report and test surface the acceptance criteria do not require.
- **Proposed resolution**: Compute churn internally for analytics if needed, but render Chronic zones with only zone, unique bug count, and member issues. Omit churned-file detail unless a follow-up issue expands the report contract.



### FINDING_9:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: architecture
- **Location**: plan step 6 / python/larch/issue/analyze_bugs.py:render_report
- **Concern**: [SCOPE-REDUCTION] Chronic zones report should omit churned-file detail. Scenario: The binding scope requires a churn metric and a Chronic zones section with zone, bug count, and member issues only. Listing churned files adds a presentation contract and golden-fixture surface that no acceptance criterion or routing rule consumes.
- **Proposed resolution**: Keep file-churn computation and unit tests in the analytics view; render Chronic zones with zone, unique bug count, and member issues only.



### FINDING_10:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: correctness
- **Location**: plan steps 6-7 / run-state.json
- **Concern**: verified_issues membership for Since-last-run deltas is unspecified. Scenario: The plan stores verified_issues in run-state.json and reports newly verified issues, but never defines which manifest issues count as verified at snapshot time. Implementations can disagree on mechanical-only rows, partial triage, or deep completions and emit unstable deltas on rerender.
- **Proposed resolution**: Define verified_issues as manifest issue numbers whose canonical record has a final evidence tier of MECH, TRIAGE, or DEEP and is not pending NEEDS_DEEP or not-yet-triaged; pin the rule in run-state schema text and delta tests.



### FINDING_11:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: plan step 2 / python/larch/issue/analyze_bugs.py:_upsert_record
- **Concern**: Metadata-only upsert must not mutate verdict or stage fields. Scenario: The plan adds a metadata-only ledger upsert but does not forbid reusing the verdict upsert path. A broad merge through _upsert_record could rewrite stages_complete or triage_evidence_verified and let risk promotion bypass the verified-triage gate for FIXED_CLEAR or FIXED_LIKELY rows.
- **Proposed resolution**: Add a dedicated metadata merge helper that updates only coordinator analytics keys on the existing cache-key row; state explicitly in plan and tests that stages_complete, triage_evidence_verified, and verdict fields are immutable on that path.



### FINDING_12:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: minor
- **Focus area**: architecture
- **Location**: plan.txt:33-34
- **Concern**: [SCOPE-REDUCTION] Historical git hydration and deferred ledger persistence exceed the required analytics path. Scenario: The plan adds git probes, failure handling, post-render mutations, and tests for legacy records whose absent metadata may remain unavailable under the stated compatibility contract
- **Proposed resolution**: Remove historical hydration and its persistence pass. Build analytics from metadata already present or collected by the selected-issue metadata upsert



### FINDING_13:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: minor
- **Focus area**: code-quality
- **Location**: plan.txt:47
- **Concern**: [SCOPE-REDUCTION] Durable per-candidate cap-drop reasons exceed the required logging contract. Scenario: The feature only requires dropped candidates to be logged instead of silently truncated. Persisting structured reasons expands ledger-summary state and tests without affecting routing or report correctness
- **Proposed resolution**: Keep the existing truncated issue identifiers and emit each issue and routing reason to stderr. Do not add a new durable reason schema



