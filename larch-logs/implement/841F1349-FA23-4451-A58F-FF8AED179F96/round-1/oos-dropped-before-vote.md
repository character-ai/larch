### OOS_1: [OUT_OF_SCOPE] `lint-flat-tests` omitted from repo-wide `make lint` (deliberate plan choice)
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: nit
- **Concern**: `lint-flat-tests` is wired into `py-lint-checks-fast` but not the repo-wide `lint:` aggregate (which already runs `lint-tier1a-size`, `lint-bg-wait-coverage`, etc.). A developer running only `make lint` can add a non-exempt `python/test_*.py` and still pass locally while CI (`py-lint-checks-fast`) fails. Acceptance targets CI via `py-lint-checks-fast`, not `make lint`.

### OOS_2: [OUT_OF_SCOPE] run-relevant fallback not restored for relocated tier1a and skill-description-length tests (plan-scoped)
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: important
- **Concern**: After the move, edits confined to `python/tests/lint/test_lint_tier1a.py` or `test_lint_skill_description_length.py` no longer match the `python/*.py` fallback (`wants_py_lint` / `wants_py_test`), so `/implement` `checks run-relevant` will not enqueue broad `py-test`/`py-lint` for test-only changes to those modules (bg-wait was fixed explicitly). Plan scoped `checks_run_relevant` updates to bg-wait only; feature acceptance does not require restoring that fallback.

### OOS_3: [OUT_OF_SCOPE] gitignored untracked flat tests invisible to ratchet
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: `git_ls_files_z` in `python/larch/lint/lint_common.py` uses `--exclude-standard`, so a flat `python/test_*.py` that is both untracked and gitignored is invisible to the ratchet until tracked. Consistent with other git-backed file linters; evasion requires an explicit gitignore entry and does not affect committed/tracked violations CI enforces.

### OOS_4: [OUT_OF_SCOPE] no regression test for bg-wait `checks_run_relevant` direct-target path
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: No regression test covers the bg-wait `checks_run_relevant` path. A future revert of `python/tests/lint/test_lint_bg_wait_coverage.py` in the direct-target tuple would not be caught by unit tests.

