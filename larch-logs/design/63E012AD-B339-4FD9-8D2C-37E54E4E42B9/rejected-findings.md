### [Plan Review] FINDING_1

### FINDING_1: Fluff-analysis coverage render omits per-run `run_id` rows
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: blocking
- **Concern**: The guideline assessment coverage render spec is aggregate-only (runs scanned, artifact count, clean/deviation totals), while `_collect_guideline_assessment_coverage` already records per-run `run_id` / `assessment_kind` and `test-fluff-analysis.sh` expects assessment-only design runs (e.g. `RUN-DSGN-ASSESS` with zero finding records) to appear by `run_id` under `## Guideline assessment coverage`. Aggregate counts alone cannot satisfy that harness assertion when multiple design runs exist, so assessment-only runs may be counted in totals yet remain invisible and unauditable in fluff-analysis output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend the section 5 coverage output to render per-run rows (at minimum `run_id` and `assessment_kind`, optionally `has_artifact`) beneath the aggregate summary, and mirror the same shape in `fluff-analysis.md` so the harness assertion and acceptance audibility criteria align.
  - From Cursor-Pragmatic: Implementation either drops the per-run assertion or fails the harness despite meeting the written render contract. Add a per-run subsection (for example a `run_id | assessment_kind` table) under `## Guideline assessment coverage`, or narrow the test to assert only aggregate totals.
  - From Codex-Pragmatic: Render per-run coverage details from assessment_coverage, for example a compact table or bullet list with run_id and assessment_kind, alongside the aggregate counts.


### [Plan Review] FINDING_2

### FINDING_2: `--assessment-file` not confined to validated `--design-tmpdir`
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan validates symlink and readability for `--assessment-file` but does not require the resolved path to lie under the validated `--design-tmpdir`. A mistaken or hostile invocation could copy content from outside the session tmpdir into committed `architectural-guideline-assessment.md`, bypassing the design-tmpdir write boundary the publish path assumes for Gate C inputs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Committed design logs may contain prose that never lived under the validated session tmpdir. After tmpdir validation, require `Path(--assessment-file).resolve()` to be under the validated design tmpdir (reject with non-zero stderr otherwise); keep the existing TOCTOU re-stat immediately before read.


