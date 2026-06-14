## Goal
Implement issue #4075: [IMPLEMENTING] /design: references raw-Bash sweep plus structural lint for script-only fences.

## Implementation Plan
## Plan

## Approach

Use the existing wrapper pattern. Keep prompt-facing `bash` fences thin and launcher-owned.

Scope is limited to `skills/design/` Step 1d.5, Step 2b.5, validator-autofix, two `plan-review.md` examples, and the structural lint. Do not touch `skills/implement/` or `skills/design/scripts/*.md` example docs beyond sibling contract updates.

## Files to modify/create

### UPDATED: scripts/launch-review.sh

When the timing kind belongs to the brainstorm family (`cursor-brainstorm` or `codex-brainstorm`) and `--stderr-sink` is set, skip `append_launch_failure` and write the sink instead. Let `design-step1d5.sh --mode collect` own run-log ingestion via its per-log sentinels so a single launch failure produces exactly one External Reviewer Issues row on resume.

### UPDATED: skills/design/scripts/design-step1d5.sh

Add `--mode collect`.

Update `--mode entry`:

- Source the session env.
- Batch-write `.completed/step-1c` and `.completed/step-1d`.
- Read `brainstorm_requested` from `$DESIGN_TMPDIR/run-params.json`.
  - Prefer `jq` when present.
  - Fall back to the existing grep pattern used in pause-resume tests.
- If brainstorm is not requested:
  - Write `.completed/step-1d.5`.
  - Print `⏩ 1d.5: brainstorm — skipped`.
  - Run the existing pause check after sentinel repair.
  - Exit 0.
- If `.brainstorm-done` exists:
  - Write `.completed/step-1d.5`.
  - Print the existing already-complete skip breadcrumb.
  - Run the existing pause check.
  - Exit 0.
- Otherwise keep the current timing mark and allow the prompt body to run.

Add `--mode collect -- <output paths...>`:

- Source env and pause-check before work.
- Reject zero paths with exit 2, since brainstorm.md must omit the collect call when no externals launched.
- Run `${CLAUDE_PLUGIN_ROOT}/scripts/collect-agent-results.sh --timeout 1260` with only the supplied paths.
- Capture stdout and stderr to `$DESIGN_TMPDIR/brainstorm-collect.failure.log` on non-zero rc.
- Append collector failures to `$DESIGN_TMPDIR/execution-issues.md` through `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" run-log append-failure`.
- Scan canonical launch failure logs, derived from the supplied collect paths:
  - For each path matching `cursor-brainstorm-output.txt`: check `$DESIGN_TMPDIR/cursor-brainstorm-launch.failure.log`.
  - For each path matching `codex-brainstorm-output.txt`: check `$DESIGN_TMPDIR/codex-brainstorm-launch.failure.log`.
- Append those launch logs once each using per-log sentinels to avoid duplicate run-log entries on resume.
- Run `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" dirty-tree checkpoint`.
- If it emits `STATUS=dirty` or `STATUS=unknown`, write `$DESIGN_TMPDIR/dirty-tree-detected.env` and print a `WARN=` line.
- Preserve collector stdout for operator visibility.

Keep `--mode complete`:

- Source env.
- Write `.completed/step-1d.5`.
- Pause-check as today; add a trailing no-op exit after the pause check so the script exits 0 when no pause is pending.

### UPDATED: skills/design/scripts/design-step1d5.md

Document:

- `--mode entry` now completes the brainstorm-off and already-done skip paths.
- `--mode collect -- <paths...>` is the only prompt-facing collection call after external brainstorm launches; launch-failure log ingestion is derived from the supplied collect paths.
- `--mode complete` is called only by the active brainstorm terminal path.

### UPDATED: skills/design/references/brainstorm.md

Replace both raw collection fences with launcher-form examples:

- One external:
  - `"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step1d5.sh --mode collect -- "$DESIGN_TMPDIR/cursor-brainstorm-output.txt"`
- Two externals:
  - Same wrapper call with both canonical output paths.

Remove the separate dirty-tree checkpoint bash fence. State that `design-step1d5.sh --mode collect` owns:

- `collect-agent-results.sh`
- launch and collector failure logging (derived from the supplied collect paths)
- dirty-tree checkpoint side effects

Update the entry guard wording:

- Brainstorm-off and already-complete skip paths are completed by `--mode entry`.
- The top-level `SKILL.md` no longer runs an unconditional `--mode complete`.

Update the free-form loop terminal branch:

- After writing `.brainstorm-done`, run `design-step1d5.sh --mode complete` through the launcher.
- Then continue to Step 1d.7 in the same turn.

Keep parent-written Agent fallback behavior unchanged.

### UPDATED: skills/design/SKILL.md

Step 1d.5:

- Remove the unconditional post-body `design-step1d5.sh --mode complete` fence.
- State that `--mode entry` writes `.completed/step-1d.5` for skip paths.
- State that `brainstorm.md` owns `--mode collect` and `--mode complete` for active brainstorm paths.
- Continue to Step 1d.7 after Step 1d.5 returns or skips.

Step 2b.5:

- Replace the rc=2 and other non-zero capture-and-append prose with: the wrapper owns logging for non-zero `plan check-size` statuses.
- Instruct the operator flow to parse `PLAN_SIZE_RC=` from wrapper output.
- For `PLAN_SIZE_RC=0`, continue with the existing size, partition, drift, and no-trigger branches.
- For `PLAN_SIZE_HANDLED=true`, return to the caller without firing size branches.

Validator-autofix:

- Replace raw `run-log append-failure` command prose in auto-fix result branches with wrapper-owned warning logging.
- Keep the `AskUserQuestion` labels unchanged.
- For Override, call a wrapper-owned record path instead of spelling the raw append command in prompt prose.

### UPDATED: skills/design/scripts/design-step2b5.sh

Finish the wrapper so it owns the current capture boundary.

Behavior:

- Source env and pause-check first.
- Run `env LARCH_QUIET_DISABLE=1 python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" plan check-size --design-tmpdir "$DESIGN_TMPDIR"`.
- Capture stdout separately from stderr.
- Always print original stdout.
- Print `PLAN_SIZE_RC=<rc>`.
- On rc 0:
  - Exit 0.
  - Do not append warnings.
- On rc 2:
  - Parse `PLAN_SIZE_STATUS=` from stdout when present.
  - Write stdout plus stderr to `$DESIGN_TMPDIR/check-plan-size.validation.log`.
  - Append a `Warnings` run-log entry with site `design Step 2b.5`, tool `python/cli.py plan check-size`, and the real rc.
  - Print the existing warning line.
  - Print `PLAN_SIZE_HANDLED=true`.
  - Exit 0.
- On any other non-zero rc:
  - Use the same log file and append path.
  - Print `PLAN_SIZE_HANDLED=true`.
  - Exit 0.

Do not implement AskUserQuestion branches in the wrapper.

### UPDATED: skills/design/scripts/design-step2b5.md

Document the stdout contract:

- Original `plan check-size` stdout is preserved.
- `PLAN_SIZE_RC=` is appended by the wrapper.
- `PLAN_SIZE_HANDLED=true` means the wrapper logged the failure and the caller should return without threshold branches.

### UPDATED: skills/design/scripts/design-step-validator-autofix.sh

Add wrapper-owned warning logging.

Add helpers:

- `validator_autofix_log_warning TOOL_LABEL OUTPUT_FILE EXIT_CODE`
- `validator_autofix_record_override`

Use the existing site, target file, and `_autofix_log_file` values.

After status normalization:

- For `ok`, append `Warnings` with tool `validate-plan-commands(auto-fixed:${_autofix_fixed_by})`.
- For `exhausted`, `unavailable`, `failed`, or `skipped-cycle-cap`, append `Warnings` with tool `validate-plan-commands(auto-fix-${_autofix_status})`.
- Preserve existing escalation recording before the operator prompt.
- Keep status stdout unchanged.

Add a CLI flag for override logging:

- `--record-override`
- Source env and pause-check.
- Append `Warnings` with tool `validate-plan-commands`.
- Exit 0.

Keep `--operator-cancel` behavior unchanged.

Do not add valued `--redact <value>` arguments to any `run-log append-failure` call; use only the boolean `--redact` flag as today.

### UPDATED: skills/design/scripts/design-step-validator-autofix.md

Document:

- Auto-fix status branches append their own `Warnings` records.
- `--record-override` records the operator override warning.
- Prompt-side prose must not spell raw `run-log append-failure` commands for these branches.

### UPDATED: skills/design/references/plan-review.md

Demote two executable-looking examples from `bash` to `text` fences:

- The superseded collector fence under `Collecting External Reviewer Results`.
- The voter-dispatch argv reference under `Voting Panel launch-order and tally`.

Do not alter the command text inside the examples unless needed for surrounding prose.

### UPDATED: scripts/test-design-structure.sh

Add `assert_references_bash_fences_are_scripts`.

Scope:

- `skills/design/SKILL.md` remains covered by existing wrapper-only checks.
- New scan covers only `skills/design/references/*.md`.
- Do not scan `skills/design/scripts/*.md`.

Fence rule:

- For every `bash` fence in `references/*.md`, inspect the first non-empty, non-comment line.
- Accept if that line starts with one of:
  - `${CLAUDE_PLUGIN_ROOT}/`
  - `"${CLAUDE_PLUGIN_ROOT}/`
  - `python3 "${CLAUDE_PLUGIN_ROOT}/`
  - `python3 ${CLAUDE_PLUGIN_ROOT}/`
  - `"$HOME/.cache/larch/sessions/design-run-$PPID.sh"`
- Reject raw preludes such as:
  - `[ -f ... ] && source ...`
  - variable setup like `_launch_id=...`
  - shell control flow as the first command
- Support same-line suppression:
  - `# lint-script-only-fences: ok <reason>`
- Require a non-empty reason after `ok`.
- Print file and fence start line on failure.

Add fixtures inside the Python scan for accepted and rejected first-line shapes.

Call the new assertion from the main assertion list.

Add pins:

- `brainstorm.md` contains `design-step1d5.sh --mode collect`.
- `plan-review.md` no longer has `bash` fences whose first command is `[ -f ~/.cache/larch/sessions/current-design-env-$PPID.sh ]` or `_launch_id=`.

### UPDATED: scripts/test-design-structure.md

Add a short section for the new references fence lint:

- Scope is `skills/design/references/*.md`.
- `skills/design/scripts/*.md` remains documentation-only and out of scope.
- Valid bash fences must start with a plugin-rooted script, plugin-rooted `python/cli.py`, or the session launcher.
- Suppression format is `# lint-script-only-fences: ok <reason>`.

## Edge cases

- Brainstorm requested but no external slots launch: do not call `--mode collect`; synthesize from parent-written or Claude-only outputs, then call `--mode complete` on terminal.
- Brainstorm skipped on resume: `--mode entry` must write `.completed/step-1d.5` exactly once and must not require the top-level complete fence.
- `jq` absent: run-params parsing must still detect `"brainstorm_requested": true`.
- Collector failure after one external succeeds: log the failure, preserve available output, and let the parent synthesize from readable outputs.
- Dirty-tree unknown: write `dirty-tree-detected.env` and warn, matching plan-review-loop behavior.
- Validator auto-fix status missing or unknown: normalize to `failed`, log a warning, and fall through to the operator prompt.

## Failure modes

- If `design-step1d5.sh --mode collect` is invoked with zero paths, exit 2. This catches prompt drift.
- If `plan check-size` emits stderr noise, do not mix it into parseable stdout. Store it only in the validation log.
- If warning append fails, suppress that append failure with `|| true` to preserve current degraded behavior.
- If the structural lint flags documentation examples that are not orchestrator-facing, narrow scope rather than adding suppressions.

## Testing strategy

Run focused checks:

- `bash -n skills/design/scripts/design-step1d5.sh`
- `bash -n skills/design/scripts/design-step2b5.sh`
- `bash -n skills/design/scripts/design-step-validator-autofix.sh`
- `bash scripts/test-design-structure.sh`
- `bash skills/design/scripts/test-design-step-validator-autofix.sh`
- `make test-design-structure`
- `make test-check-plan-size`
- `make test-auto-fix-plan-commands`

Run repository-relevant checks before handoff:

- `bash scripts/relevant-checks.sh`

## Non-goals

- Do not refactor `collect-agent-results.sh`.
- Do not change plan-review dispatch logic.
- Do not scan `skills/design/scripts/*.md`.
- Do not update `scripts/test-design-structure.md`.
- Do not add new pre-commit hooks for this lint. Keep it inside `scripts/test-design-structure.sh`.
- Do not move dirty-tree operator recovery into `design-step1d5.sh`; the wrapper records evidence, while `brainstorm.md` owns the prompt.
- Do not add valued redact arguments to validator-autofix wrapper APIs.

## Acceptance

- Zero raw-Bash bash fences under `skills/design/references/`; `assert_references_bash_fences_are_scripts` fails on regression and passes on the cleaned tree.
- Brainstorm-off path: one Bash call (`design-step1d5.sh --mode entry`).
- Brainstorm externals collection: one Bash call after launches (`design-step1d5.sh --mode collect -- <paths>`).

diff_lines: 670

## Test plan
(no test plan section in plan-file)
