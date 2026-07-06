### [Plan Review] FINDING_2

### FINDING_2: Legacy fallback labels remain in tally agreement rows
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Concern**: `plan_review_tally` still uses a separate legacy fallback dict for agreement rows, so empty `slot_tool[pos]` positions can continue to emit Claude/Codex/Cursor labels after the design moves to semantic dispatch, splitting calibration labels across modules.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an explicit plan_review_tally.py step to reuse the same design semantic fallbacks (codex-validity/codex-plan-fidelity/codex-pragmatism) for the _voter_agreement_row_for_item path


