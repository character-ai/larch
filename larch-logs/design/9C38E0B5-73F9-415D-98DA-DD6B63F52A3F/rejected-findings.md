### [Plan Review] FINDING_1

### FINDING_1: OOS prose compression conflicts with shared helper boundary
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan asks implementers to shorten OOS prose in `render_plan_review_main()` while also forbidding edits to `_oos_proposal_instruction()` / `oos_proposal_instruction()`. The plan-review OOS cap and materiality text is injected only through the shared helper, so the compression step is not executable within the stated boundary and could also spill into shared implement/voter surfaces.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: `Remove OOS from the compressible-prose list in the \`render_plan_review_main()\` section. Limit compression to the inline [OUT_OF_SCOPE] prefix line in the f-string; keep the shared OOS helper byte-stable`


