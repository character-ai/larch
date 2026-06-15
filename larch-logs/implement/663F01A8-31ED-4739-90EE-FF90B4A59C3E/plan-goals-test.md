## Goal
Implement issue #3690: [IMPLEMENTING] sh-to-py E1: retire legacy bash ship-pr path.

## Implementation Plan
## Plan

## Approach

- Treat `approach-synthesis.txt` as `NO_SKETCHES`.
- Follow the approved outline and discussion constraints.
- Remove the legacy bash ship-pr selector entirely.
- Keep `python/ship.py` behavior out of scope except for stale references.
- Move relevant-checks orchestration into Python:
  - branch/staged/unstaged/untracked file discovery
  - existing regular-file filtering
  - `pre-commit run --files`
  - direct relevant make-target routing (full `run_direct_relevant_targets` case map from `scripts/relevant-checks.sh`, minus entries for paths retired in this issue)
  - contains-pin verification
  - `agent-lint`
  - same log markers and result envelopes
  - env scrub before calling child processes (unset `LARCH_QUIET_*` and `CLAUDE_PLUGIN_ROOT` before `pre-commit`/`make`/`agent-lint` child processes)
- Add `python/cli.py checks` CLI surface so shell wrappers and skills can call Python without importing modules from Bash. CLI emits the full `FAILURE_REASON` token enum matching `run-relevant-checks-captured.md` contract (`tmpdir-validation`, `site-validation`, `repo-root-unresolved`, `log-dir-symlink-rejected`, `redaction-failed`, etc.).
- Add `python/cli.py checks lint-fix` CLI surface emitting `LINT_FIX_STATUS`, `STDERR_TAIL_PATH`, `CODER_LOG_FILE` matching `lint-fix-loop.sh` output contract so implement SKILL.md Steps 3/6 failure-repair paths work after bash deletion.
- Delete only confirmed orphans:
  - ship-pr bash path and its direct harnesses/libs
  - relevant-checks/lint-fix-loop bash suite and harnesses
  - dead `--codex-add-dir`
- Update docs and structural pins so `git grep` finds no remaining `LARCH_SHIP_PR_IMPL` or deleted-script references outside retired-path manifest history rules.

## Files to modify/create

### UPDATED: python/checks.py

- Replace `run_relevant_checks` shell-out to `scripts/relevant-checks.sh`.
- Add native helpers for:
  - repo root resolution
  - changed-file union: `main...HEAD` or `origin/main...HEAD`, staged, unstaged, untracked
  - existing regular-file filtering
  - `pre-commit` preflight and invocation
  - `agent-lint --pedantic`
  - direct relevant make-target dispatch (port the full `run_direct_relevant_targets` case map from `scripts/relevant-checks.sh:100-494`, removing only case arms for paths retired in this issue: ship-pr.sh, lint-fix-loop.sh, relevant-checks.sh, check-contains-pins.sh, test-ship-pr-*.sh, test-relevant-checks-*.sh, test-lint-fix-loop.sh, test-check-contains-pins.sh, surface-lint-fix-stderr-tail.sh; keep all other arms verbatim)
  - contains-pin scan
  - env scrub: child processes (`pre-commit`, `make`, `agent-lint`) run with `LARCH_QUIET_*` and `CLAUDE_PLUGIN_ROOT` unset from inherited env so nested invocations target the consumer repo CLI
- Preserve these log markers:
  - `=== Running pre-commit on ... changed file(s) ===`
  - `=== Running direct relevant make target(s): ... ===`
  - `=== Running agent-lint ===`
  - `WARNING: agent-lint not found on PATH — skipping`
- Preserve current `ChecksResult` behavior:
  - bounded green-path result
  - redacted failure log under session tmpdir
  - `COVERAGE` and `PHASE` marker inference
  - fail-closed tmpdir/log validation
  - `failure_reason` field on `ChecksResult` populated from `run_relevant_checks` structural failures (`tmpdir-validation`, `site-validation`, `repo-root-unresolved`, `log-dir-symlink-rejected`, `log-alloc-failed`, `redaction-failed`)
- Add `check_contains_pins_main` as a Python port of `scripts/check-contains-pins.sh`:
  - scans `scripts/test-*.sh` and `skills/*/scripts/test-*.sh` for `contains "$VAR" "literal"` assertions
  - verifies each literal still exists in the resolved target file
  - supports `--changed-files FILE` scoping
  - emits `DEFECT: <script>:<line>: literal not found` and exits 1 when defects found
- Remove the skip-when-absent path (`skipped=True`) for the default-repo case; after bash deletion there is no script to be absent — fail closed on any internal error instead. Gate `RELEVANT_CHECKS_SKIPPED` output behind an explicit CLI `--allow-skip` flag for test-only use only.
- Keep the existing `run_lint_fix` Python implementation.
- Rename prompt text that tells fixers to make `scripts/relevant-checks.sh` pass. It should name the Python relevant-checks command or local relevant checks instead.
- Remove docstrings that describe deleted bash files as live ports where they become misleading.

### UPDATED: python/cli.py

- Add CLI entries for Python checks:
  - `checks run-relevant` — captured relevant checks, with the same stdout keys as `run-relevant-checks-captured.sh`:
    - `STATUS=fail FAILURE_REASON=<token> [REDACTED_LOG_FILE=<path>]` on failure
    - `RELEVANT_CHECKS_OK=true SITE=<site> COVERAGE=<coverage> PHASE=<phase> [WARN=...]` on success
    - `RELEVANT_CHECKS_SKIPPED=true SITE=<site>` only when `--allow-skip` is passed (never emitted on default path after bash deletion)
  - `checks lint-fix` — runs `checks.run_lint_fix`, emits `LINT_FIX_STATUS=<status>`, `STDERR_TAIL_PATH=<path>` on dispatch-failed paths (stem under `$IMPLEMENT_TMPDIR/lint-fix-loop`), and `CODER_LOG_FILE=<path>` when applicable; same contract as `lint-fix-loop.sh`
  - `checks contains-pins` — runs `check_contains_pins_main`, emits `DEFECTS=<N>` on exit

### UPDATED: python/review_and_fix.py

- Replace `_run_relevant_checks_captured` (subprocess to `run-relevant-checks-captured.sh`) with direct call to `checks.run_relevant_checks`:
  - thread session-env + repo-root discovery (resolve `CLAUDE_PROJECT_DIR` / `git rev-parse --show-toplevel`)
  - pass site `step5-review-fixes`
  - map `ChecksResult` fields to the existing dict contract (`STATUS`, `FAILURE_REASON`, `RELEVANT_CHECKS_OK`, `RELEVANT_CHECKS_SKIPPED`, `REDACTED_LOG_FILE`) via an adapter helper
- Replace `_run_lint_fix_loop` (subprocess to `lint-fix-loop.sh`) with direct call to `checks.run_lint_fix`:
  - thread `CODEX_PRESENT`/`CURSOR_PRESENT` from env or session-env
  - pass `repo_root`, `run_parent` (under implement tmpdir), `allowed_tmpdir`
  - map `FixOutcome` fields to the existing lint-fix result dict (`LINT_FIX_STATUS`, `STDERR_TAIL_PATH` on dispatch-failed paths)
- Keep `_step5_post_round_gates` behavior:
  - pass on OK or skip
  - run lint-fix loop on redacted-log failures
  - enforce attempt cap
  - return existing stall reasons
- Remove capture parsing helpers that become dead after the subprocess seam is gone.
- Extend `python/test_review_and_fix.py` to assert repo-root and presence wiring (CODEX_PRESENT/CURSOR_PRESENT forwarding).

### UPDATED: python/agents.py

- Remove `--codex-add-dir` from `agent launch-review` argument parser.
- Remove `_review_validate_codex_add_dir` function.
- Remove all call sites and references to `codex_add_dir`.
- Keep Codex `--add-dir` for the output parent so read-only sandbox writes still work.
- Remove the cursor-only rejection branch (`if args.tool == "cursor" and args.codex_add_dir`).

### UPDATED: python/config.py

- Remove `ENV_LARCH_SHIP_PR_IMPL` constant.

### UPDATED: python/migration_lint.py

- Remove the `scripts/ship-pr.sh` live-reference carve-out.
- Keep retired-path matching exclusions for `larch-logs/`, `CHANGELOG.md`, and the manifest.

### UPDATED: python/migrated-scripts.tsv

- Append each retired path with `#3690`.
- Include both `.sh` and `.md` siblings where they exist.
- Include deleted bash harnesses.
- Include `scripts/surface-lint-fix-stderr-tail.sh` (no `.md` sibling).

### UPDATED: python/test_checks.py

- Replace current stub-`scripts/relevant-checks.sh` tests with native dispatcher tests:
  - no changed files plus agent-lint present
  - zero phases when no pre-commit files and no agent-lint
  - pre-commit missing
  - not a git repo
  - changed-file pre-commit success and failure
  - direct target routing (at least one representative row per map family)
  - direct target de-dupe
  - Python lint/test tool availability warnings
  - contains-pin success/failure/scoped changed files
  - log markers, coverage, phase, redaction failure, tmpdir validation
  - failure_reason populated for structural failures
  - no RELEVANT_CHECKS_SKIPPED on default path after bash deletion
  - env-scrub: nested invocations do not inherit `CLAUDE_PLUGIN_ROOT` from plugin cache
- Keep `run_lint_fix` tests, but update prompt assertions away from `scripts/relevant-checks.sh`.
- Add `check_contains_pins_main` pytest coverage.

### UPDATED: python/test_checks_bash_parity.py

- Remove parity tests that source `scripts/ship-pr.sh` or execute `run-relevant-checks-captured.sh`.
- Keep only Python-side regression tests that still add value, or delete this file if it becomes empty.
- Move any non-bash behavioral assertions into `python/test_checks.py`.

### UPDATED: python/test_review_and_fix.py

- Update monkeypatches from `_run_relevant_checks_captured` / `_run_lint_fix_loop` to the new ChecksResult/FixOutcome adapter seams.
- Add one integration-style test proving Step 5 calls `checks.run_relevant_checks` with repo-root wiring and then `checks.run_lint_fix` with presence flags on failure.

### UPDATED: python/test_launch_review.py

- Remove `--codex-add-dir` accept/reject tests.
- Update argv rejection parametrization (remove `--codex-add-dir` entry from rejection table).
- Add or keep coverage proving Codex still passes `--add-dir <output-parent>`.

### UPDATED: python/test_config.py

- Remove the `ENV_LARCH_SHIP_PR_IMPL` assertion.

### UPDATED: python/test_migration_lint.py

- Remove tests for the `scripts/ship-pr.sh` live-reference carve-out.
- Add coverage that retired `scripts/ship-pr.sh` references are now normal stale references outside excluded paths.

### UPDATED: skills/implement/scripts/step-18-finalize.sh

- Drop the `LARCH_SHIP_PR_IMPL=bash` gate on the finalize-state restore predicate.
- Always use the Python finalize-state restore path (already present on the non-bash branch).
- Update `step-18-finalize.md` to describe the script as single-path Python restore only.

### UPDATED: skills/implement/scripts/step-8-ship.sh

- Remove the `LARCH_SHIP_PR_IMPL` branch.
- Always run `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" ship pr`.
- Keep:
  - state-key rehydration
  - Python 3.11 guard
  - JSON stalled envelope on stale Python
  - `--state-file`
  - `--no-logs-commit`
  - expected session/tmpdir args
- Remove bash-only `RESUME_PHASE` forwarding.

### UPDATED: skills/implement/scripts/step-8-ship.md

- Describe the script as the Python ship driver wrapper, not a selector.
- Remove bash resume-phase wording.

### UPDATED: skills/implement/scripts/test-step-8-ship.sh

- Remove bash-mode tests and static pins against `scripts/ship-pr.sh`.
- Keep stale-Python JSON tests.
- Add a dynamic test that the wrapper invokes `python/cli.py ship pr` with the expected argv.

### UPDATED: skills/implement/scripts/run-step-checks.sh

- Repoint the helper to `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" checks run-relevant --site "$SITE" --tmpdir "$IMPLEMENT_TMPDIR"`.
- Keep plugin-root and telemetry rehydration.

### UPDATED: skills/implement/scripts/run-step-checks.md

- Update the description to Python relevant-checks.
- Remove `run-relevant-checks-captured.sh`.

### UPDATED: skills/implement/scripts/test-implement-relevant-checks-anti-halt.sh

- Update structural pins from `run-relevant-checks-captured.sh` to `run-step-checks.sh` or the new Python command.
- Keep the anti-halt intent.

### UPDATED: skills/implement/SKILL.md

- Remove all `LARCH_SHIP_PR_IMPL` branches.
- Remove bash `ship-pr.sh` continuation rules.
- Route Step 8+ only through the Python ship wrapper.
- Update Step 3/5/6 prose: replace `${CLAUDE_PLUGIN_ROOT}/scripts/lint-fix-loop.sh --tmpdir "$IMPLEMENT_TMPDIR" --site <site> --checks-log "$REDACTED_LOG_FILE"` invocations with `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" checks lint-fix --tmpdir "$IMPLEMENT_TMPDIR" --site <site> --checks-log "$REDACTED_LOG_FILE"` and update parsing to read the same `LINT_FIX_STATUS` / `STDERR_TAIL_PATH` / `CODER_LOG_FILE` keys from the new CLI stdout.
- Replace `${CLAUDE_PLUGIN_ROOT}/scripts/surface-lint-fix-stderr-tail.sh` pipe invocations with the new CLI's native `STDERR_TAIL_PATH` key (no separate pipe step needed).
- Update relevant-checks helper wording to `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" checks run-relevant ...`.
- Keep anti-halt rules for relevant-checks helpers, but make them command-name neutral.

### UPDATED: skills/implement/references/ship-pr-exit-matrix.md

- Retire or rewrite as a Python-driver non-zero routing reference.
- Remove bash-only exit matrix text.
- Keep only Python JSON/exit-code routing that is still live.

### UPDATED: skills/implement/references/conflict-resolution.md

- Simplify cross-driver handoff prose to the single Python driver.
- Remove bash `ship-pr-rrr-phase14` re-invocation instructions.
- Keep `caller_kind=ship_pr_pre_push` conflict handling if still used by `python/ship.py`.

### UPDATED: skills/implement/references/phantom-probe.md

- Remove the bash exception before Step 8.
- Describe the single pre-ship probe path.

### UPDATED: skills/implement/references/codex-manifest-schema.md

- Remove `scripts/ship-pr.sh` as a manifest consumer.
- Keep `python/cli.py implement step2-dispatch` and `python/ship.py`.

### UPDATED: skills/implement/scripts/materialize-manifest-oos.md

- Remove `scripts/ship-pr.sh` as a caller.
- Keep Python callers.

### UPDATED: skills/review/SKILL.md

- Replace the Step 3e `run-relevant-checks-captured.sh` invocation with `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" checks run-relevant --site review-step3e --tmpdir "$REVIEW_TMPDIR"`.
- Keep continuation behavior after OK, skip, or failure.

### UPDATED: skills/review-and-fix/SKILL.md

- Replace validation prose that names `run-relevant-checks-captured.sh` with the Python CLI path.

### UPDATED: skills/shared/subskill-invocation.md

- Replace helper-specific `run-relevant-checks-captured.sh` wording with command-neutral relevant-checks helper wording.
- Remove the bash Step 8 resume example.

### UPDATED: skills/alias/SKILL.md

- Replace the stale `run-relevant-checks-captured.sh` anti-halt mention.

### UPDATED: scripts/test-implement-structure.sh

- Remove pins for `LARCH_SHIP_PR_IMPL`, bash selector branches, and `scripts/ship-pr.sh`.
- Add pins for single Python Step 8 wrapper behavior.
- Remove pins that inspect deleted `scripts/ship-pr.sh`.

### UPDATED: scripts/test-implement-step8-exit3-first-fixer.sh

- Remove bash-exit-matrix pins.
- Retarget to Python driver routing if the harness still has value, otherwise delete it in a separate plan only if confirmed orphaned.

### UPDATED: scripts/test-prompt-template-invariants.sh

- Remove the `lint-fix-loop.sh` prompt render smoke.
- Add equivalent `checks.py` prompt composition coverage in pytest if not already covered.

### UPDATED: scripts/test-compose-pr-summary.sh

- Remove stale guidance text that asks contributors to wire into `ship-pr.sh`.

### UPDATED: scripts/test-lib-external-launcher-common.sh

- Remove `lint-fix-loop.sh` from the Codex auth inventory pin.
- Add the Python checks lint-fix path if the auth inventory still covers it.

### UPDATED: .claude/rules/external-tool-launcher-parity.md

- Remove `scripts/lint-fix-loop.sh` from paths and prose.
- Replace with `python/checks.py` or the new CLI path if needed.
- Remove the `--codex-add-dir` comparison.

### UPDATED: .claude/rules/gh-body-file.md

- Remove `scripts/ship-pr.sh` from the path list.

### UPDATED: Makefile

- Remove `.PHONY` entries and target bodies for deleted harnesses:
  - `test-relevant-checks`
  - `test-relevant-checks-byte-budget`
  - `test-relevant-checks-validation`
  - `test-relevant-checks-helper-failure`
  - `test-review-relevant-checks-helper`
  - `test-lint-fix-loop`
  - `test-check-contains-pins`
  - `test-ship-pr-rebase`
  - `test-ship-pr-oos-pr-prep`
- Remove them from shard targets (shards 10, 12, 14, 15, 18, 20).
- Replace coverage with existing or new pytest targets, mainly `py-test`.

### UPDATED: AGENTS.md

- Remove `LARCH_SHIP_PR_IMPL=bash`.
- Replace `bash scripts/relevant-checks.sh` guidance with `make lint`, plus `make py-lint` and `make py-test` when Python files change.

### UPDATED: README.md

- Remove the `scripts/relevant-checks.sh` catalog row.
- Remove the consumer-contract link from the setup summary.
- Point validation guidance at Python checks or Make targets.

### UPDATED: docs/installation-and-setup.md

- Remove the relevant-checks consumer-contract section.
- Remove the legacy bash ship-driver escape hatch.
- Keep Python 3.11 prerequisite wording for `/implement`.

### UPDATED: docs/configuration-and-permissions.md

- Delete the `LARCH_SHIP_PR_IMPL` env-var section.
- Remove bash driver conflict/handoff prose.
- Remove `lint-fix-loop.sh` from Codex auth inventory.
- Update any path-specific security descriptions now owned by Python.

### UPDATED: docs/linting.md

- Replace the `scripts/relevant-checks.sh` section with Python relevant-checks behavior.
- Remove deleted harness rows.
- Update CI/local lint descriptions that say `scripts/relevant-checks.sh` runs `lint-bash32`.
- Keep `make lint`, `py-lint`, and `py-test` guidance.

### UPDATED: docs/skills.md

- Remove the `scripts/relevant-checks.sh` skill/catalog entry.

### UPDATED: docs/workflow-lifecycle.md

- Remove dual-driver wording.
- Describe `python/cli.py ship pr` as the only Step 8+ driver.

### UPDATED: docs/external-reviewers.md

- Remove `lint-fix-loop.sh` from Codex auth scope.
- Add Python checks lint-fix if the inventory still needs that path.

### UPDATED: docs/run-logs.md

- Remove bash opt-in refresh references.
- Keep Python `run_logs.flush_logs_pre` behavior.

### UPDATED: docs/python-migration.md

- Remove the `scripts/ship-pr.sh` retention carve-out.
- Add a note that E1 retired the bash path and appended retired paths to `python/migrated-scripts.tsv`.

### UPDATED: docs/vendor-agent-diagnostics-audit.md

- Remove or retire the `scripts/lint-fix-loop.sh` row.

### UPDATED: python/README.md

- Remove the legacy ship-pr path.
- Remove the old "intentional fifth wiring change" note that references `scripts/ship-pr.sh`.
- Add the Python checks CLI entry if added.

### UPDATED: SECURITY.md

- Update the ship-pr driver security section to single Python driver.
- Update relevant-checks captured-log section to Python implementation.
- Remove `scripts/ship-pr.sh` and `lint-fix-loop.sh` as live security surfaces.
- Keep security claims about mode-700/mode-600 logs, redacted failure logs, Codex env-key behavior, and fail-closed redaction.

### REWRITTEN: scripts/ship-pr.sh

- Delete the file.

### REWRITTEN: scripts/ship-pr.md

- Delete the file.

### REWRITTEN: scripts/lib-finalize-state-keys.sh

- Delete the file.

### REWRITTEN: scripts/lib-finalize-state-keys.md

- Delete the file.

### REWRITTEN: scripts/test-ship-pr-rebase.sh

- Delete the file.

### REWRITTEN: scripts/test-ship-pr-rebase.md

- Delete the file.

### REWRITTEN: scripts/test-ship-pr-oos-pr-prep.sh

- Delete the file.

### REWRITTEN: scripts/relevant-checks.sh

- Delete the file.

### REWRITTEN: scripts/relevant-checks.md

- Delete the file.

### REWRITTEN: scripts/run-relevant-checks-captured.sh

- Delete the file after all callers use Python.

### REWRITTEN: scripts/run-relevant-checks-captured.md

- Delete the file.

### REWRITTEN: scripts/lint-fix-loop.sh

- Delete the file.

### REWRITTEN: scripts/lint-fix-loop.md

- Delete the file.

### REWRITTEN: scripts/surface-lint-fix-stderr-tail.sh

- Delete the file.

### REWRITTEN: scripts/check-contains-pins.sh

- Delete the file after porting to Python.

### REWRITTEN: scripts/check-contains-pins.md

- Delete the file.

### REWRITTEN: scripts/test-relevant-checks.sh

- Delete the file.

### REWRITTEN: scripts/test-relevant-checks.md

- Delete the file.

### REWRITTEN: scripts/test-relevant-checks-byte-budget.sh

- Delete the file.

### REWRITTEN: scripts/test-relevant-checks-byte-budget.md

- Delete the file.

### REWRITTEN: scripts/test-relevant-checks-validation.sh

- Delete the file.

### REWRITTEN: scripts/test-relevant-checks-validation.md

- Delete the file.

### REWRITTEN: scripts/test-relevant-checks-helper-failure.sh

- Delete the file.

### REWRITTEN: scripts/test-relevant-checks-helper-failure.md

- Delete the file.

### REWRITTEN: scripts/test-review-relevant-checks-helper.sh

- Delete the file.

### REWRITTEN: scripts/test-review-relevant-checks-helper.md

- Delete the file.

### REWRITTEN: scripts/test-lint-fix-loop.sh

- Delete the file.

### REWRITTEN: scripts/test-lint-fix-loop.md

- Delete the file.

### REWRITTEN: scripts/test-check-contains-pins.sh

- Delete the file after pytest coverage exists.

### REWRITTEN: scripts/test-check-contains-pins.md

- Delete the file.

## Edge cases

- **Deleted-only branches:** still run agent-lint and direct checks where applicable.
- **No regular files for pre-commit:** do not silently pass; fail with no-phase semantics unless agent-lint runs.
- **Missing tools:** preserve current warnings for optional Python lint/test direct targets. Keep hard failure for missing `pre-commit` if pre-commit would run.
- **Dangling symlinks:** keep fail-closed tmpdir and log handling.
- **Large logs:** keep streaming marker scan and bounded redaction behavior.
- **Prompt text drift:** update external-fixer prompts so they do not ask agents to run deleted scripts.
- **Sandbox grants:** removing `--codex-add-dir` must not remove the required output-parent `--add-dir` for Codex review output.

## Failure modes

- **Stale caller remains:** deleted helper causes runtime failure. Mitigate with `git grep` for every retired path before deletion.
- **Coverage drop:** deleting bash harnesses can hide behavior regressions. Mitigate by moving behavioral cases into pytest before deleting harness targets.
- **Envelope mismatch:** skills expect old KEY output. Mitigate with CLI tests for exact stdout grammar.
- **Migration lint noise:** retired manifest catches historical docs. Mitigate by removing stale live refs and keeping excluded-path rules intact.
- **Security doc drift:** log redaction or Codex auth claims may become inaccurate. Mitigate by updating `SECURITY.md` in the same change.

## Testing strategy

- Run focused Python tests:
  - `python3 -m pytest python/test_checks.py`
  - `python3 -m pytest python/test_review_and_fix.py`
  - `python3 -m pytest python/test_launch_review.py`
  - `python3 -m pytest python/test_migration_lint.py`
  - `python3 -m pytest python/test_config.py`
- Run structural harnesses still present after Makefile update:
  - `make test-implement-structure`
  - `make test-implement-relevant-checks-anti-halt`
  - `make test-lib-external-launcher-common`
  - `make test-prompt-template-invariants`
- Run migration/stale-ref checks:
  - `python3 python/cli.py lint retired-scripts`
  - `git grep -n 'LARCH_SHIP_PR_IMPL\|scripts/ship-pr.sh\|run-relevant-checks-captured.sh\|scripts/relevant-checks.sh\|lint-fix-loop.sh\|check-contains-pins.sh\|--codex-add-dir' -- . ':!larch-logs/**'`
- Run full required checks:
  - `make lint`
  - `make py-lint`
  - `make py-test`
- For final smoke, run one `/implement` Step 8 wrapper test path with a stubbed `python3 python/cli.py ship pr` command if full ship smoke is not safe locally.

## Acceptance checks

- `scripts/ship-pr.sh` is gone.
- `LARCH_SHIP_PR_IMPL` has no live references.
- `scripts/relevant-checks.sh`, `scripts/run-relevant-checks-captured.sh`, `scripts/lint-fix-loop.sh`, `scripts/check-contains-pins.sh`, and listed harnesses are gone.
- `python/checks.py` no longer shells out to `scripts/relevant-checks.sh`.
- `review_and_fix.py` no longer shells out to deleted helpers.
- `python/agents.py` no longer accepts `--codex-add-dir`.
- `python/migrated-scripts.tsv` includes all retired paths with `#3690`.
- `make lint`, `make py-lint`, and `make py-test` pass.

## Acceptance

Gate C approved by operator.

diff_lines: 9750

## Test plan
(no test plan section in plan-file)
