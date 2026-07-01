### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/flags.md:9
- **Concern**: [SCOPE-REDUCTION] Plan allows rephrasing the binding-convention sentence while issue scope requires it verbatim. Scenario: Issue acceptance requires preserving the non-normative-index relationship to the SKILL.md table verbatim; the plan Recommended edits say keep that relationship's meaning intact and Approach item 2 only names the relationship without a byte-stable constraint. An implementer can shorten line 9, pass parser and closure checks, and still miss acceptance.
- **Proposed resolution**: Tighten the plan: preserve flags.md line 9 verbatim (or explicitly mark it do-not-edit); drop meaning-intact wording for that sentence.

### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/flags.md:23-24
- **Concern**: [SCOPE-REDUCTION] Plan preserve list and Edge cases push new `--hard` rejection prose into flags.md. Scenario: `flags.md` documents `--approve` and `--manual`/`-m` rejections only; `--hard` rejection lives in `design_argv.py` and `SKILL.md`. Keep-exact-tokens plus the Edge cases bullet grouping `--hard` with flags.md rejection tokens invites adding new normative text, expanding scope beyond density-only compression.
- **Proposed resolution**: Remove `--hard` from the preserve list and Edge cases rejection bullet; state explicitly that `--hard` stays undocumented here and rejected by parser only.
