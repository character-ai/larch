## Goal
Implement issue #5869: [IMPLEMENTING] [py-code-quality] [pkg-payoff] Enforce flat-test mirror ratchet.

## Implementation Plan
## Plan

## Approach

- Move only the three flat lint test modules into `python/tests/lint/`.
- Keep `python/test_support.py` at root, per discussion round 1.
- Add `larch.lint.lint_flat_tests` to detect non-exempt `python/test_*.py` files at root.
- Register the CLI as `python3 python/cli.py lint flat-tests`.
- Wire the lint into `py-lint-checks-fast` so the Python lint CI path enforces it.
- Update only direct Makefile harness paths. Do not add pytest wrappers to `test-harnesses-*`.
- Update `checks_run_relevant.py` so `/implement` `checks run-relevant` still triggers `test-lint-bg-wait-coverage` when the relocated pytest module changes.
- Do not edit `python/shard-assignments.json`; the moved tests had no shard entries.

## Files to modify/create

### NEW: python/tests/lint/test_lint_tier1a.py

Create by moving `python/test_lint_tier1a.py` to this path.

Required content changes:
- Preserve existing assertions.
- Update `test_live_repo_files_pass` repo root from `Path(__file__).resolve().parents[1]` to `Path(__file__).resolve().parents[3]` so `lint_tier1a.check_root` targets the repo root from `python/tests/lint/` (same depth as other mirrored lint tests such as `test_lint_skill_closure_growth.py`).
- Delete the old root file as part of the move.

### NEW: python/tests/lint/test_lint_bg_wait_coverage.py

Create by moving `python/test_lint_bg_wait_coverage.py` to this path.

- Preserve existing assertions and helpers.

### NEW: python/tests/lint/test_lint_skill_description_length.py

Create by moving `python/test_lint_skill_description_length.py` to this path.


### NEW: python/larch/lint/lint_flat_tests.py

Add a small repo-root lint module.

Required behavior:
- Accept the shared `--root` argument using `lint_common.run_file_lint` or the same exit-code convention.
- Scan only `python/test_*.py` at root.
- Include tracked and untracked files when the root is a git worktree.
- Use an explicit exemption set containing only `test_support.py`.
- Emit exit `0` when only exempt flat helper files exist.
- Emit exit `1` with clear path diagnostics for any other flat root `test_*.py`.
- Emit exit `2` for invalid roots or enumeration errors.
- Keep exemption wording in code explicit, for example `EXEMPT_ROOT_TESTS = frozenset({"test_support.py"})`, with a short reason that it is a shared pytest helper, not a test module.

### NEW: python/tests/lint/test_lint_flat_tests.py

Add focused unit tests for the new lint.

Cover:
- Clean tree with no root tests.
- `python/test_support.py` is accepted as the only exemption.
- A new `python/test_example.py` fails with exit `1` and a diagnostic naming the path.
- Nested mirrored tests such as `python/tests/lint/test_example.py` do not fail.
- Invalid `--root` exits `2`.
- If practical, verify untracked files are included through the non-git fallback or by writing fixtures under a temp root.

### UPDATED: python/larch/cli.py

Register the new lint entry.

Required entry:
- `("lint", "flat-tests"): ("larch.lint.lint_flat_tests", "main")`

Keep the registry lazy-import pattern unchanged.

### UPDATED: python/larch/implement/checks_run_relevant.py

Repoint the existing bg-wait direct-target rule to the relocated pytest path.

Required change:
- In the bg-wait rule tuple (around lines 449–463), replace `python/test_lint_bg_wait_coverage.py` with `python/tests/lint/test_lint_bg_wait_coverage.py`.
- Leave the linter path (`python/larch/lint/lint_bg_wait_coverage.py`), `Makefile`, `.pre-commit-config.yaml`, and harness targets (`test-lint-bg-wait-coverage`, `test-hook-bg-poll-guard`, `test-hook-no-progress-guard`) unchanged.
- Do not add new run-relevant rows for `lint flat-tests` in this change; `py-lint-checks-fast` already enforces the ratchet in CI.

### UPDATED: Makefile

Make the lint enforced and fix stale paths.

Required changes:
- Add `lint-flat-tests` and `test-lint-flat-tests` to the relevant `.PHONY` lists.
- Add `$(PYTHON) python/cli.py lint flat-tests` to `py-lint-checks-fast`.
- Add a direct `lint-flat-tests` target that runs the same CLI.
- Add a direct `test-lint-flat-tests` target that runs `python/tests/lint/test_lint_flat_tests.py`.
- Update:
  - `test-lint-tier1a-size` to use `python/tests/lint/test_lint_tier1a.py`.
  - `test-lint-bg-wait-coverage` to use `python/tests/lint/test_lint_bg_wait_coverage.py`.
  - `test-lint-skill-description-length` to use `python/tests/lint/test_lint_skill_description_length.py`.
- Do not add the new pytest wrapper to `test-harnesses-*`.

### MAY_UPDATE: python/README.md

Only update if the existing prose becomes misleading after the moves.

Minimal acceptable edit:
- State that unit tests live under `python/tests/` mirroring package layout.
- State that `python/test_support.py` intentionally remains at root as a shared pytest helper and is exempted by `lint flat-tests`.

## Edge cases

- `test_support.py` must not be treated as a pytest test by the new lint.
- The lint must not flag mirrored tests under `python/tests/**`.
- The lint should see untracked root tests, so agents cannot add a new flat file and pass locally before staging.
- The moved `test_lint_tier1a.py` must use `parents[3]` for repo root; `parents[1]` resolves to `python/tests`, not the repo root.
- After the bg-wait test move, edits confined to `python/tests/lint/test_lint_bg_wait_coverage.py` must still match the `checks run-relevant` bg-wait rule.
- Root symlinks are rare; handle them consistently with existing file-scanning lints or document the choice in code.

## Failure modes

- If the new lint is only registered but not wired into `py-lint-checks-fast`, CI may not enforce the ratchet.
- If Makefile paths stay flat, direct harness targets will fail after the move.
- If `checks_run_relevant.py` keeps the flat bg-wait pytest path, `/implement` can skip `test-lint-bg-wait-coverage` while CI still passes.
- If the exemption set grows beyond `test_support.py`, the ratchet loses value.
- If the move changes imports or repo-root resolution, `make py-test` may fail even though targeted lint tests pass.

## Testing strategy

Run targeted checks first:
- `python3 -m pytest python/tests/lint/test_lint_flat_tests.py -q`
- `python3 -m pytest python/tests/lint/test_lint_tier1a.py python/tests/lint/test_lint_bg_wait_coverage.py python/tests/lint/test_lint_skill_description_length.py -q`
- `python3 python/cli.py lint flat-tests`
- `make test-lint-flat-tests`
- `make test-lint-tier1a-size`
- `make test-lint-bg-wait-coverage`
- `make test-lint-skill-description-length`

Then run acceptance checks:
- `make py-test`
- `make py-lint-checks-fast`

Optional focused verification for FINDING_1:
- Confirm `python3 python/cli.py checks run-relevant` includes `test-lint-bg-wait-coverage` when only `python/tests/lint/test_lint_bg_wait_coverage.py` changes (existing `test_checks.py` coverage or a one-off porcelain probe).

Optional negative check:
- Temporarily create an untracked `python/test_flat_fixture.py`, run `python3 python/cli.py lint flat-tests`, confirm exit `1`, then remove it before final checks.

## Acceptance

Run targeted checks first:
- `python3 -m pytest python/tests/lint/test_lint_flat_tests.py -q`
- `python3 -m pytest python/tests/lint/test_lint_tier1a.py python/tests/lint/test_lint_bg_wait_coverage.py python/tests/lint/test_lint_skill_description_length.py -q`
- `python3 python/cli.py lint flat-tests`
- `make test-lint-flat-tests`
- `make test-lint-tier1a-size`
- `make test-lint-bg-wait-coverage`
- `make test-lint-skill-description-length`

Then run acceptance checks:
- `make py-test`
- `make py-lint-checks-fast`

Optional focused verification for FINDING_1:
- Confirm `python3 python/cli.py checks run-relevant` includes `test-lint-bg-wait-coverage` when only `python/tests/lint/test_lint_bg_wait_coverage.py` changes (existing `test_checks.py` coverage or a one-off porcelain probe).

Optional negative check:
- Temporarily create an untracked `python/test_flat_fixture.py`, run `python3 python/cli.py lint flat-tests`, confirm exit `1`, then remove it before final checks.

diff_added: 175
diff_deleted: 4
mechanical_churn: false
diff_lines: 215

## Test plan
(no test plan section in plan-file)
