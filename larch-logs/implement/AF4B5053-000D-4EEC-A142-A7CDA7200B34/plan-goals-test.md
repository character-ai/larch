## Goal
Implement issue #6516: [IMPLEMENTING] Remove the spurious-task-notification defense stack once bgjob waits land.

## Implementation Plan
## Plan

## Scope notes

- `approach-synthesis.txt` is `NO_SKETCHES`; draft from direct repo inspection.
- Round 1 resolves the only material fork: repoint Section E consumers to bgjob result envs and delete sentinels where possible. Keep only route data that cannot be removed without changing non-guard behavior.
- Do not change bgjob start, wait, registry, daemon lifecycle, timeout, orphan, or result-env semantics.
- Fresh-launch bgjob result-env and merge-env hygiene is distinct from guard-era sentinel cleanup. Keep the former everywhere a new Step 3 (or equivalent) launch must not inherit stale `bgjob/*.result.env` or merge env state.

## Approach

1. Remove the obsolete guard hooks.
   - Delete `hook-bg-poll-guard` and `hook-no-progress-guard` scripts and docs.
   - Remove their `hooks/hooks.json` entries.
   - Keep `hook-deny-run-in-background.sh`, `block-submodule-edit.sh`, SessionStart hooks, `hook-stop-fail-close.sh`, and `hook-anti-read-poll.sh`.

2. Split `hook-anti-read-poll.sh`.
   - Delete the `tasks/*.output` branch, bg-wait marker discovery, probe-clamp coupling, and legacy env knobs.
   - Keep only the generic repeated identical `Read` warning.
   - Trim its harness to generic repeated-Read cases.

3. Remove marker and sidecar code.
   - Delete `python/larch/implement/bg_wait.py`.
   - Remove Python imports and calls that write or clear `.bg-wait-active`, no-progress sidecars, and bg-poll counters.
   - Keep or move `_read_keepalive_clone_path` only if a non-guard caller still needs it. Prefer a local helper near the caller rather than keeping `bg_wait.py`.

4. Strip marker blocks from migrated wrappers.
   - Remove `_bg_wait_marker_start` functions, marker cleanup traps, no-progress resets, and bg-poll counter resets from design and implement wrappers.
   - Keep bgjob launch, wait, result-env, and merge-env behavior intact.
   - On fresh launch, keep result-env reset and merge-env recreation. Remove only guard-era sentinel args, compatibility sentinel writes, and sentinel-only stale clears.

5. Repoint Section E terminal sentinels.
   - Prefer bgjob result envs at `$TMPDIR/bgjob/<step>.result.env`.
   - Delete daemon `--sentinel` args and compatibility writes when all consumers are repointed.
   - Record this decision table in the PR body:
     - `design .completed/step-3-terminal`: REPOINT to `bgjob/design-step3-review.result.env`; keep `.completed/step-3` as the distinct Gate B and pause milestone.
     - `.completed/step-4`: REPOINT Step 4 tail routing to `bgjob/design-step4-tail.result.env`.
     - `.completed/step-5c-terminal`: REPOINT Step 6 prelude and cleanup to `bgjob/design-step5c.result.env`.
     - `.completed/step-final-summary`: REPOINT final-summary completion to `bgjob/design-step-final-summary.result.env`.
     - `implement .completed/step-3-terminal`: REPOINT Step 3 checks routing to `bgjob/implement-step3-checks.result.env`.
     - `.completed/step-5-terminal`: REPOINT Step 5 review routing to `bgjob/implement-step5-review.result.env`.
     - `.completed/step-5-resume-terminal`: REPOINT resume routing to `bgjob/implement-step5-resume.result.env`.
     - `.completed/step-5-self-review-terminal`: REPOINT self-review routing to `bgjob/implement-checks-step5-self-review.result.env`.
     - `.completed/step-6-terminal`: REPOINT Step 6 routing to `bgjob/implement-step6-checks.result.env`.
     - `.completed/step-7a-terminal`: REPOINT Step 18 transcript condition to the Step 7a result env or another existing non-sentinel completion fact.
     - `.step-8-ship-handoff.rc`: REPOINT `ship route-exit` to `STEP8_HANDOFF_RC` from `bgjob/implement-step8-ship.result.env` if current merge-result KVs already carry it. Keep `.step-8-ship-handoff.json` if it remains the route payload. KEEP the `.rc` only if this repoint would require changing ship-driver semantics.

6. Remove guard-only lints, harnesses, and pre-commit hooks.
   - Delete writer-parity lint and tests.
   - Remove the `lint-bg-wait-writer-parity` hook from `.pre-commit-config.yaml`; keep `lint-bg-wait-coverage`.
   - Delete guard-only hook harnesses, the implement anti-polling literal harness and its companion doc, and the clone-ownership parity harness (both compared hooks are deleted; no surviving parity contract).
   - Keep `lint_bg_wait_coverage.py` and its Make targets.
   - Shrink or delete `bg_wait_allowlist.txt` so retained skill prose has zero `run_in_background: true` allowlist rows.

7. Replace prompt and doc prose.
   - Delete `skills/shared/design-background-wait.md` and `.claude/rules/wrapper-sentinel-before-stdout.md`.
   - Replace `AGENTS.md` notification bullets with the provided bgjob-owned daemon bullet.
   - Replace `orchestrator-never.md` items 3 to 5 with the provided bgjob wait rule, then renumber.
   - Rephrase `skills/shared/final-summary-emit.md` marker-first source binding without the literal `task-notification` token.
   - Sweep design, implement, research, and docs for notification-era terms.
   - Keep the replacement rule and `skills/shared/bgjob-wait.md`.

8. Add a mechanical extinct-token harness.
   - Add one harness that runs the acceptance grep outside `larch-logs/`.
   - Allow only the enumerated survivors.
   - Include test fixtures in the grep. Update or remove stale fixtures if they contain extinct text.

9. Update inventories and manifests.
   - Remove deleted scripts from `Makefile`, `.PHONY`, lint aggregate, test shards, `agent-lint.toml`, residual Bash inventory, and direct-target mappings.
   - Update `python/wire-artifact-manifest.json` for removed sentinel artifacts.
   - Update `python/migrated-scripts.tsv` where wrapper artifacts or compat sentinel notes change.
   - Regenerate `python/skill-closure-baseline.json` after prompt deletions.

## Files to modify/create

### UPDATED: hooks/hooks.json
Remove `hook-bg-poll-guard.sh` from `PreToolUse`. Remove both `hook-no-progress-guard.sh` entries from `Stop` and `UserPromptSubmit`. Keep the run-in-background deny hook and remaining shipped hooks.

### REWRITTEN: scripts/hook-bg-poll-guard.sh
Delete this file.

### REWRITTEN: scripts/hook-bg-poll-guard.md

### REWRITTEN: scripts/hook-no-progress-guard.sh

### REWRITTEN: scripts/hook-no-progress-guard.md

### UPDATED: scripts/hook-anti-read-poll.sh
Keep only generic repeated identical `Read` detection. Remove task-output token tracking, marker discovery, design/implement live-marker logic, bg-poll counters, and `LARCH_BG_POLL_GUARD_*` handling.

### UPDATED: scripts/hook-anti-read-poll.md
Document only the generic repeated-Read reminder.

### UPDATED: scripts/test-hook-anti-read-poll.sh
Keep generic repeated-Read tests. Delete task-output, marker, clamp, and notification recovery cases.

### REWRITTEN: scripts/test-hook-bg-poll-guard.sh
Delete this harness.

### REWRITTEN: scripts/test-hook-no-progress-guard.sh

### REWRITTEN: scripts/test-hook-clone-ownership-parity.sh
Delete this harness. Both compared hooks (`hook-bg-poll-guard.sh`, `hook-no-progress-guard.sh`) are removed; there is no surviving clone-ownership contract to pin.

### REWRITTEN: scripts/test-hook-clone-ownership-parity.md
Delete this harness doc with the script.

### REWRITTEN: scripts/test-implement-anti-polling-rule.sh
Delete this harness. The bgjob wait lint and harness now own the replacement rule.

### REWRITTEN: scripts/test-implement-anti-polling-rule.md
Delete this companion doc with the harness. It still pins retired literals (`design-background-wait`, `task-notification`, premature-notification recovery, and other removed contracts) and would fail the extinct-token acceptance grep after the `.sh` is removed.

### NEW: scripts/test-extinct-notification-stack.sh
Add a grep-based harness for the acceptance tokens. Exclude `larch-logs/` only. Permit the enumerated survivors in `skills/shared/bgjob-wait.md`, `skills/shared/orchestrator-never.md`, and `docs/configuration-and-permissions.md`.

### UPDATED: .pre-commit-config.yaml
Remove the `lint-bg-wait-writer-parity` hook entry. Keep `lint-bg-wait-coverage`.

### UPDATED: Makefile
Remove deleted targets, `.PHONY` entries, lint aggregate entries, and shard prerequisites for writer-parity lint, guard harnesses, clone-ownership parity, and implement anti-polling rule. Keep `lint-bg-wait-coverage` and `test-lint-bg-wait-coverage`. Add the extinct-token harness to one shard, then rebalance or manually validate shard coverage.

### UPDATED: agent-lint.toml
Remove the `scripts/test-hook-clone-ownership-parity.sh` pin and the `scripts/test-implement-anti-polling-rule.sh` pin (and its sibling-doc comment).

### UPDATED: python/larch/cli.py
Remove the `lint bg-wait-writer-parity` dispatch entry. Keep `lint bg-wait-coverage`.

### REWRITTEN: python/larch/implement/bg_wait.py
Delete this module after moving any still-needed non-guard helper.

### UPDATED: python/larch/design/design_core.py
Remove `_bg_wait_marker_context`, marker constants, no-progress cleanup, probe-counter cleanup, terminal-sentinel maps tied only to guard release, and the `bg_wait` import. Keep bgjob result-env helpers.

### UPDATED: python/larch/design/design_lifecycle.py
Remove imports or call paths for `_bg_wait_marker_context`.

### UPDATED: python/larch/design/design_step5c.py
Remove terminal-sentinel reset and write helpers if Step 5c completion is fully result-env based. Keep `.completed/step-5c` if it is a separate non-guard milestone.

### UPDATED: python/larch/design/design_step6.py
Use `bgjob/design-step5c.result.env` and registry state, not `.completed/step-5c-terminal`, to decide in-flight and complete Step 5c state.

### UPDATED: python/larch/design/design_terminal.py
Extend preferred bgjob result-env reading as needed for final-summary and Step 4/5c paths. Do not add new bgjob behavior.

### UPDATED: python/larch/review/plan_review_loop.py
Remove `.completed/step-3-terminal` and `.step3-terminal-persisted-this-run` from downstream-clear helpers once consumers are repointed. Keep `bgjob/design-step3-review.result.env`, `bgjob/design-step4-tail.result.env`, and merge-env clearing in `_step3_clear_downstream_sentinels` and equivalent re-entry paths. Route by result env and existing phase milestones.

### UPDATED: python/larch/review/plan_review_normalize.py
Remove Step 3 terminal-sentinel and persisted-sidecar writes. Preserve `.completed/step-3` and `.completed/step-3.5` milestone writes.

### UPDATED: python/larch/implement/dispatch_commit_route.py
Remove `_clear_step3_bg_wait_sidecars` and call sites. Keep checks routing unchanged.

### UPDATED: python/larch/implement/step_7a.py
Remove `.completed/step-7a-terminal` compatibility sentinel write. Ensure Step 7a completion remains discoverable through its bgjob result env or existing committed artifacts.

### UPDATED: python/larch/implement/dispatch_ship.py
Prefer `STEP8_HANDOFF_RC` from the Step 8 bgjob result env. Keep `.step-8-ship-handoff.rc` only if route-exit cannot safely consume result-env data without a behavior change.

### UPDATED: python/larch/bgjob/daemon.py
Remove legacy `LARCH_BG_POLL_GUARD_SESSION_PID` owner fallback only. Do not change daemon lifecycle, registry, wait, timeout, orphan, or result-env write semantics.

### UPDATED: python/larch/core/config.py
Remove obsolete env constants for no-progress and bg-poll guard knobs if present. Keep bgjob constants.

### REWRITTEN: python/larch/lint/lint_bg_wait_writer_parity.py
Delete this lint.

### REWRITTEN: python/tests/lint/test_lint_bg_wait_writer_parity.py
Delete this test.

### UPDATED: python/larch/lint/bg_wait_allowlist.txt
Shrink to empty or delete if the retained coverage lint supports a missing allowlist as zero entries.

### UPDATED: python/larch/lint/lint_bg_wait_coverage.py
If the allowlist is deleted, make the lint require zero allowlisted rows. Keep the inverse `run_in_background` enforcement.

### UPDATED: python/tests/lint/test_lint_bg_wait_coverage.py
Update fixtures for an empty or absent allowlist and the retained inverse rule.

### UPDATED: python/wire-artifact-manifest.json
Remove relative-path rows for sentinel artifacts that are no longer read or written.

### UPDATED: python/migrated-scripts.tsv
Remove or revise rows that describe sentinel compatibility artifacts.

### UPDATED: python/skill-closure-baseline.json
Regenerate after deleting `design-background-wait.md` and trimming prompt prose.

### UPDATED: python/env-via-config-constant-baseline.json
Remove obsolete baseline entries tied to deleted bg-wait helpers or env constants.

### UPDATED: python/tests/design/test_design_lifecycle.py
Remove bg-wait marker and terminal-sentinel assertions. Add result-env based assertions for Step 4, Step 5c, and final-summary routing.

### UPDATED: python/tests/review/test_plan_review.py
Remove `.step3-terminal-persisted-this-run` and `.completed/step-3-terminal` assertions. Assert result-env driven routing, fresh-launch result-env clearing, and milestone preservation.

### UPDATED: python/tests/implement/test_implement_dispatch.py
Remove sentinel args and bg-wait marker assertions. Add result-env routing assertions for Steps 3, 5, 5-resume, 6, and 8.

### UPDATED: python/tests/implement/test_step_7a.py
Remove terminal-sentinel assertions. Assert Step 7a result-env completion evidence.

### UPDATED: python/tests/bgjob/test_daemon.py
Remove legacy `LARCH_BG_POLL_GUARD_SESSION_PID` owner fallback cases if that env knob is removed. Keep bgjob owner tests for current envs.

### UPDATED: skills/design/scripts/design-step3-review.sh
Remove marker start, `--sentinel`, and guard-only terminal-sentinel compatibility writes. **Keep** fresh-launch hygiene: `rm -f "$DESIGN_TMPDIR/bgjob/design-step3-review.result.env"`, `step3_review_recreate_merge_env` (or equivalent merge-env reset), and stale downstream result-env clearing on re-entry. Remove only `.completed/step-3-terminal` and `.step3-terminal-persisted-this-run` from guard-era cleanup once consumers are repointed. Preserve merge-result env, bgjob start, and wait contract.

### UPDATED: skills/design/scripts/design-step3-review.md
Replace compatibility sentinel wording with result-env completion wording. Document that fresh-launch clears stale `bgjob/design-step3-review.result.env` and recreates merge env before `bgjob start`.

### UPDATED: skills/design/scripts/test-design-step3-review.sh
Remove sentinel pinning. Pin fresh-launch result-env clearing, merge-env recreation, bgjob result-env, and merge-env behavior instead.

### UPDATED: skills/design/scripts/design-step3b-tail.sh
Remove `--sentinel "$DESIGN_TMPDIR/.completed/step-4"` and any stale sentinel cleanup. Route Step 4 completion through the bgjob result env.

### UPDATED: skills/design/scripts/design-step3b-tail.md
Update Step 4 completion docs.

### UPDATED: skills/design/scripts/design-step3b-entry.sh
Replace `.completed/step-4` fallback checks with result-env or `.step4-mode.env` checks.

### UPDATED: skills/design/scripts/design-step5c.sh
Remove `--sentinel "$DESIGN_TMPDIR/.completed/step-5c-terminal"` and stale sentinel cleanup.

### UPDATED: skills/design/scripts/design-step5c.md
Document result-env completion only.

### UPDATED: skills/design/scripts/test-design-step5c.sh
Remove `step-5c-terminal` assertion. Assert `bgjob/design-step5c.result.env` and required KVs.

### UPDATED: skills/design/scripts/design-step-final-summary.sh
Remove final-summary compatibility sentinel if present. Use result-env completion.

### UPDATED: skills/design/scripts/design-step-final-summary.md

### UPDATED: skills/implement/scripts/run-step-checks.sh
Remove Step 3 and self-review sentinel args and bg-poll counter cleanup. Preserve bgjob step slugs and merge result envs.

### UPDATED: skills/implement/scripts/run-step-checks.md
Remove terminal-sentinel prose.

### UPDATED: skills/implement/scripts/step-5-review.sh
Remove `.completed/step-5-terminal` cleanup and `--sentinel`.

### UPDATED: skills/implement/scripts/step-5-review.md
State that completion requires bgjob result env and Step 5 KVs only.

### UPDATED: skills/implement/scripts/test-step-5-review.sh
Remove sentinel assertions. Keep result-env, stall, and rejoin assertions.

### UPDATED: skills/implement/scripts/test-step-5-review.md
Update harness docs.

### UPDATED: skills/implement/scripts/step-5-resume.sh
Remove `.completed/step-5-resume-terminal` cleanup and `--sentinel`.

### UPDATED: skills/implement/scripts/step-5-resume.md

### UPDATED: skills/implement/scripts/step-6-entry.sh
Remove `.completed/step-6-terminal` write, cleanup, and `--sentinel`.

### UPDATED: skills/implement/scripts/step-6-entry.md

### UPDATED: skills/implement/scripts/step-7a.md
Remove `.completed/step-7a-terminal` compatibility wording.

### UPDATED: skills/implement/scripts/step-8-ship.sh
Remove no-progress and bg-poll cleanup. Repoint `.step-8-ship-handoff.rc` to result-env data if safe. Keep route JSON sidecar only if still needed.

### UPDATED: skills/implement/scripts/step-8-ship.md
Replace stale guard text with current bgjob result-env and route-handoff contract.

### UPDATED: skills/implement/scripts/test-step-8-ship.sh
Remove bg-poll/no-progress assertions. Update rc expectations if `.step-8-ship-handoff.rc` is removed.

### UPDATED: skills/implement/scripts/step-18.sh
Replace `.completed/step-7a-terminal` transcript-capture condition with Step 7a result-env evidence.

### UPDATED: skills/implement/scripts/step-18.md
Update Step 7a and Step 8 prose.

### UPDATED: skills/implement/scripts/test-step-18.sh
Trim sentinel-guard assertions and add result-env evidence cases.

### UPDATED: AGENTS.md
Replace the two notification-era bullets with the provided long-running daemon bullet. Keep adjacent ScheduleWakeup, `/review --subagent`, and `/design` inline-only bullets unchanged.

### REWRITTEN: skills/shared/design-background-wait.md

### UPDATED: skills/shared/orchestrator-never.md
Delete current items 3, 4, and 5. Add the provided `NEVER wait on harness background tasks` rule. Renumber later items.

### UPDATED: skills/shared/bgjob-wait.md
Keep as the normative wait contract. Only update if references to deleted sentinels or background-task notification compatibility text remain.

### UPDATED: skills/shared/final-summary-emit.md
Rephrase the marker-first profile source binding and any forbidden-source examples without the literal `task-notification` token (for example, “not background-task notification output” or “captured foreground Bash wrapper stdout only”). Do not add this file to the extinct-token survivor list.

### REWRITTEN: .claude/rules/wrapper-sentinel-before-stdout.md

### UPDATED: skills/design/SKILL.md
Remove `design-background-wait.md`, task-notification recovery, compatibility sentinel, and terminal-sentinel completion text. Keep bgjob start/wait instructions and required result-env KVs.

### UPDATED: skills/design/references/flags.md
Remove notification-recovery text if present.

### UPDATED: skills/design/references/sentinel-host-table.md
Remove compatibility sentinel rows or mark surviving non-guard milestones only.

### UPDATED: skills/implement/SKILL.md
Remove remaining Immediate-background and task-notification text, including the stale portion of NEVER #8 and final-summary source bindings that cite `task-notification`. Keep the `ScheduleWakeup` and bgjob wait prohibitions. If Bash fences change, inspect `scripts/test-implement-fence-shape.sh`.

### UPDATED: scripts/test-implement-fence-shape.sh
Update `EXPECTED_OLD` / `EXPECTED_NEW` only if `skills/implement/SKILL.md` Bash fence shape changes.

### UPDATED: skills/implement/references/self-review.md
Remove self-review terminal-sentinel prose.

### UPDATED: skills/implement/references/conflict-resolution.md
Remove notification-era or terminal-sentinel wording if present.

### UPDATED: skills/implement/references/stall-recovery.md
Remove guard-sidecar wording if present.

### UPDATED: skills/implement/references/ship-pr-ci-fix.md
Remove notification-era wording if present.

### UPDATED: skills/implement/references/ship-pr-exit-matrix.md
Update Step 8 rc handling if `.step-8-ship-handoff.rc` is repointed.

### UPDATED: skills/research/SKILL.md
Repoint any `design-background-wait.md` reference to `bgjob-wait.md` or remove it.

### UPDATED: skills/research/references/research-phase.md
Remove task-notification wait-mechanism text if present.

### UPDATED: skills/research/references/validation-phase.md

### UPDATED: docs/configuration-and-permissions.md
Remove the four obsolete env knobs. Keep the optional `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1` note allowed by the acceptance criteria.

### UPDATED: docs/workflow-lifecycle.md
Remove guard hook, notification, and sentinel compatibility text. Keep bgjob diagnostics and Step 8 route semantics.

### UPDATED: docs/linting.md
Remove retired writer-parity, clone-ownership parity, and anti-polling harness documentation (including the `test-implement-anti-polling-rule` target and sibling contract). Keep coverage lint documentation.

### UPDATED: SECURITY.md
Update the shipped hook inventory. Remove `hook-bg-poll-guard.sh` and no-progress guard claims. Keep `hook-anti-read-poll.sh` as a generic repeated-Read hygiene hook.

### UPDATED: scripts/residual-bash-paths.txt
Remove deleted guard scripts and harnesses if listed.

### MAY_UPDATE: python/test_fixtures/plan-fidelity-calibration
Sweep tracked fixtures for extinct tokens. Update or remove stale calibration fixtures if the new extinct-token harness catches them.

### MAY_UPDATE: .github/workflows/ci.yaml
Touch only if harness shard count changes. If only shard membership changes inside `Makefile`, leave CI unchanged.

## Edge cases

- Stale sidecars under existing session dirs must become inert. Do not add migration code.
- `.completed/step-3` is not the same contract as `.completed/step-3-terminal`. Preserve `.completed/step-3` if pause, Gate B, or plan-review milestones still use it.
- Fresh-launch `rm -f` of `bgjob/*.result.env` and merge-env recreation must survive sentinel removal. Do not conflate result-env hygiene with guard-era sentinel cleanup.
- Step 8 `.step-8-ship-handoff.rc` may be route data, not guard-only. Delete it only after route-exit can consume equivalent current data from the bgjob result env.
- Test fixtures are tracked files. The extinct-token harness must not exempt them unless the acceptance criteria are changed.
- Removing `design-background-wait.md` can shrink skill-closure baselines. Regenerate, do not hand-edit counts.
- `lint_consecutive_bash.py` has explicit task-notification and sentinel carve-outs. Remove only carve-outs that are no longer needed by current fences.
- Keep `hook-deny-run-in-background.sh`; it is the replacement guard, not part of the obsolete stack.
- Deleting clone-ownership parity without removing its Make target, shard prerequisite, `agent-lint.toml` pin, or pre-commit writer-parity hook leaves CI calling removed commands.
- Deleting `scripts/test-implement-anti-polling-rule.sh` without also deleting `scripts/test-implement-anti-polling-rule.md` leaves a tracked doc that still contains extinct tokens (`design-background-wait`, `task-notification`, `premature notification`, and related retired contracts) and fails the acceptance grep.

## Failure modes when non-trivial

- A stale sentinel reader can make a bgjob-complete step look incomplete.
- Removing a sentinel writer before all consumers are repointed can break resume.
- Removing fresh-launch result-env clearing while deleting sentinels can make a new launch inherit stale `BGJOB_RC` or `NEXT_ACTION` from a prior run.
- Deleting `.step-8-ship-handoff.rc` without route-exit repointing can break ship routing.
- Over-broad grep cleanup can remove historical explanation in the two allowed replacement docs.
- Incomplete Makefile or pre-commit cleanup can leave orphaned targets or missing shard coverage.
- Removing legacy env fallback from bgjob owner detection can break a caller that has not adopted current owner envs. Verify all bgjob launchers set current envs before removing the fallback.
- Leaving `task-notification` literals in `final-summary-emit.md` or implement SKILL bindings will fail the extinct-token acceptance grep.
- Leaving `scripts/test-implement-anti-polling-rule.md` after harness deletion will fail the extinct-token acceptance grep even when all runtime surfaces are cleaned up.

## Testing strategy

1. Static token and config checks:
   - `bash scripts/test-extinct-notification-stack.sh`
   - `jq . hooks/hooks.json`
   - `git grep -n` for each extinct token with `':!larch-logs'`
   - `git grep -n 'task-notification\|run_in_background' -- AGENTS.md skills`

2. Targeted hook and harness checks:
   - `make test-hook-anti-read-poll`
   - `make test-hook-deny-run-in-background`
   - `make test-sessionstart`
   - `make test-harness-shards-coverage`
   - Confirm `make test-hook-clone-ownership-parity`, `make test-implement-anti-polling-rule`, and `make test-lint-bg-wait-writer-parity` are gone from the Makefile

3. Targeted Python tests:
   - `python3 -m pytest python/tests/lint/test_lint_bg_wait_coverage.py`
   - `python3 -m pytest python/tests/design/test_design_lifecycle.py python/tests/review/test_plan_review.py`
   - `python3 -m pytest python/tests/implement/test_implement_dispatch.py python/tests/implement/test_step_7a.py`
   - `python3 -m pytest python/tests/bgjob`

4. Aggregate local checks:
   - `make lint`
   - `make py-lint`
   - `make py-test`
   - `make test-harnesses`
   - `pre-commit run lint-bg-wait-coverage --all-files` (writer-parity hook must be absent)

5. Manual acceptance after merge:
   - Run one full `/design`.
   - Run one full `/implement --merge`.
   - Confirm transcripts contain no guard messages, sidecar paths, or notification-recovery turns.

## Difficulty

confidence: medium

## Acceptance

1. Static token and config checks:
   - `bash scripts/test-extinct-notification-stack.sh`
   - `jq . hooks/hooks.json`
   - `git grep -n` for each extinct token with `':!larch-logs'`
   - `git grep -n 'task-notification\|run_in_background' -- AGENTS.md skills`

2. Targeted hook and harness checks:
   - `make test-hook-anti-read-poll`
   - `make test-hook-deny-run-in-background`
   - `make test-sessionstart`
   - `make test-harness-shards-coverage`
   - Confirm `make test-hook-clone-ownership-parity`, `make test-implement-anti-polling-rule`, and `make test-lint-bg-wait-writer-parity` are gone from the Makefile

3. Targeted Python tests:
   - `python3 -m pytest python/tests/lint/test_lint_bg_wait_coverage.py`
   - `python3 -m pytest python/tests/design/test_design_lifecycle.py python/tests/review/test_plan_review.py`
   - `python3 -m pytest python/tests/implement/test_implement_dispatch.py python/tests/implement/test_step_7a.py`
   - `python3 -m pytest python/tests/bgjob`

4. Aggregate local checks:
   - `make lint`
   - `make py-lint`
   - `make py-test`
   - `make test-harnesses`
   - `pre-commit run lint-bg-wait-coverage --all-files` (writer-parity hook must be absent)

5. Manual acceptance after merge:
   - Run one full `/design`.
   - Run one full `/implement --merge`.
   - Confirm transcripts contain no guard messages, sidecar paths, or notification-recovery turns.

diff_added: 725
diff_deleted: 5818
mechanical_churn: false
oversize_override: operator
diff_lines: 6543

## Test plan
(no test plan section in plan-file)
