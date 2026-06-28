## Proposed Design Outline

### Goals
- Reduce always-loaded `/implement` SKILL.md by ~17+ lines
- Relocate `--force` BYPASS log grammar and bypass carve-outs to `references/force-bypass.md` (loaded only when `force_requested=true`)
- Relocate arch-guidelines `present+ok` path (assessment authoring + write-staged fence) to `references/step-architectural-guidelines-present.md` (loaded only when status is `present` with ok diff)

### Non-goals
- No changes to Python code, scripts, or implementation behavior
- No changes to the `--force` flag-table row or item-4 skip breadcrumb
- No changes to the `absent`/`invalid`/`diff-failed` routing paths for arch-guidelines

### Approach sketch
- Create `skills/implement/references/force-bypass.md` with BYPASS grammar, canonical kind tokens, and carve-outs
- Create `skills/implement/references/step-architectural-guidelines-present.md` with assessment-authoring body, write-staged fence, and Phase A completion instructions
- In SKILL.md: replace Force mode paragraph (line 208) with a 2-line MANDATORY READ pointer; replace `present+ok` body (lines 664-674) with a 1-line MANDATORY READ pointer (keeping "Continue to Step 8..." and "Do not call..." in SKILL.md)
- Update `scripts/test-implement-fence-shape.sh`: EXPECTED_NEW 22→21 (one fence removed from SKILL.md)
- Update `scripts/test-plan-adequacy-audit.sh`: add FORCE_BYPASS_REF, update 3 assertions to check reference file instead of SKILL.md

### Surfaces in scope
- `skills/implement/SKILL.md`
- `skills/implement/references/force-bypass.md` (NEW)
- `skills/implement/references/step-architectural-guidelines-present.md` (NEW)
- `scripts/test-implement-fence-shape.sh`
- `scripts/test-plan-adequacy-audit.sh`

### Open questions
- None.
