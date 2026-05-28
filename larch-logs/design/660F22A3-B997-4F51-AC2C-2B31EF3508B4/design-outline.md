## Proposed Design Outline

### Goals
- Make `lib-voter-coverage.sh` plan-review-specificity explicit at the symbol level so a future code-review caller fails loudly instead of silently corrupting KV stdout.
- Validate `--design-tmpdir` paths uniformly across all consumers via a shared helper that canonicalizes (realpath) and enforces a documented session-tmpdir prefix.
- Make the `emit_kv` FD-3 contract robust against accidental embedded newlines by rejecting them at the helper boundary with `larch_err`.

### Non-goals
- Refactoring `voter_coverage_emit_status_block` to be truly generic (KV reordering + paths-file restructuring). Deferred to a future explicit consolidation effort.
- Adding backward-compat shims for the renamed function (no deprecated stub; clean rename).
- Sanitizing `--implement-tmpdir`, `--review-tmpdir`, `--research-tmpdir` callers in this PR (the shared helper may be parameterizable, but the OOS-named scope is `--design-tmpdir`).
- Escaping (rather than rejecting) embedded newlines in `emit_kv` values. The contract becomes "values must be single-line"; callers are responsible.

### Approach sketch
- Rename `scripts/lib-voter-coverage.sh` → `scripts/lib-plan-voter-coverage.sh` and rename the functions `voter_coverage_*` → `voter_coverage_plan_*` (or a clearer `plan_voter_coverage_*` form). Update the one production sourcer (`scripts/dispatch-plan-voters.sh`) and the sibling `.md`. Regression harness `test-dispatch-plan-voters.sh` continues to validate dispatcher stdout, unchanged.
- Add a new `scripts/lib-design-tmpdir.sh` with `larch_design_tmpdir_validate <dir>` that resolves `--design-tmpdir` via realpath and enforces a prefix allowlist of `$HOME/.cache/larch/sessions/`, `$TMPDIR`, `/tmp/`. Wire a one-line guard at the top of each `--design-tmpdir` consumer (`dispatch-plan-voters.sh`, `tally-plan-review.sh`, plus the broader audit list). New harness `scripts/test-lib-design-tmpdir.sh`.
- Extend `emit_kv` in `scripts/lib-quiet.sh` to reject values containing `\n` or `\r` via a single-pass `case` test. On detection, `larch_err` with a clear message naming the offending key, then return 2. Add regression coverage in `scripts/test-lib-quiet.sh` (create if absent).
- Update every `.md` sibling per `.claude/rules/script-md-siblings.md`: `lib-voter-coverage.md` (or its successor name), `dispatch-plan-voters.md`, `tally-plan-review.md`, `lib-quiet.md`, plus a new `lib-design-tmpdir.md`.

### Surfaces in scope
- `scripts/lib-voter-coverage.sh` (renamed) + `scripts/lib-voter-coverage.md` (renamed).
- `scripts/dispatch-plan-voters.sh` + `scripts/dispatch-plan-voters.md` — update sourcer line, add validator guard, update KV-emit caller.
- `skills/design/scripts/tally-plan-review.sh` + sibling `.md` — add validator guard.
- `scripts/lib-quiet.sh` + `scripts/lib-quiet.md` — `emit_kv` reject embedded newlines.
- NEW: `scripts/lib-design-tmpdir.sh` + `scripts/lib-design-tmpdir.md` + `scripts/test-lib-design-tmpdir.sh` + `scripts/test-lib-design-tmpdir.md`.
- All other `--design-tmpdir` consumers (~20 additional scripts under `scripts/` and `skills/design/scripts/`) — add the one-line guard.
- Harness additions: regression coverage for `emit_kv` reject (`scripts/test-lib-quiet.sh` create-if-absent) and the new tmpdir validator.

### Open questions
- None.
