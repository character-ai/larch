### [Plan Review] FINDING_4

### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/flags.md:23-24
- **Concern**: [SCOPE-REDUCTION] Plan preserve list and Edge cases push new `--hard` rejection prose into flags.md. Scenario: `flags.md` documents `--approve` and `--manual`/`-m` rejections only; `--hard` rejection lives in `design_argv.py` and `SKILL.md`. Keep-exact-tokens plus the Edge cases bullet grouping `--hard` with flags.md rejection tokens invites adding new normative text, expanding scope beyond density-only compression.
- **Proposed resolution**: Remove `--hard` from the preserve list and Edge cases rejection bullet; state explicitly that `--hard` stays undocumented here and rejected by parser only.


