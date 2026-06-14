## Proposed Design Outline

### Goals
- Eliminate all raw-Bash bash fences from orchestrator-facing markdown under `skills/design/references/`
- Reduce brainstorm-off path to one Bash call; brainstorm collection to one call after external launches
- Add a structural lint to `scripts/test-design-structure.sh` that fails on regression and passes on the full cleaned tree

### Non-goals
- No changes to `skills/implement/` or any skill outside `skills/design/`
- No changes to `scripts/*.md` sibling-doc files (documentation only, not orchestrator-facing)
- No structural changes to SKILL.md bash fences (prose simplification only)

### Approach sketch
- Add `--mode collect` to `design-step1d5.sh`: absorbs two brainstorm collection fences, dirty-tree checkpoint, and failure logging; entry guard completes the skip path itself (writes step-1d.5 sentinel), so SKILL.md removes its unconditional `--mode complete` call
- Move `--mode collect` and `--mode complete` launcher calls into `brainstorm.md` body (after launches, after synthesis), replacing the two raw collection fences
- Demote the superseded `plan-review.md` collector fence and voter-dispatch argv snippet from `bash` to `text` fences
- Fold the Step 2b.5 rc=2 capture-then-append pair into `design-step2b5.sh`; fold the validator-autofix Warnings appends into `design-step-validator-autofix.sh`
- Add `assert_references_bash_fences_are_scripts` to `test-design-structure.sh`: checks every `bash` fence in `references/*.md` starts with `${CLAUDE_PLUGIN_ROOT}` or launcher on first non-comment line; supports `# lint-script-only-fences: ok <reason>` suppression

### Surfaces in scope
- `skills/design/references/brainstorm.md`
- `skills/design/references/plan-review.md`
- `skills/design/scripts/design-step1d5.sh` + `.md`
- `skills/design/scripts/design-step-validator-autofix.sh` + `.md`
- `skills/design/scripts/design-step2b5.sh` + `.md`
- `skills/design/SKILL.md` (prose changes only: Step 1d.5 section, validator-autofix section, Step 2b.5 rc=2 section)
- `scripts/test-design-structure.sh` + `.md`

### Open questions
- None.
