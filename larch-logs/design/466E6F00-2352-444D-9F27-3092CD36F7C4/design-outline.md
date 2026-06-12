## Proposed Design Outline

### Goals
- Eliminate per-fence `CLAUDE_PLUGIN_ROOT` rehydration boilerplate from all post-Step-0 SKILL.md fences.
- Centralize rehydration into a single `larch-run.sh` launcher emitted by Step 0 bootstrap.
- Update the structural fence-shape harness to pin the new single-line form.

### Non-goals
- No changes to the behavior of any wrapped script.
- No changes to pre-bootstrap fences (Preflight, Step 0 initial, dirty-tree recovery, structured-invocation pin).
- No changes to session-env.sh or plugin-root.env write semantics.

### Approach sketch
- Add `emit_larch_run_sh()` to `scripts/implement-bootstrap.sh`; call it after `plugin-root.env` is written in `phase_infra()` and in the `--resume-plan-tail` path.
- `larch-run.sh` sources `plugin-root.env` (guarded), falls back to awk extract, exports `CLAUDE_PLUGIN_ROOT` and `IMPLEMENT_TMPDIR`, then execs `"$CLAUDE_PLUGIN_ROOT/$1" "$@"` (Bash 3.2 `shift`-based).
- Update SKILL.md: collapse ~30 post-Step-0 fences to `bash "$IMPLEMENT_TMPDIR/larch-run.sh" <rel-script-path>`. Update "Bash block prelude" prose.
- Update `scripts/test-implement-fence-shape.sh` to accept both old shape (guard + `$CLAUDE_PLUGIN_ROOT/...`) and new shape (`bash "$IMPLEMENT_TMPDIR/larch-run.sh" ...`).

### Surfaces in scope
- `scripts/implement-bootstrap.sh`
- `skills/implement/SKILL.md`
- `scripts/test-implement-fence-shape.sh`
- `scripts/implement-bootstrap.md` (sibling doc update)
- `scripts/test-implement-fence-shape.md` (sibling doc update)
- New file: `$IMPLEMENT_TMPDIR/larch-run.sh` (runtime artifact, not committed)

### Open questions
- None.
