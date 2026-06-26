### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/fluff-analysis/scripts/fluff-analysis.py
- **Concern**: Guideline assessment coverage render spec omits per-run run_id rows that tests and acceptance require (incomplete fix for prior round-3 coverage visibility). Section 5 defines only aggregate columns (runs scanned, runs with artifact, clean count, deviation count) while `_collect_guideline_assessment_coverage` already records per-run `run_id`/`assessment_kind`, and `test-fluff-analysis.sh` requires the emitted report to list `RUN-DSGN-ASSESS` for assessment-only design runs with zero finding records.. Scenario: An assessment-only design run can be counted in totals yet never appear by run_id in `## Guideline assessment coverage`, so zero-finding design runs are not auditable in fluff-analysis output and the planned `RUN-DSGN-ASSESS` fixture assertion has no render contract to implement against.
- **Proposed resolution**: Extend the section 5 coverage output to render per-run rows (at minimum `run_id` and `assessment_kind`, optionally `has_artifact`) beneath the aggregate summary, and mirror the same shape in `fluff-analysis.md` so the harness assertion and acceptance audibility criteria align.



### FINDING_2:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/fluff-analysis/scripts/fluff-analysis.py:591-623
- **Concern**: Fluff-analysis coverage render spec conflicts with planned fixture assertions. Scenario: The plan defines only an aggregate coverage table (runs scanned, artifact count, clean/deviation totals) but `test-fluff-analysis.sh` requires listing `RUN-DSGN-ASSESS` by run_id when that run has zero finding records. Aggregate counts alone cannot satisfy that assertion once multiple design runs exist in the fixture corpus.
- **Proposed resolution**: Implementation either drops the per-run assertion or fails the harness despite meeting the written render contract. Add a per-run subsection (for example a `run_id | assessment_kind` table) under `## Guideline assessment coverage`, or narrow the test to assert only aggregate totals.



### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: security
- **Location**: python/architectural_guidelines.py:61-63
- **Concern**: `--assessment-file` is not confined to the validated `--design-tmpdir`. Scenario: The plan validates symlink and readability but allows any absolute readable regular file. A mistaken or hostile invocation can copy out-of-tmpdir content into committed `architectural-guideline-assessment.md`, bypassing the design-tmpdir write boundary the publish path assumes for Gate C inputs.
- **Proposed resolution**: Committed design logs may contain prose that never lived under the validated session tmpdir. After tmpdir validation, require `Path(--assessment-file).resolve()` to be under the validated design tmpdir (reject with non-zero stderr otherwise); keep the existing TOCTOU re-stat immediately before read.



### FINDING_4:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: plan.txt:159-165,179
- **Concern**: Coverage collection is still aggregate-only, so the assessment-only fixture cannot surface RUN-DSGN-ASSESS or any other run_id.. Scenario: Assessment-only design runs remain invisible in fluff-analysis, and the new test that expects the fixture run id will fail.
- **Proposed resolution**: Render per-run coverage details from assessment_coverage, for example a compact table or bullet list with run_id and assessment_kind, alongside the aggregate counts.



### FINDING_5:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/gc_run_logs.py:19-27; skills/gc-run-logs/SKILL.md:13-20; docs/run-logs.md:535-537
- **Concern**: design keep set omits architectural-guideline-assessment.md. Scenario: GC slimming will delete the new committed assessment file from older design runs, so audit-runs and fluff-analysis lose the evidence this feature adds and the run log stops being auditable after retention kicks in
- **Proposed resolution**: Add architectural-guideline-assessment.md to the /design consumer-core keep set in gc-run-logs code and skill docs, mirror the retention note in docs/run-logs.md, and add a regression test in python/test_gc_run_logs.py



