### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: ARCHITECTURAL_INVARIANTS.md
- **Concern**: Plan mandates byte-for-byte invariant bodies but omits both paragraph texts. Scenario: /implement materializes plan.txt from the larch:plan block only; this plan lists headings and says copy supplied paragraphs without embedding them, so an implementer can paraphrase or drop lines (including INV-Pause-1 test-path wording) and still think the plan is satisfied
- **Proposed resolution**: Paste both issue Entry 1 and Entry 2 fenced paragraph blocks verbatim into the plan Approach (or Files) section so plan.txt is self-contained for byte-stable insertion

### FINDING_2:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/core/architectural_guidelines.py:55,287-305
- **Concern**: The planned `INV-*` paragraph entries do not satisfy the existing invariant parser. Scenario: `read_invariants()` will still report "No parsed invariant entries were present in ARCHITECTURAL_INVARIANTS.md." because `_INVARIANT_HEADING_RE` only matches `I-*` headings and `parse_invariant_entries()` drops non-`- Why:` body text, so the seeded rules never reach prompt or review surfaces.
- **Proposed resolution**: Extend the parser to accept the new `INV-*` paragraph shape, or change the entries to the parser's current `I-*`/`- Why:` format before landing.

### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: code-quality
- **Location**: ARCHITECTURAL_INVARIANTS.md
- **Concern**: Plan omits the two invariant body paragraphs required byte-for-byte. Scenario: /implement materializes from plan.txt only; Approach references "supplied wrapped paragraph text" without quoting the issue fences, so an implementer can paraphrase or omit INV-Gate-1 and INV-Pause-1 bodies and still satisfy the listed file edit steps
- **Proposed resolution**: Embed both full heading lines and body paragraphs from the issue anchor verbatim in the plan (under Approach or the UPDATED file section) so byte-stable copy needs no external lookup

### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/core/architectural_guidelines.py:55
- **Concern**: Proposed INV-* headings pass coverage-index but not architectural-invariants read. Scenario: _INVARIANT_ID_RE in learn_from_bugs.py accepts INV-* and the Testing strategy checks only coverage-index; _INVARIANT_HEADING_RE accepts only I-* so python/cli.py architectural-invariants read returns present with an empty parsed block and /design and /implement never surface the seeded text despite a passing test
- **Proposed resolution**: Add an Edge case noting _INVARIANT_HEADING_RE is I-* only; extend Testing strategy with python/cli.py architectural-invariants read expecting no untrusted block today, and record a follow-up to align the reader with _INVARIANT_ID_RE or reissue headings as I-*
