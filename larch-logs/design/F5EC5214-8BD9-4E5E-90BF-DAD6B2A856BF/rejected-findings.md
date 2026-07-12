### [Plan Review] FINDING_1

### FINDING_1: Preserve persist-design-assessment stdout asymmetry
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: The proposed shared parser and emitter helpers must preserve the existing stdout difference between guideline and invariant persistence. `persist_design_assessment_main` emits `ARCHITECTURAL_GUIDELINE_ASSESSMENT_PERSIST_*` rows, including failed-flag and file-path cases, while `invariants_persist_design_assessment_main` remains stdout-silent on success and most failures. Both verbs remain in `_MACHINE_STDOUT_KEYS`, so the plan needs to encode this distinction explicitly and test both paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add a descriptor persist_stdout policy (or keep separate entry emitters) and add an explicit required regression that invariant persist-design-assessment success/failure stdout stays empty while guideline paths keep the existing ARCHITECTURAL_GUIDELINE_ASSESSMENT_PERSIST_* grammar
  - From Cursor-Innovation: Add a descriptor-level persist-stdout policy (or keep separate entry emitters) and add an explicit required regression that invariant `persist-design-assessment` stdout stays empty while guideline paths keep the existing `ARCHITECTURAL_GUIDELINE_ASSESSMENT_PERSIST_*` grammar.


### [Plan Review] FINDING_2

### FINDING_2: Preserve per-kind invalidate artifact sets
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: The guideline and invariant invalidation paths intentionally delete different artifact sets. Guideline invalidation removes `LEGACY_WARNING` and `LEGACY_WARNING_ENV` in addition to guideline staged, durable, dropped, and sidecar artifacts, while invariant invalidation uses a shorter set without those legacy entries. A generic invalidation helper must represent this divergence to avoid stale guideline warnings or deleting unrelated legacy files during invariant invalidation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add invalidate_artifacts (or equivalent) per GUIDELINES/INVARIANTS instance and a parity test that guideline invalidate removes legacy warning artifacts while invariant invalidate leaves unrelated legacy files untouched
  - From Cursor-Innovation: Add per-kind `invalidate_artifacts` (or equivalent) on `AssessmentKind` and a parity test that guideline invalidate clears legacy warning artifacts while invariant invalidate does not touch them.

