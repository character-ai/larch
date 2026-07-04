## Plan

Assumptions:
- `approach-synthesis.txt` is `NO_SKETCHES`, so this plan comes from direct repo inspection.
- Round 1 resolved that writer-parity lint coverage is in scope.
- The approved outline limits scope to the listed writer, sibling docs, lint, lint tests, CLI registry, and Makefile wiring.

Approach:
1. Align the Step 3 shell marker writer with the sibling writers.
   - In the `SITE=step3` block, read `CLONE_PATH` from `$IMPLEMENT_TMPDIR/.larch-keepalive` only when it is a regular non-symlink file.
   - Use the same `awk -F=` pattern as `step-5-review.sh`.
   - Extend the `.bg-wait-active` `printf` to include `CLONE_PATH=%s\n`.
   - Keep marker writes fail-open with `|| true`.
2. Document the marker field.
   - Update the wrapper contract to say the Step 3 marker copies `CLONE_PATH` from `.larch-keepalive` when available.
3. Add a writer-parity lint.
   - Create a small Python lint under `python/larch/lint/`.
   - Enumerate known `.bg-wait-active` writer files:
     - `skills/design/scripts/design-step3-review.sh`
     - `skills/design/scripts/design-step3b-tail.sh`
     - `skills/implement/scripts/run-step-checks.sh`
     - `skills/implement/scripts/step-5-review.sh`
     - `skills/implement/scripts/step-6-entry.sh`
     - `skills/implement/scripts/step-8-ship.sh`
     - `python/larch/design/design_core.py`
     - `python/larch/implement/dispatch_commit_route.py`
     - `python/larch/implement/step_7a.py`
   - For each file, require marker-writer evidence and a local `CLONE_PATH=` emission.
   - Treat a missing inventory file as a lint failure with an actionable message, not as success.
   - Keep the lint static and deterministic. Do not parse runtime tempdirs.
4. Register and wire the lint.
   - Add `("lint", "bg-wait-writer-parity")` to the CLI registry.
   - Add Makefile `lint-bg-wait-writer-parity` and `test-lint-bg-wait-writer-parity`.
   - Add the lint target to the main `lint:` dependency list near `lint-bg-wait-coverage`.
5. Add targeted tests.
   - Cover clean current-style writer inventory.
   - Cover a writer that writes `.bg-wait-active` but lacks `CLONE_PATH=`.
   - Cover missing inventory path diagnostics.
   - Cover that non-writer files or cleanup-only marker references do not define the parity set.

Files to modify/create:

### UPDATED: skills/implement/scripts/run-step-checks.sh
- Add `_step3_clone_path=""` before the marker `printf`.
- Read from `$IMPLEMENT_TMPDIR/.larch-keepalive` only if it exists and is not a symlink.
- Append `CLONE_PATH=%s\n` to the marker format.
- Pass `"$_step3_clone_path"` as the final `printf` argument.
- Preserve existing `PID`, `CLAUDE_PID`, `START_EPOCH`, `STEP`, and `TIMEOUT_S` values.

### UPDATED: skills/implement/scripts/run-step-checks.md
- Update the Step 3 marker invariant to include the `CLONE_PATH` field.
- State that the field is copied from sibling `.larch-keepalive` when available.
- Keep the fail-open wording.

### NEW: python/larch/lint/lint_bg_wait_writer_parity.py
- Implement `main(argv: list[str] | None = None) -> int`.
- Use the shared `--root` parsing style from `lint_common`.
- Define a frozen writer spec dataclass with `path` and a short `label`.
- Read each listed writer file with UTF-8 replacement or normal UTF-8, matching nearby lint style.
- Report violations to stderr as `lint-bg-wait-writer-parity: <path>: <reason>`.
- Fail with exit 1 for missing `CLONE_PATH=` or missing writer evidence.
- Return exit 2 for invalid root or unreadable expected files only if that matches existing lint conventions used by the chosen helper.

### NEW: python/tests/lint/test_lint_bg_wait_writer_parity.py
- Add pytest coverage for accept and reject cases.
- Build synthetic temp roots with the expected inventory paths, or test a pure helper with synthetic `WriterSpec` entries.
- Assert diagnostics name the offending file.
- Include a reject fixture that mirrors the current `run-step-checks.sh` omission: `.bg-wait-active` marker write, no `CLONE_PATH=`.
- Include an accept fixture with `CLONE_PATH=%s\n` or `CLONE_PATH={...}` depending on file type.

### UPDATED: python/larch/cli.py
- Register `("lint", "bg-wait-writer-parity")` to dispatch to the new lint module.

### UPDATED: Makefile
- Add `.PHONY` entries for `lint-bg-wait-writer-parity` and `test-lint-bg-wait-writer-parity`.
- Add `lint-bg-wait-writer-parity` to the main `lint:` dependency list.
- Add:
  - `lint-bg-wait-writer-parity: python3 python/cli.py lint bg-wait-writer-parity`
  - `test-lint-bg-wait-writer-parity: python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/tests/lint/test_lint_bg_wait_writer_parity.py -q`

Edge cases:
- Missing or unreadable `.larch-keepalive` must still produce a marker with an empty `CLONE_PATH=` field.
- Symlinked `.larch-keepalive` must be ignored, matching sibling writers.
- Marker write failure must not abort Step 3 checks.
- The lint must not treat hook consumers, docs, tests, or cleanup-only `.bg-wait-active` references as writer sites.
- If a writer is moved or ported to Python, the lint inventory should fail until the implementer updates it.

Failure modes:
- A too-broad grep lint may flag hook scripts and tests. Avoid this with an explicit writer inventory.
- A too-weak lint that only searches repo-wide `CLONE_PATH=` could miss a future omitted writer. Check each writer file independently.
- A shell quoting mistake in the new `printf` could shift marker fields. Keep the sibling writer shape and run shell syntax checks.
- Adding the lint only to tests would not prevent drift. Wire it into `make lint`.

Testing strategy:
- `bash -n skills/implement/scripts/run-step-checks.sh`
- `python3 python/cli.py lint bg-wait-writer-parity`
- `python3 -m pytest python/tests/lint/test_lint_bg_wait_writer_parity.py -q`
- `make lint-bg-wait-writer-parity`
- `make test-lint-bg-wait-writer-parity`
- For changed Python files, run targeted ruff, pyright, and pylint on the new lint and test modules if the local environment has those tools.

Non-goals:
- Do not change hook fallback behavior.
- Do not add missing-keepalive diagnostics.
- Do not touch other marker writers except through lint inventory coverage.
- Do not change `/implement` Step 3 orchestration or active `checks-commit-route` behavior.

confidence: high

## Acceptance

See Testing strategy in plan.

review_status: complete
rounds_completed: 1
difficulty: MODERATE
mechanical_churn: false
diff_lines: 240
