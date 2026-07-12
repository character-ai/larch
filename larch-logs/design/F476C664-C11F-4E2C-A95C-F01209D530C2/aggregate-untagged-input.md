### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/issue/analyze_bugs.py:716-778
- **Concern**: Consumer-scan fail-closed lacks a machine-readable bundle flag and coordinator gate. Scenario: The plan says scan errors must fail closed, but it does not say how `build_bundle_record` records a failed consumer scan, nor how Python blocks `FIXED_CLEAR` / `FIXED_LIKELY` / `CONFIRMED_FIXED` when consumer evidence is incomplete. Today `_git_stdout` collapses non-zero exits to empty output (lines 612-616), the same pattern that caused FINDING_4. Agents or ingest could still certify from a diff-only bundle while blast radius is unknown.
- **Proposed resolution**: Add explicit plan steps: emit a non-empty `## Consumers of changed symbols` error stanza (not an empty section) on scan failure; persist a bundle/coordinator status such as `consumer_scan_status=failed`; reject or downgrade clear/likely/confirmed verdicts at ingest or `_final_verdict_with_tier` when status is failed; clarify whether `all_scan_files` falls back to touched-only for history scans while certification stays blocked.

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/issue/analyze_bugs.py:1529-1550
- **Concern**: Triage ingest omits value validation for current-schema `introduced_risk`. Scenario: The plan validates `introduced_risk`, `class_complete`, and `sibling_sites` only for current verifier rows. Current triage rows gain `introduced_risk` via strict keys but no type or shape checks. A non-string, empty, or incoherent triage risk can enter the ledger and break `## Introduced risk` rendering or precedence when deep verification never runs.
- **Proposed resolution**: Mirror verifier rules in `_parse_triage_row` for the current seven-key shape: require `introduced_risk` to be a non-empty string; reject malformed current rows; add a plan-mandated test that bad triage `introduced_risk` values are rejected while legacy six-key rows still ingest as `legacy_schema=true`.

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/issue/analyze_bugs.py:129-151
- **Concern**: Stage-specific ledger field names are not pinned. Scenario: The plan calls for stage-specific `introduced_risk` and evidence-reason fields plus round-trip tests, but it never names the exact `LedgerRecord` / `_record_json` keys (for example `triage_introduced_risk` vs `deep_introduced_risk` and matching evidence-reason columns). Report precedence and refresh-clear rules depend on those names.
- **Proposed resolution**: Add one plan bullet listing exact ledger key names for triage-stage and deep-stage risk plus evidence-reason fields, and require `_upsert_record`, `_record_json`, and `_ledger_record_from_mapping` to use those names consistently.

### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/issue/analyze_bugs.py:612-747
- **Concern**: Widened history, revert, and diff scans still need fail-closed status handling. Scenario: _git_stdout collapses git failures to empty output. A failed scan can appear as no later commits or no consumers, allowing a false clear.
- **Proposed resolution**: Propagate command status and errors for every required evidence scan, including diff extraction, later-history, and revert scans. Mark the bundle incomplete or NEEDS_DEEP on failure, and test each failure path.

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/issue/analyze_bugs.py:612-616,680-747
- **Concern**: Widened later-history and revert scans are not status-aware; they still flow through `_git_stdout`, which maps any non-zero git exit to empty output. Scenario: The plan widens `all_scan_files` into later-history and revert scans, but `_later_history` and revert `git log` still use `_git_stdout`. A missing path, bad checkout, or other git failure reads as "(none)" / empty revert evidence, recreating the #6931 false-clear blast-radius failure on consumer paths
- **Proposed resolution**: Add status-aware later-history and revert helpers (distinct from grep exit `1` = no matches). On scan error, fail closed via the existing mechanical `NEEDS_DEEP` pattern with a bounded reason instead of writing empty history sections

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: code-quality
- **Location**: python/tests/issue/test_analyze_bugs.py
- **Concern**: Acceptance criterion #6632 is not named in the testing strategy. Scenario: Binding scope requires a fixture where the same regex/pattern appears in two modules, only one is fixed, and the verifier yields `class_complete=false` with a listed sibling site. The plan tests #6946, generic schema checks, and a report fixture, but never commits to the #6632 end-to-end shape
- **Proposed resolution**: Add an explicit #6632-shaped fixture test: duplicate pattern across two modules, one-sided fix, verifier ingest with non-empty `sibling_sites`, and assert class-open report/follow-up eligibility

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/issue/analyze_bugs.py:716-778
- **Concern**: Consumer grep fail-closed has no named bundle escalation when scanning fails. Scenario: The plan requires consumer scan errors to fail closed and not imply an empty blast radius, but `build_bundle_record` does not specify how failures surface (for example mechanical `NEEDS_DEEP`, a scan-error banner, or skipping clear certification). Implementers can still emit a normal bundle that triage treats as healthy
- **Proposed resolution**: On checkout or grep tool failure, triage may return `FIXED_CLEAR` while consumer evidence is incomplete, undermining the blast-radius goal before deep verification Name the bundle-level behavior: on any consumer scan error, set mechanical `NEEDS_DEEP` with a bounded reason (same pattern as malformed plan / bad fix SHA) and assert it in tests

### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/issue/analyze_bugs.py:716-778
- **Concern**: Consumer-scan fail-closed is not wired into bundle output or certification gates. Scenario: The plan requires scan errors to block clear/certified results, but only specifies status-aware grep. It does not say how bundles distinguish scan failure from zero consumers, and build_bundle_record still lets triage emit FIXED_CLEAR via mechanical_verdict="" and unchanged agent flow. FINDING_4 is only partly addressed.
- **Proposed resolution**: Add an explicit per-bundle scan status in bundle markdown (for example consumer_scan_status=failed plus reason), set mechanical_verdict=NEEDS_DEEP or equivalent coordinator gate on failure, and require triage/verifier agents to treat failed scans as insufficient evidence. Cover coordinator plus agent contract in tests.

### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/issue/analyze_bugs.py:1529-1565
- **Concern**: Stage-specific evidence-reason fields have no agent JSONL source. Scenario: The plan adds ledger evidence-reason fields and report rendering that prefers risk plus its evidence reason, but agent updates only require introduced_risk, class_complete, and sibling_sites. Ingest parsers are not told where the evidence sentence comes from, so the new report section cannot be populated deterministically.
- **Proposed resolution**: Either add introduced_risk_evidence to triage and verifier JSONL with strict ingest validation, or drop separate evidence-reason ledger/render fields and render introduced_risk alone. Pick one contract and align agents, ingest, ledger, tests, and SKILL docs.

### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/issue/analyze_bugs.py:1529-1550
- **Concern**: Triage-stage introduced_risk validation is unspecified. Scenario: The plan validates introduced_risk, class_complete, and sibling_sites for current verifier rows and says render uses valid triage-stage risk, but it does not define triage ingest validation for introduced_risk type or allowed values. Malformed triage rows could enter the ledger and produce empty or garbage Introduced risk output.
- **Proposed resolution**: Add current-triage validation mirroring verifier rules at minimum: introduced_risk must be a string, only none found or a non-empty risk claim; reject incoherent values at ingest.

### FINDING_11:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: plan.txt:17-22,30-36
- **Concern**: FINDING_1: The accepted cross-field validation fix remains incomplete because class completeness ignores the verifier verdict. Scenario: UNVERIFIABLE, NOT_FIXED, REGRESSED, or INCOMPLETE may require class_complete=false without known sibling sites, so strict ingest rejects valid fail-closed rows. If siblings exist, the report can also falsely label an unfixed instance as fixed and append it to follow-up content.
- **Proposed resolution**: Allow false with an empty sibling list for non-CONFIRMED_FIXED verdicts. Require nonempty siblings only for CONFIRMED_FIXED plus false, and restrict class-open reporting and follow-up generation to that combination.

### FINDING_12:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: .claude/agents/bug-fix-verifier.md:planned changes
- **Concern**: The prior class-open fix remains incomplete because instance verdict and class completeness are not distinguished. Scenario: A verifier can emit INCOMPLETE with class_complete=false, which the plan then mislabels as “Instance fixed, class open”; the required #6632 fixture is also absent
- **Proposed resolution**: Define verdict as instance-level and class_complete as sibling-level, render class-open only for confirmed instances, and add the required duplicated-regex fixture

### FINDING_13:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/issue/analyze_bugs.py:1529-1576
- **Concern**: The accepted strict-ingest fix still permits empty risk claims. Scenario: The plan validates verifier introduced_risk only as a string and states no triage value validation, so an empty current-schema risk can bypass the report instead of being rejected
- **Proposed resolution**: Require non-empty introduced_risk strings for both current schemas and a non-empty evidence reason for reported risks; keep none found as the exact no-risk sentinel
