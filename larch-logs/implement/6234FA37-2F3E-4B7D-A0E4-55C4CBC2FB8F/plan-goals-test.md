## Goal
Fix version-bump-reasoning.md being written with consecutive blank lines (MD012 violation) by squeezing them in write_version_reasoning_fragment().

## Goal
Fix version-bump-reasoning.md being written with consecutive blank lines (MD012 violation) by squeezing them in write_version_reasoning_fragment().

## Implementation Plan

### Files to modify

1. scripts/implement-finalize.sh (line 411)
   - Replace: `printf '%s\n' "$content" > "$input_file"`
   - With: pipe through awk to collapse consecutive blank lines and drop trailing blanks
   - Awk pattern: `/^[[:space:]]*$/{blank=1; next} {if(blank){print ""; blank=0}; print}`
   - Add guard: if awk produces empty file (all-blank content), write minimal `\n`

2. scripts/implement-finalize.md
   - Update write_version_reasoning_fragment description to mention blank-line squeezing

3. scripts/test-implement-finalize.sh
   - Add test case: create reasoning file with double blank lines, run postbump,
     assert larch-log-batches/version-bump-reasoning.md has no consecutive blank lines
     (use same awk blank-check pattern already used for changelog at line 732)

## Test plan
- `/relevant-checks` (pre-commit markdownlint + shellcheck + agent-lint)
- New test case in test-implement-finalize.sh exercises the awk squeezing

## Test plan
Run /relevant-checks (pre-commit markdownlint + shellcheck + agent-lint). New test in test-implement-finalize.sh verifies no consecutive blank lines in the written batch file.
