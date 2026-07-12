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


