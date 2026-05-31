### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-implement-timing-rehydration.sh:48-48
- **Concern**: Prelude doc rewrite adds an 11th canonical source line while assertion (a) still expects 40. Scenario: Plan replaces the Bash block prelude example (skills/implement/SKILL.md:116-120) with the same byte-identical guarded source line as the 37 post-Step-0 sites plus 3 pre-bootstrap sites; grep -Fxc of that line would be 41 and fail CI
- **Proposed resolution**: Set expected guarded-source count to 41, or carve the prelude fence out of the cardinality check, or document the prelude with a non-matching illustrative line

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-implement-timing-rehydration.sh:48
- **Concern**: Planned grep -Fxc source-line count of 40 conflicts with prelude doc fence. Scenario: After SKILL.md migration, 40 executable fences plus the Bash block prelude example (skills/implement/SKILL.md:116-121) will both contain the byte-identical canonical source line, so grep -Fxc returns 41 and the new assertion fails in CI even when migration is correct
- **Proposed resolution**: Count only executable fences (e.g. awk fence scanner like Invariant C, or exclude the prelude line range), assert >=40 with a separate ==1 doc check, or use a non-identical commented example in the prelude

### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-implement-timing-rehydration.sh:48
- **Concern**: Guarded source-line grep count is 40 but prose also gets the canonical line. Scenario: The plan replaces the Bash block prelude example (skills/implement/SKILL.md:116-121) with the same one-line source form while asserting grep -Fxc count == 40 for the guarded source pattern; 37 post-Step-0 + 3 pre-bootstrap + 1 prose = 41 identical lines, so CI fails after an otherwise correct SKILL migration
- **Proposed resolution**: Set the expected guarded-source count to 41, or exclude the prose fence from the grep (e.g., assert 40 outside the prelude section only)

### FINDING_4:
- **Reviewer(s)**: Cursor-dyn-writer-source-safety
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/write-session-env.sh (proposed emit_plugin_root_env); scripts/implement-bootstrap.sh:563-586
- **Concern**: Resume-tail emit trusts session-env value without re-validation before writing a sourceable file. Scenario: Post-Step-0 blocks dot-source plugin-root.env; a hostile or malformed LARCH_CLAUDE_PLUGIN_ROOT= line in session-env.sh can become executable shell when sourced (worse than today's awk-to-variable path)
- **Proposed resolution**: Inside emit_plugin_root_env, reuse the existing ^[A-Za-z0-9_./~+-]{1,512}$ plus absolute-path checks from write-session-env.sh:136-145 on the value argument; skip the write when validation fails (same as empty/missing)
