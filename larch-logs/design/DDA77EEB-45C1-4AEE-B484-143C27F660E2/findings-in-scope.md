### FINDING_1: Binding convention sentence must stay verbatim
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan allows rephrasing the `SKILL.md` non-normative-index binding sentence on `flags.md` line 9 while issue acceptance requires that relationship verbatim. The Approach only says to keep the table relationship as a non-normative index, and Recommended edits say to keep that relationship’s meaning intact. An implementer can shorten the opening block, paraphrase the Binding convention sentence, and still pass parser smoke tests, closure ratchet checks, and growth lint while missing the issue’s verbatim acceptance criterion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Align plan language with the issue acceptance contract: require preserving flags.md line 9 verbatim (or quote the exact sentence under Recommended edits / Approach) and drop the meaning-intact paraphrase allowance for that line
  - From Cursor-Pragmatic: Require byte-preservation of the existing Binding convention sentence (or quote it as a do-not-edit line); delete the meaning-intact carve-out for that sentence.

### FINDING_2: Opening-block compression lacks anchored header triplet guard
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: Opening-contract compression has no explicit guard for the references header triplet enforced in CI. The plan directs shortening the opening contract, but `flags.md` lines 3–7 must keep anchored `**Consumer**:`, `**Contract**:`, and `**When to load**:` headers per `scripts/test-references-headers.sh` (test-harnesses-1). Merging or reheading that block fails CI even when flag/parser contracts stay intact and listed plan tests may still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add one edge-case or Recommended-edits bullet: keep those three anchored headers byte-stable; compress only their paragraph bodies.
  - From Cursor-Pragmatic: Add an Edge cases bullet: preserve those three anchored header lines verbatim; only shorten their paragraph text.

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/flags.md:9
- **Concern**: [SCOPE-REDUCTION] Plan allows rephrasing the binding-convention sentence while issue scope requires it verbatim. Scenario: Issue acceptance requires preserving the non-normative-index relationship to the SKILL.md table verbatim; the plan Recommended edits say keep that relationship's meaning intact and Approach item 2 only names the relationship without a byte-stable constraint. An implementer can shorten line 9, pass parser and closure checks, and still miss acceptance.
- **Proposed resolution**: Tighten the plan: preserve flags.md line 9 verbatim (or explicitly mark it do-not-edit); drop meaning-intact wording for that sentence.

### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/flags.md:23-24
- **Concern**: [SCOPE-REDUCTION] Plan preserve list and Edge cases push new `--hard` rejection prose into flags.md. Scenario: `flags.md` documents `--approve` and `--manual`/`-m` rejections only; `--hard` rejection lives in `design_argv.py` and `SKILL.md`. Keep-exact-tokens plus the Edge cases bullet grouping `--hard` with flags.md rejection tokens invites adding new normative text, expanding scope beyond density-only compression.
- **Proposed resolution**: Remove `--hard` from the preserve list and Edge cases rejection bullet; state explicitly that `--hard` stays undocumented here and rejected by parser only.
