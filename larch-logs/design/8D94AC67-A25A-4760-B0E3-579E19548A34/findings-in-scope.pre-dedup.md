### FINDING_1:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/core/architectural_guidelines.py:257-284
- **Concern**: Parser tracking text says store normal detail bullets but flush rules emit only Why/Deviate for unmarked entries. Scenario: An implementer may treat Guidance/Note/Run bullets as storable detail and emit them once mechanized-aware state exists, breaking the acceptance criterion that unmarked entries stay byte-for-byte and bloating the normalized payload across many live entries with Guidance bullets
- **Proposed resolution**: Clarify parse state as heading plus optional mechanized, Why, and Deviate fields only; explicitly state all other bullets remain ignored and never emitted on either branch



### FINDING_2:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/tests/core/test_architectural_guidelines.py
- **Concern**: Testing strategy omits a byte-exact unmarked regression case with extra Guidance bullets. Scenario: The planned parser refactor is the main regression surface; a Why/Deviate-only fixture would not catch accidental emission of Guidance bullets that today are silently dropped in production entries like G-Fix-1 and G-Py-15
- **Proposed resolution**: Add one mandated test mirroring a Guidance-bearing unmarked entry with an exact expected normalized string proving Guidance is still omitted ## Findings 1. **correctness** — `python/larch/core/architectural_guidelines.py:257-284`: The plan tells the implementer to track "normal detail bullets" while also requiring unmarked entries to remain byte-for-byte identical to today's Why/Deviate-only output. Those two instructions conflict. Today the parser ignores `Guidance:`, `Note:`, and other non-Why bullets; many production entries rely on that behavior. Revise the plan to define parse state as heading plus optional `Mechanized`, `Why`, and `Deviate` fields only, and state explicitly that every other bullet stays ignored and is never emitted. 2. **risk-integration** — `python/tests/core/test_architectural_guidelines.py`: The testing strategy lists marked, unmarked, and mixed cases, but not the edge case already documented in the plan: an unmarked entry with extra bullets such as `Guidance:` must still omit them. That omission matters because this change rewrites parser state handling. Add one byte-exact regression test using a `Guidance:`-bearing unmarked fixture (G-Py-15 shape) so accidental emission cannot slip through. [OUT_OF_SCOPE] **architecture** — `ARCHITECTURAL_GUIDELINES.md:1-4`: The plan could add a short author note in the file intro describing the `- Mechanized:` marker convention for future graduations. The issue does not require it; markers on G-Cfg-1 and G-Bash-3 are enough for this batch.



