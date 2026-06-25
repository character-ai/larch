## Proposed Design Outline

### Goals
- Combine `architectural-guidelines read` + `materialize-diff` into a single `prepare` verb that returns `STATUS` and (when present) the materialized diff in one foreground turn.
- Reduce Phase A cost by ~1 foreground turn per present-file pass (compounds on reassessment reruns and Step 16 pin).
- Keep `write-staged` separate; prompt-side judgment between materialize and write cannot fold.

### Non-goals
- No changes to `write-staged`, `pin-note-from-staged`, `invalidate`, `present-note`, or `read` verbs.
- No changes to `/design` Step 2b's use of `architectural-guidelines read`.
- No backward-compat shims for the deleted `read.sh` + `materialize.sh` wrappers.

### Approach sketch
- Add `prepare_main` to `python/architectural_guidelines.py`: invalidate stale artifacts, read guidelines; if present, materialize diff; emit combined STATUS + content block + diff status + diff block.
- Register `("architectural-guidelines", "prepare")` in `python/cli.py` and `python/test_design_cli_ports.py`.
- New thin wrapper `skills/implement/scripts/step-architectural-guidelines-prepare.sh` (reads `FORKED_TARGET_RESOLVED`, calls `prepare`).
- Update `skills/implement/SKILL.md` Phase A: replace the 2 fences with 1, simplify branching prose.
- Delete retired `read.sh` + `materialize.sh` and their `.md` siblings; update `scripts/residual-bash-paths.txt`.
- Update `test-implement-fence-shape.sh` (`EXPECTED_NEW` 32 → 31) and `skills/implement/references/conflict-resolution.md`.
- Add `prepare_main` tests to `python/test_architectural_guidelines.py`; update `test-architectural-guidelines-step.sh`.

### Surfaces in scope
- `python/architectural_guidelines.py`
- `python/cli.py`, `python/test_design_cli_ports.py`
- `python/test_architectural_guidelines.py`
- `skills/implement/SKILL.md`, `skills/implement/references/conflict-resolution.md`
- `skills/implement/scripts/` (new `prepare.sh/.md`; delete `read.sh/.md` + `materialize.sh/.md`)
- `scripts/residual-bash-paths.txt`, `scripts/test-implement-fence-shape.sh`
- `skills/implement/scripts/test-architectural-guidelines-step.sh/.md`

### Open questions
- None.
