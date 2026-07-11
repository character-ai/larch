## Proposed Design Outline

### Goals
- Add guideline `G-Gate-1` to `ARCHITECTURAL_GUIDELINES.md` covering fail-closed gate/producer sequencing.
- Encode three rules: ship ordering, author guidance update, and regression test requirement.

### Non-goals
- No lint, invariant, or test added in this change.
- No changes to existing guidelines or any other file.
- Does not fold into issues #6873 or #6892.

### Approach sketch
- Add a new "Fail-closed gates" section to `ARCHITECTURAL_GUIDELINES.md` after "Enforcement philosophy".
- Write a single `G-Gate-1` entry with Why, Guidance, and Deviate when bullets.
- Cite bugs #6880, #6882, and #6875 in the Why clause.

### Surfaces in scope
- `ARCHITECTURAL_GUIDELINES.md`

### Open questions
- None.
