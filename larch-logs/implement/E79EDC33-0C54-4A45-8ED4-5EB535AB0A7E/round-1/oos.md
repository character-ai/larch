### FINDING_1: [OUT_OF_SCOPE] parent firm-heading derivation and coverage in decompose.prepare
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, dyn-dyn-plan-size
- **Severity**: major
- **Concern**: Parent-path extraction is coming from scope-based fallback logic instead of the firm-heading grammar, and the split path can miss or mis-derive complete parent firm-heading coverage. That can produce wrong piece metadata, allow incomplete splits, and make feature-only partitions fail when no parent plan exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Pass use_fallback=False or use _firm_heading_paths from plan_quality.py.
  - From codex-specialist-edge-cases: Condition firm-heading enforcement on a parent plan, or allow a feature-only placeholder while preserving acceptance/dependency checks.
  - From dyn-dyn-plan-size: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_3: [OUT_OF_SCOPE] symlinked plan-file handling is inconsistent across size checks
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-testing
- **Severity**: major
- **Concern**: Symlinked plan paths are being handled inconsistently between the size-check path and the override path, so the guard can inspect one byte stream while the writer or override logic acts on another.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Align symlink policy between check-size and set-oversize-override.
  - From cursor-specialist-edge-cases: Reuse _canonical_plan_for_override in check_plan_size_main.
  - From codex-specialist-testing: Reject symlinks on the original path before calling resolve(), or perform containment validation on the pre-resolved path and reject symlinks up front.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_4: [OUT_OF_SCOPE] publish guard can drift from the artifact actually published
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-plan-size
- **Severity**: major
- **Concern**: The publish guard is checking `plan.txt`, but the publish path writes `composed-plan.md`. After override updates, the composed file can lag or omit the override trailer, so the checked artifact and the published artifact can diverge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Re-check size on composed-plan.md or assert compose freshness before publish.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-plan-size: Make override atomic in Python: have set_oversize_override_main (or a shared helper) always unlink composed-plan.md on success, and/or have publish_core recompose from plan.txt (or run an equality/freshness check) immediately before named-block write so the published artifact cannot lag plan.txt.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_12: [OUT_OF_SCOPE] mechanical_churn advisory breadcrumb can blur override intent
- **Reviewer(s)**: dyn-dyn-plan-size
- **Severity**: minor
- **Concern**: The Step 2b.5 breadcrumb always emits the mechanical-churn advisory even when soft-advisory state comes from override suppression, so the visible signal can read like churn relief instead of an explicit operator override.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-plan-size: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_13: [OUT_OF_SCOPE] duplicated optional key sets need one source of truth
- **Reviewer(s)**: dyn-dyn-plan-size
- **Severity**: minor
- **Concern**: The duplicated optional-key lists in the two consumers can drift out of sync, which risks one side preserving override data that the other side drops.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-plan-size: Address the concern above.
Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

