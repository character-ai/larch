### FINDING_1: /design OOS cap uses unnormalized slot keys on retry/phase collector paths
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The planned per-reviewer OOS cap in `_compose_findings_from_collector` keys `oos_counts_by_slot` via `slot_by_output.get(rf, Path(rf).stem.replace("-output", ""))` without `voting.normalize_reviewer_basename`. Collector OK records for waterfall retries use paths like `cursor-plan-arch-output-retry.txt` that are absent from `slot_by_output`, so the fallback stem becomes `cursor-plan-arch-retry` instead of manifest slot `cursor-plan-arch`. That gives the logical reviewer an independent 3-OOS bucket; multiple OK records for one slot can each retain 3 OOS rows (6+ total), defeating the per-reviewer cap. `write_reviewer_status_tsv` already joins via `voting.normalize_reviewer_basename` (#4848); the cap path does not mirror that normalization, so a prior FINDING_5-style fix remains incomplete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In _compose_findings_from_collector build slot_by_norm_output from manifest rows with voting.normalize_reviewer_basename(output) -> slot; resolve each REVIEWER_FILE through voting.normalize_reviewer_basename(rf) before cap accounting (mirror write_reviewer_status_tsv #4848). Extend edge cases and failure modes to cover /design retry/phase collector paths, not only /implement label normalization.
  - From Cursor-Pragmatic: When building `slot_by_output`, also map `voting.normalize_reviewer_basename(output)` to manifest `slot`. Resolve cap identity with the same norm join before counting. Add a `_compose_findings_from_collector` test with a retry-path OK sidecar (4 OOS + 1 in-scope) asserting only 3 OOS retained for slot `cursor-plan-arch`.

### FINDING_2: Planned /design cap tests omit retry-path collector identity regression
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The new cap test covers overflow OOS plus a trailing in-scope row on canonical output paths only. It does not exercise collector `REVIEWER_FILE` paths with `-retry`/`-phase2`/`-phase3` suffixes that `_compose_findings_from_collector` already receives in production (#4848). An implementation can pass the listed tests while leaving retry-path cap keys on the wrong bucket.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add a unit test modeled on test_write_reviewer_status_tsv_retry_path_maps_to_done: manifest output cursor-plan-arch-output.txt, collector OK on cursor-plan-arch-output-retry.txt with 4 distinct OOS TSV rows plus 1 in-scope row; assert only 3 OOS retained under slot cursor-plan-arch, overflow absent, and the in-scope row kept.

### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/shared/reviewer-templates.md:245-248 and python/rendering.py:116-129
- **Concern**: [SCOPE-REDUCTION] Plan injects identical OOS cap/materiality blocks in four GENERATED_BODY sections, five hand-maintained agents, `_dynamic_agent_body`, and `_specialist_tagging`/`render_plan_review_main`. Scenario: Every `/implement` specialist prompt loads agent/pre-rendered body then appends `_specialist_tagging`; dynamic slots always go through `render specialist` after `_dynamic_agent_body`. Duplicating the cap block 2x per reviewer adds vendor tokens while the issue targets OOS over-production waste.
- **Proposed resolution**: Keep one proposal-time source: `rendering._oos_proposal_instruction()` wired into `render_plan_review_main` and `_specialist_tagging` only. In templates/agents, replace contradictory uncapped-finding sentences (round-1 FINDING_2) but omit redundant `### Out-of-Scope Observations` cap bullet triplets. Drop `_dynamic_agent_body` cap injection unless a path renders dynamic agents without `_specialist_tagging` (none today).
