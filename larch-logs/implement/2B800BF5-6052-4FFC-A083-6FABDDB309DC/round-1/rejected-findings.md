### [rejected] FINDING_1

**Rejected subtype:** dismissed (0 YES)

### FINDING_1: lint-classified invariants need section 4 mechanical fields
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing, dyn-dyn-proposal-wording
- **Severity**: major
- **Concern**: Section 5 can describe a `lint`-classified invariant as complete without requiring a matching section 4 lint proposal that carries the mechanical fields the operator needs: what it flags, scan surface, suppression policy, and baseline policy.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-proposal-wording: When best-home is `lint`, require a matching section 4 entry with all mechanical fields, or add an explicit cross-reference rule that every `lint`-classified invariant must have a同名 section 4 proposal before the report is complete.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** dismissed (0 YES)

### FINDING_2: readability-style brevity carve-out needs explicit override
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-proposal-wording
- **Severity**: minor
- **Concern**: The carve-out still does not explicitly say it overrides `skills/shared/readability-style.md`'s Brevity axis for report sections 4-6, so agents can keep compressing proposal wording instead of producing paste-ready text.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-proposal-wording: Extend the carve-out to say proposal wording in report sections 4–6 overrides the Brevity axis of `skills/shared/readability-style.md`, and that entries must be pasteable into target files without rewriting.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** dismissed (0 YES)

### FINDING_5: invariants-file entries need a fallback when no invariant IDs exist
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Section 5 assumes the repo scan will find invariant IDs, but there is no fallback for repos with no invariants file or an empty `ARCHITECTURAL_INVARIANTS.md`, so headings may not match the scanner regex and won't be paste-ready.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=2 JUDGE_ERROR=1

### [rejected] FINDING_10

**Rejected subtype:** dismissed (0 YES)

### FINDING_10: guideline proposals need the on-disk entry layout
- **Reviewer(s)**: dyn-dyn-proposal-wording
- **Severity**: major
- **Concern**: Proposal wording can satisfy the semantic sentence requirements while still missing the target repo's on-disk entry layout, and `guideline`-classified items can also be complete in section 5 without being verbatim pasteable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-proposal-wording: Add an explicit layout requirement: for repos with an on-disk guideline format, each proposed entry must reproduce that format (for larch: `### G-*` heading and the `- Why:` / `- Deviate when:` bullet lines), not just the three semantic fields.
  - From dyn-dyn-proposal-wording: For `guideline` classifications, either require the same entry layout as section 6 (imperative, Why, Deviate-when in target-file format) or state that such items must appear only in section 6 and must not be duplicated as incomplete section 5 stubs.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** dismissed (0 YES)

### FINDING_11: best-home classification needs routing guidance
- **Reviewer(s)**: dyn-dyn-proposal-wording
- **Severity**: minor
- **Concern**: The rewrite no longer tells the operator how best-home classification routes `lint`, `rule`, `invariants-file`, and creating a new invariants file, so the Step 5 follow-up choice is less explicit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-proposal-wording: Restore a short routing sentence after the classification list, or tie each class to the Step 5 follow-up gate it triggers.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

