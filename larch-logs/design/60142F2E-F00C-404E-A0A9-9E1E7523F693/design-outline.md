## Proposed Design Outline

### Goals
- Extract the inline Python dedup heredoc out of `_run_post_apply_pipeline` into a standalone helper script, killing the awk-extraction coupling.
- Document the intentional fence-boundary divergence between `parse-plan-commands.awk` and the dedup logic.
- Add a full `run_loop` integration test for the `LOOP_REASON=dedup-python-failed` caller wiring.

### Non-goals
- No dedup behavior change — pure refactor, byte-identical output.
- Do NOT unify the two fence models (document only).
- No change to the loop's terminal-status contract or to other parsers.

### Approach sketch
- New `skills/design/scripts/dedup-plan-lines.py` holds the verbatim Python; `_run_post_apply_pipeline` calls it through a PLUGIN_ROOT-relative path with a test-overridable `DEDUP_PLAN_LINES_PY` env var (mirrors the `DESIGN_DRIVER_SH` wiring pattern).
- Add sibling `dedup-plan-lines.md` (script-md-siblings rule).
- Update the four `awk`-extraction dedup tests in `test-plan-review-loop.sh` to export the new script-path var.
- Document the fence divergence in the new `.md` and a note in `parse-plan-commands.md`.
- Add a `run_loop` integration test asserting `LOOP_STATUS=emit-plan-failed` + surfaced `LOOP_REASON=dedup-python-failed`.

### Surfaces in scope
- `skills/design/scripts/plan-review-loop.sh`
- `skills/design/scripts/dedup-plan-lines.py` + `dedup-plan-lines.md` (new)
- `skills/design/scripts/test-plan-review-loop.sh`
- `skills/design/scripts/parse-plan-commands.md` (doc note)

### Open questions
- None.
