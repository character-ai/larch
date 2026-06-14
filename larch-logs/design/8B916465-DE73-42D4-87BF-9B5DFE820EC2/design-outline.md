## Proposed Design Outline

### Goals
- Eliminate the ambiguity that allows orchestrators to use Bash/Python tool calls to extract and print the final-summary body
- Ensure the `## Review Phase Detail` section is always visible as plain chat text
- Add structural regression pins that fail CI if a bash fence in SKILL.md references `LARCH_FINAL_SUMMARY_BEGIN`

### Non-goals
- Changing wrapper script logic or the content/format of `final-summary.md`
- Modifying the marker protocol itself
- Changing how `render-final-summary.sh` produces the summary body

### Approach sketch
- Add explicit prohibition sentence at every emit site in `skills/design/SKILL.md`
- Fix `skills/implement/SKILL.md` Step 17 prose that sanctions `Bash cat`; add prohibition at NEVER #17 and Step 18b
- Add awk bash-fence absence pin in `scripts/test-design-structure.sh`
- Add Python require/forbid checks in `scripts/test-implement-structure.sh`

### Surfaces in scope
- `skills/design/SKILL.md`
- `skills/implement/SKILL.md`
- `scripts/test-design-structure.sh`
- `scripts/test-implement-structure.sh`

### Open questions
- None.
