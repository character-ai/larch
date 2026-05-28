## Proposed Design Outline

### Goals
- Source `scripts/lib-design-tmpdir.sh` and call `larch_design_tmpdir_validate "$DESIGN_TMPDIR"` in every remaining production `--design-tmpdir` consumer (17 scripts) so misconfigured orchestrators cannot read/write outside the allowlist.
- Follow the canonical pattern established by `scripts/dispatch-plan-voters.sh` and `skills/design/scripts/tally-plan-review.sh` exactly: source line near other library sources, validate call immediately after the required-arg presence check.
- Update the sibling `.md` for each modified script (16 files) to document the new validation step.

### Non-goals
- Do not modify `scripts/lib-design-tmpdir.sh` (validator behavior unchanged).
- Do not modify the 2 already-wired scripts.
- Do not wire the 3 test harnesses (`scripts/test-revise-plan-with-waterfall.sh`, `skills/design/scripts/test-design-pause-resume.sh`, `skills/design/scripts/test-plan-review-loop.sh`).
- Do not create `skills/design/scripts/emit-design-plan-preview.md` (pre-existing sibling-rule gap, separate concern).
- No refactoring of unrelated code in target scripts.

### Approach sketch
- For each of the 17 scripts: add `source` of `lib-design-tmpdir.sh` near existing library sources (path varies: `$SCRIPT_DIR/lib-design-tmpdir.sh` for `scripts/`, `$SCRIPT_DIR/../../../scripts/lib-design-tmpdir.sh` or `$PLUGIN_ROOT/scripts/lib-design-tmpdir.sh` for `skills/design/scripts/`), then `larch_design_tmpdir_validate "$DESIGN_TMPDIR" || exit $?` after argv required-arg checks and before any read/write into `$DESIGN_TMPDIR`.
- Per-script adaptations:
  - `scripts/design-pause-load.sh`: substitute `|| emit_load_fail "tmpdir-invalid"` for `|| exit $?` to preserve the script's `LOAD_OK=false ERROR=…` KV contract.
  - `skills/design/scripts/decompose-file-issues.sh`: insert the validate call in all three subcommand argv handlers (`prepare`, `annotate`, `close-original`).
  - `skills/design/scripts/emit-design-plan-preview.sh`: add a `SCRIPT_DIR=` definition before sourcing the library (it currently has none).
- After all .sh edits, update each sibling .md with a one-line note that the script now calls `larch_design_tmpdir_validate` after argv parsing.

### Surfaces in scope
- `scripts/`: `design-log-publish.sh`, `design-pause-load.sh`, `design-pause-save.sh`, `write-design-current-env.sh` (+ siblings).
- `skills/design/scripts/`: `check-plan-size.sh`, `decompose-aggregator.sh`, `decompose-file-issues.sh`, `decompose-panel-dispatch.sh`, `design-driver.sh`, `dispatch-plan-review-panel.sh`, `emit-design-plan-preview.sh`, `emit-plan.sh`, `file-design-oos.sh`, `finalize-plan.sh`, `plan-review-loop.sh`, `render-plan-review-prompt.sh`, `revise-plan-with-waterfall.sh` (+ siblings, except `emit-design-plan-preview.md`).

### Open questions
- None.
