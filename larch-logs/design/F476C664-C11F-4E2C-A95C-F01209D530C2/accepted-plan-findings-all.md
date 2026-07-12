### FINDING_1: Class-open follow-ups can be omitted
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: major
- **Concern**: Follow-up generation considers only terminal verdict rows, so fixed instances with incomplete sibling coverage may produce no follow-up body.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In render_report, build follow-up content from terminal verdict rows plus class-open rows (legacy_schema=false, deep complete, class_complete=false); write follow-up-issue.md when either set is non-empty
  - From Cursor-Innovation: Extend render_report to build follow-up-issue.md when class-open ledger rows exist even if terminal verdict followups are empty; append class-open bullets alongside any terminal findings


### FINDING_2: Legacy rows can fabricate risk or class-open claims
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-dyn-Schema Contract Auditor, Codex-dyn-Schema Contract Auditor
- **Severity**: major
- **Concern**: Persisted or ingested rows missing current-schema fields may receive defaults and be rendered as current evidence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Set legacy_schema=true when loading or ingesting prior key shapes; include only legacy_schema=false rows with populated current-schema fields in Introduced risk and Instance fixed class open sections and follow-up bodies
  - From Cursor-Pragmatic: In `_ledger_record_from_mapping`, set `legacy_schema=true` when deserialized rows lack the new current-schema key set (or have only the prior key set); keep ingest-time legacy marking for agent JSONL as planned
  - From Cursor-dyn-Schema Contract Auditor: _ledger_record_from_mapping defaults missing class_complete to false; pre-feature deep rows with legacy_schema=true would still satisfy class_complete=false and appear in ## Instance fixed, class open and follow-up generation, fabricating class-open claims the edge case forbids In render_report and follow-up assembly, include introduced-risk and class-open rows only when legacy_schema is false; for class-open also require deep stage complete with current-schema verifier output, not absent-field defaults
  - From Codex-dyn-Schema Contract Auditor: Detect missing new persisted fields while loading, mark those records legacy, and suppress risk and class-completeness claims for them


### FINDING_3: Deep ingest lacks value and cross-field validation
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: Malformed or incoherent `class_complete` and `sibling_sites` values can enter the ledger and generate unusable or missing class-open evidence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: For current-schema deep rows, reject class_complete=false unless sibling_sites is a non-empty list of path:symbol strings; reject class_complete=true when sibling_sites is non-empty unless you define an explicit allowed exception
  - From Codex-Arch: Validate new value types and sibling_sites path:symbol format, and reject invalid current-schema rows
  - From Cursor-Innovation: In the analyze_bugs.py plan step for _parse_deep_row, require sibling_sites be a list of path:symbol strings and reject rows where class_complete is false and sibling_sites is empty; allow empty sibling_sites only when class_complete is true
  - From Cursor-Pragmatic: In `_parse_deep_row`, validate `class_complete` is bool, `sibling_sites` is a list of `path:symbol` strings, reject rows where `class_complete=false` and `sibling_sites` is empty, and reject malformed sibling entries
  - From Cursor-Requirements: Extend `_parse_deep_row` (and tests) to reject current-schema rows unless `class_complete` is bool; `class_complete=true` requires at least one `path:symbol` sibling entry; `class_complete=false` requires non-empty siblings for class-open reporting; legacy 6-key rows stay accepted with `legacy_schema=true` and no fabricated class data.


### FINDING_4: Consumer-scan failures can produce false-clear verdicts
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Concern**: Scan errors or invalid evidence checkouts may be treated as empty matches, allowing certification from incomplete scans.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Use status-aware scanning. Treat grep exit 1 as no matches, but fail closed on other errors and prevent certification


### FINDING_5: Verifier risk claims are not explicitly checkout-verified
- **Reviewer(s)**: Codex-Pragmatic, Codex-Requirements
- **Severity**: major
- **Concern**: The verifier may emit `introduced_risk` based only on bundle evidence without a required targeted Grep against the current checkout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Require a targeted checkout Grep for `introduced_risk` and add a contract assertion for it
  - From Codex-Requirements: Require checkout Grep for every verifier risk verdict, including `none found`, and add the mandated #6946-shaped verifier fixture with a non-none risk


### FINDING_7: Risk provenance and report precedence are underspecified
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Codex-dyn-Schema Contract Auditor
- **Severity**: major
- **Concern**: Triage and deep-stage risk fields lack explicit validity, precedence, and refresh rules, permitting stale, masked, or nondeterministic report output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Track legacy status and field presence per stage. Emit risk only from the selected valid stage and emit class-open only for an explicit current verifier false
  - From Cursor-Innovation: Specify in the render_report plan step: when deep stage is complete and introduced_risk is present on the ledger row, prefer deep introduced_risk and reason; otherwise use triage introduced_risk; skip rows with legacy_schema=true or introduced_risk equal to none found
  - From Cursor-Pragmatic: Spell out `render_report` rules: include `## Introduced risk` when verified triage or completed deep has `introduced_risk` not equal to `none found`, prefer deep values when `deep` is in `stages_complete`, exclude `legacy_schema` rows, and include `## Instance fixed, class open` only for deep rows with `class_complete=false` and non-empty `sibling_sites`
  - From Cursor-Requirements: Specify in `render_report`: emit a row only when stored `introduced_risk` is present, not `none found`, and `legacy_schema` is false; prefer the deep-ingested value when deep stage is complete, otherwise use triage; render the `introduced_risk` string itself, not the general verdict `reason`.
  - From Codex-dyn-Schema Contract Auditor: Store stage-specific risks or define explicit precedence and clear all invalidated deep fields during triage refresh; report only the selected valid stage


### FINDING_1: Scan failures silently masquerade as empty evidence (fail-closed gap)
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: major
- **Concern**: The plan requires fail-closed behavior when consumer, later-history, revert, and diff scans fail, but `_git_stdout` collapses non-zero git exits to empty output (lines 612–616). A failed scan can read as no later commits, no consumers, or empty revert evidence, recreating false-clear blast-radius outcomes (#6931-style). The plan does not fully specify how `build_bundle_record` records scan failure versus zero consumers, how bundle/coordinator status blocks `FIXED_CLEAR` / `FIXED_LIKELY` / `CONFIRMED_FIXED`, or how widened `all_scan_files` history/revert paths stay status-aware end to end.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add explicit plan steps: emit a non-empty `## Consumers of changed symbols` error stanza (not an empty section) on scan failure; persist a bundle/coordinator status such as `consumer_scan_status=failed`; reject or downgrade clear/likely/confirmed verdicts at ingest or `_final_verdict_with_tier` when status is failed; clarify whether `all_scan_files` falls back to touched-only for history scans while certification stays blocked.
  - From Codex-Arch: Propagate command status and errors for every required evidence scan, including diff extraction, later-history, and revert scans. Mark the bundle incomplete or NEEDS_DEEP on failure, and test each failure path.
  - From Cursor-Innovation: Add status-aware later-history and revert helpers (distinct from grep exit `1` = no matches). On scan error, fail closed via the existing mechanical `NEEDS_DEEP` pattern with a bounded reason instead of writing empty history sections
  - From Cursor-Innovation: On checkout or grep tool failure, triage may return `FIXED_CLEAR` while consumer evidence is incomplete, undermining the blast-radius goal before deep verification Name the bundle-level behavior: on any consumer scan error, set mechanical `NEEDS_DEEP` with a bounded reason (same pattern as malformed plan / bad fix SHA) and assert it in tests
  - From Cursor-Pragmatic: Add an explicit per-bundle scan status in bundle markdown (for example consumer_scan_status=failed plus reason), set mechanical_verdict=NEEDS_DEEP or equivalent coordinator gate on failure, and require triage/verifier agents to treat failed scans as insufficient evidence. Cover coordinator plus agent contract in tests.


### FINDING_2: `introduced_risk` ingest validation incomplete for current-schema triage and verifier rows
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Codex-Requirements
- **Severity**: major
- **Concern**: The plan validates `introduced_risk`, `class_complete`, and `sibling_sites` for current verifier rows but does not define equivalent triage ingest validation for the current seven-key shape. Malformed values—a non-string, empty string, or incoherent claim—can enter the ledger and break `## Introduced risk` rendering or precedence when deep verification never runs. Verifier strict ingest also permits empty `introduced_risk` strings instead of rejecting them or requiring the `none found` sentinel.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Mirror verifier rules in `_parse_triage_row` for the current seven-key shape: require `introduced_risk` to be a non-empty string; reject malformed current rows; add a plan-mandated test that bad triage `introduced_risk` values are rejected while legacy six-key rows still ingest as `legacy_schema=true`.
  - From Cursor-Pragmatic: Add current-triage validation mirroring verifier rules at minimum: introduced_risk must be a string, only none found or a non-empty risk claim; reject incoherent values at ingest.
  - From Codex-Requirements: Require non-empty introduced_risk strings for both current schemas and a non-empty evidence reason for reported risks; keep none found as the exact no-risk sentinel


### FINDING_5: Instance verdict and class completeness are conflated in ingest and reporting
- **Reviewer(s)**: Codex-Pragmatic, Codex-Requirements
- **Severity**: major
- **Concern**: The accepted cross-field validation fix remains incomplete because class completeness is not tied to instance verdict. `UNVERIFIABLE`, `NOT_FIXED`, `REGRESSED`, or `INCOMPLETE` rows may require `class_complete=false` without known sibling sites, so strict ingest can reject valid fail-closed rows. Conversely, when siblings exist, the report can mislabel an unfixed instance as fixed and append it to follow-up content. A verifier emitting `INCOMPLETE` with `class_complete=false` can be misrendered as “Instance fixed, class open.”
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Allow false with an empty sibling list for non-CONFIRMED_FIXED verdicts. Require nonempty siblings only for CONFIRMED_FIXED plus false, and restrict class-open reporting and follow-up generation to that combination.
  - From Codex-Requirements: Define verdict as instance-level and class_complete as sibling-level, render class-open only for confirmed instances, and add the required duplicated-regex fixture


### FINDING_6: Acceptance criterion #6632 is not committed in the testing strategy
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: Binding scope requires a fixture where the same regex/pattern appears in two modules, only one is fixed, and the verifier yields `class_complete=false` with a listed sibling site. The plan tests #6946, generic schema checks, and a report fixture, but never commits to the #6632 end-to-end shape in its testing strategy.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add an explicit #6632-shaped fixture test: duplicate pattern across two modules, one-sided fix, verifier ingest with non-empty `sibling_sites`, and assert class-open report/follow-up eligibility


