---LARCH-REJECTED-BEGIN---
## Considered Plan Review Suggestions (Not Adopted)

These reviewer suggestions were considered but not adopted. Some may already be addressed by the current plan; they are not automatically unimplemented gaps.

### [Plan Review] FINDING_1

### FINDING_1: Ignore non-Why bullets in normalization
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Concern**: The parser-state guidance is ambiguous about whether non-Why detail bullets are stored and re-emitted. That conflicts with the byte-for-byte requirement for unmarked entries and could cause Guidance/Note/Run bullets to appear in normalized output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Clarify parse state as heading plus optional mechanized, Why, and Deviate fields only; explicitly state all other bullets remain ignored and never emitted on either branch
  - From Cursor-Requirements: Revise the plan to define parse state as heading plus optional `Mechanized`, `Why`, and `Deviate` fields only, and state explicitly that every other bullet stays ignored and is never emitted.


### [Plan Review] FINDING_2

### FINDING_2: Add Guidance-bearing unmarked regression test
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Concern**: The test plan does not cover an unmarked entry with extra Guidance bullets, so the parser refactor could accidentally start emitting them without a failing regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add one mandated test mirroring a Guidance-bearing unmarked entry with an exact expected normalized string proving Guidance is still omitted
  - From Cursor-Requirements: Add one byte-exact regression test using a `Guidance:`-bearing unmarked fixture (G-Py-15 shape) so accidental emission cannot slip through

---LARCH-REJECTED-END---
