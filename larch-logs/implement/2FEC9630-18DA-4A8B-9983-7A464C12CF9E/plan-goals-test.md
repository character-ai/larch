## Goal
Implement issue #3679: [IMPLEMENTING] sh-to-py C3a2: design plan-command validation + revision waterfall.

## Implementation Plan
## Plan

## Plan

## Approach

- Use **direct inspection** only.
- Use the existing **`plan` CLI domain**.
  - It already owns `plan scope-paths`.
  - Add plan-quality verbs there instead of creating a new domain.
- Keep behavior **byte-compatible** where callers consume machine output.
  - Preserve TSV headers and row types.
  - Preserve `KEY=value` contract output.
  - Preserve exit codes that wrappers branch on.
  - Preserve log filenames where downstream scripts read them.
  - Preserve validator evidence paths that downstream auto-fix and postplan readers consume.
- Port the shell domain into one stdlib-only module.
  - Avoid shims.
  - Let surviving bash callers invoke `python3 "$PLUGIN_ROOT/python/cli.py" plan <verb> ...` directly.
- Delete absorbed bash surfaces only after callers and pytest parity are in place.
- Do not port `lib-drift-baseline.sh` wholesale.
  - Inline only the drift-baseline file read/write and unreadable-marker semantics needed by plan-size checks.
  - Do not subprocess-source the bash library from Python.
  - Do not broaden scope into a general drift-baseline port.
- Keep **authoritative contract docs** that remain loaded by `/design`.
  - Repoint them to the Python CLI surfaces before deleting absorbed scripts.
  - Include basename-only stale references in the final sweep.

## Files to modify/create

### NEW: python/plan_quality.py

Implement importable functions and CLI mains for the absorbed plan-quality surface.

Suggested public function groups:

- **Plan command parsing**
  - `parse_plan_commands(plan_text, repo_root, plugin_root) -> list[PlanCommandRow]`
  - `render_plan_command_tsv(rows) -> str`
  - `parse_plan_commands_main(argv) -> int`
- **Plan command validation**
  - `validate_plan_command_rows(rows, repo_root, registry, source_kind, help_timeout, dry_run_timeout) -> ValidationResult`
  - `validate_plan_commands_main(argv) -> int`
  - `validate_plan_main(argv) -> int`
- **Optional trailer metadata**
  - `last_nonempty_line_number(path) -> int`
  - `parse_optional_metadata(plan_text) -> OptionalMetadata`
  - `snapshot_optional_trailer_keys_main(argv) -> int`
  - `snapshot_optional_trailer_values_main(argv) -> int`
  - `optional_trailers_main(argv) -> int`
  - `validate_optional_trailer_keys_preserved(...)`
  - `validate_optional_trailers_preserved(...)`
- **Plan-size checks**
  - `check_plan_size(...) -> PlanSizeResult`
  - `check_plan_size_main(argv) -> int`
- **Revision waterfall**
  - `revise_plan_with_waterfall(...) -> ReviseResult`
  - `revise_plan_with_waterfall_main(argv) -> int`
- **Plan-command auto-fix**
  - `auto_fix_plan_commands(...) -> AutoFixResult`
  - `auto_fix_plan_commands_main(argv) -> int`
- **Plan-goals test composition**
  - `compose_plan_goals_test(plan_text, goal_text) -> str`
  - `compose_plan_goals_test_main(argv) -> int`

Port behavior from the absorbed parser, validator, plan-size, optional-trailer, revision-waterfall, auto-fix, invoke-validator, validate-plan wrapper, and plan-goals composer scripts.

Implementation notes:

- Use `argparse` in each `*_main`.
- Use `logging_util.quiet_init`, `emit`, and `emit_kv` for contract streams.
- Use `proc.py` helpers where they fit.
- Use `subprocess.run` only where the bash code already launched external tools.
- Prefer Python `subprocess.run(..., timeout=seconds)` over shell timeout helpers.
- Keep path guards explicit.
  - Reject CR/LF in revision paths.
  - Resolve symlinks for plan, findings, and feature files.
  - Require revision plan target to resolve to `$DESIGN_TMPDIR/plan.txt`.
  - Require findings and feature files to resolve under `$DESIGN_TMPDIR`.
- Port parser logic, not shell parsing.
  - Handle fenced `bash` and `sh` blocks.
  - Join continuations.
  - Strip heredoc bodies.
  - Split segments on `|`, `&&`, `||`, and `;` outside quotes and parentheses.
  - Emit `parse_note` rows for command substitution, process substitution, `eval`, inline shell, non-canonical script paths, and charset violations.
  - Normalize plugin-root, repo-root, env-prefix, and dot-slash path forms.
  - Preserve allow-list rows from `### NEW:`, `### UPDATED:`, bracket heading forms, and legacy files-to-create/update sections.
- Port validator behavior.
  - Validate repo script paths only under `scripts/*`, `skills/*/scripts/*`, and `.claude/skills/*/scripts/*`.
  - Skip new scripts.
  - Probe `--help`.
  - Treat exit 0, 1, or 2 with non-empty help output as usable help.
  - Validate long flags using the same distinct-token rule.
  - Read dry-run registry from `scripts/dry-runnable-scripts.tsv` by default.
  - Support `--validate-only` and `LARCH_DRY_RUN=1`.
  - Skip Tier 3 for `--source-kind composed`.
  - Redact Tier 3 capture through `python3 python/cli.py redact secrets`.
- Port validate-plan wrapper behavior into `plan validate`.
  - Parse the plan, run command validation, and emit the same `VALIDATE_*` stdout KVs as the retired wrapper.
  - Preserve the wrapper status model.
    - Command defects emit `VALIDATE_STATUS=defects-found` and return the same success rc expected by callers that branch on the status key.
    - Infrastructure failures emit the corresponding failure status and return a nonzero rc.
  - Preserve `VALIDATE_LOG_FILE`.
    - Read `DESIGN_TMPDIR` from the environment.
    - Also accept `--design-tmpdir DIR` for explicit tests and future callers.
    - When a valid design tmpdir exists, copy the full validator log to `$DESIGN_TMPDIR/validate-plan-commands.log`.
    - Emit `VALIDATE_LOG_FILE` pointing at that copied log.
    - When no design tmpdir is available, emit `VALIDATE_LOG_FILE` pointing at a stable temp log path that is not removed by `EXIT` cleanup before post-run readers can inspect it.
  - Preserve validator log contents and copy timing so auto-fix can copy `ORIGINAL_VALIDATE_LOG_FILE`.
- Port plan-size behavior.
  - Preserve `PLAN_SIZE_STATUS` values.
  - Preserve rc 0, 2, and 3 meanings.
  - Keep thresholds: plan body over 800, diff lines over 1500, diff added over 2000.
  - Preserve `mechanical_churn: true` soft advisory behavior.
  - Inline only the current drift-baseline env file behavior needed for existing `DRIFT_*` output and baseline seeding.
  - Preserve unreadable baseline handling and recovery semantics.
  - Do not call or source `lib-drift-baseline.sh` from Python.
  - Do not expand into a full drift-baseline library migration.
- Port revision waterfall behavior.
  - Compose prompts with the same trust-boundary wording.
  - Use existing B4 launcher surfaces:
    - `scripts/launch-review.sh --tool codex`
    - `scripts/launch-review.sh --tool cursor`
    - `python3 python/cli.py agent launch-claude-review`
  - Preserve tier order: Codex, Cursor, Claude, then file-replacement fallback for unified-diff mode.
  - Preserve output paths under `$DESIGN_TMPDIR/plan-review/round-N/revise`.
  - Preserve `revise.env` keys and stdout `REVISE_*` keys.
  - Preserve optional trailer key checks.
  - Preserve heading-count guard.
- Port auto-fix behavior.
  - Keep bounded vendor alternation.
  - Keep plan-file target under design tmpdir.
  - Keep non-target tmpdir and repo dirty-tree guards.
  - Keep original validator log copy behavior.
  - For `plan.txt` targets, keep the Gate B trailer snapshot and dedup coupling.
    - Minimum-change path: subprocess `skills/design/scripts/gate-b-dedup-plan.sh --snapshot-trailers` before vendor edits.
    - Then subprocess `skills/design/scripts/gate-b-dedup-plan.sh --dedup` after vendor edits.
    - Preserve the same failure, restoration, and breadcrumb behavior as the bash auto-fix path.
  - Keep stdout keys:
    - `AUTOFIX_STATUS`
    - `VENDOR_SEQUENCE`
    - `ATTEMPTS`
    - `FIXED_BY`
    - `FINAL_VALIDATE_STATUS`
    - `ORIGINAL_VALIDATE_LOG_FILE`
    - `REVALIDATE_LOG_FILE` when applicable.
  - When revalidating, rely on the Python `plan validate` log contract so `ORIGINAL_VALIDATE_LOG_FILE` and `REVALIDATE_LOG_FILE` are stable readable files.
- Port compose-plan-goals-test behavior.
  - Preserve pointer-only rejection.
  - Preserve minimum 64-byte plan check.
  - Preserve test-section extraction headings.
  - Preserve duplicated-heading stripping under `## Implementation Plan`.

### NEW: python/test_plan_quality.py

Replace absorbed shell harness coverage with pytest.

Coverage blocks:

- **Parser golden fixtures**
  - Parametrize every current parser fixture before deleting fixture files.
  - Assert exact TSV output.
  - Include direct unit tests for continuations, heredocs, arithmetic substitution, command substitution notes, env prefixes, dot-slash normalization, quoted argv, bracket headings, and updated flag allow-list rows.
- **Validator integration**
  - Port validator and invoke-validator harness coverage.
  - Create temporary fixture scripts at runtime instead of embedding retired-path literals.
  - Test unknown flags, missing scripts, noncanonical paths, `./` paths, new-script skips, updated flag allow-list, nonzero help rc, empty help skip, Tier 3 dry-run pass/fail, unsafe token redaction, `--validate-only`, bad registry hooks, composed-plan Tier 3 skip, direct `plan validate` stdout KVs, and quiet-parent capture with `LARCH_QUIET_DISABLE=1`.
  - Test `plan validate` log handling with `DESIGN_TMPDIR` set.
    - Assert the copied log path is `$DESIGN_TMPDIR/validate-plan-commands.log`.
    - Assert `VALIDATE_LOG_FILE` points at that copied log.
    - Assert the file remains readable after the command exits.
  - Test `plan validate` log handling without `DESIGN_TMPDIR`.
    - Assert `VALIDATE_LOG_FILE` points at a stable temp file.
    - Assert the file remains readable after the command exits.
  - Test defects-found wrapper semantics.
    - Assert command defects emit `VALIDATE_STATUS=defects-found`.
    - Assert the rc matches the retired wrapper success behavior expected by postplan and publish callers.
  - Test infrastructure-failure semantics.
    - Assert nonzero rc and log evidence are preserved.
- **Optional trailers**
  - Port trailer helper coverage into pure unit tests.
  - Assert keys, values, parse mode, absent keys, duplicate strict trailers, `0[89]` rejection, invalid `mechanical_churn`, block-boundary scan, and preservation checks.
  - Assert `snapshot-keys` plus `snapshot-values` writes the `.values` companion required by Gate B snapshot mode.
- **Plan-size**
  - Port plan-size harness coverage.
  - Cover missing plan, missing `diff_lines`, invalid `mechanical_churn`, baseline recovery, unreadable baseline handling, drift advisory, size trigger, partition flag interaction if applicable, `diff_added` basis, mechanical churn soft advisory, and normal under-threshold output.
  - Assert drift-baseline behavior is implemented without sourcing the retired bash library.
- **Revision waterfall**
  - Port revision waterfall harness coverage using fake launchers.
  - Assert tier order, skipped absent vendors, no-patch handling, invalid diff rejection, apply failure restoration, emit-plan gate failure restoration, heading guard, optional trailer preservation, file-replacement fallback, `revise.env`, and stdout keys.
- **Auto-fix**
  - Port auto-fix harness coverage.
  - Assert vendor alternation, unavailable vendors, cycle caps if covered by caller tests, non-target tmpdir restoration, repo dirty-tree guard, validator infrastructure failure, redacted prompt fallback, revalidation success source, stable original validator log copying, and Gate B snapshot/dedup subprocess coupling for `plan.txt`.
- **Plan-goals composer**
  - Port composer harness coverage.
  - Assert goal, plan body, test section extraction, heading stripping, pointer-only failures, short plan failures, and empty test-plan fallback.

Test hygiene:

- Build retired paths dynamically where stale-reference lint could otherwise match full retired paths.
- Use `Path(__file__).with_name("cli.py")` for CLI subprocess tests.
- Use temp dirs for all writable test state.
- Avoid network.
- Keep tests stdlib plus pytest only.

### UPDATED: python/cli.py

Register new verbs under the existing `plan` domain:

- `("plan", "parse-commands")`
- `("plan", "validate-commands")`
- `("plan", "validate")`
- `("plan", "check-size")`
- `("plan", "revise-waterfall")`
- `("plan", "auto-fix-commands")`
- `("plan", "optional-trailers")`
- `("plan", "compose-goals-test")`

Add machine-output verbs that emit captured stdout contracts to `_MACHINE_STDOUT_KEYS`.

Include at least:

- `plan validate`
- `plan validate-commands`
- `plan check-size`
- `plan revise-waterfall`
- `plan auto-fix-commands`
- any optional-trailer subcommand whose stdout is parsed by callers.

Preferred CLI contracts:

```bash
python3 python/cli.py plan parse-commands --plan-file FILE --output FILE [--repo-root DIR]
python3 python/cli.py plan validate-commands --tsv-file FILE --log-file FILE [--dry-runnable-registry FILE] [--source-kind plan|composed] [--help-timeout SEC] [--dry-run-timeout SEC]
python3 python/cli.py plan validate --plan-file FILE [--repo-root DIR] [--source-kind plan|composed] [--design-tmpdir DIR]
python3 python/cli.py plan check-size --design-tmpdir DIR [--plan-file PATH]
python3 python/cli.py plan revise-waterfall --design-tmpdir DIR --plan-file FILE --findings-file FILE --feature-file FILE --round-num N --codex-present true|false --cursor-present true|false [--timeout SECS] [--patch-format unified-diff|file-replacement]
python3 python/cli.py plan auto-fix-commands --design-tmpdir DIR --plan-file PATH --codex-present true|false --cursor-present true|false [--codex-available true|false] [--cursor-available true|false] [--repo-root DIR] [--max-attempts N] [--site STR] [--timeout SECS]
python3 python/cli.py plan optional-trailers <parse|keys|values|has-key|snapshot-keys|snapshot-values|validate-keys|validate-values> ...
python3 python/cli.py plan compose-goals-test --plan-file PATH [--goal-text TEXT]
```

For `plan validate`:

- Prefer `--design-tmpdir` when passed.
- Fall back to inherited `DESIGN_TMPDIR`.
- Emit `VALIDATE_LOG_FILE` even when no design tmpdir is available.
- Do not clean the emitted log path before callers can read it.

### UPDATED: skills/design/scripts/design-driver.sh

Cut `VALIDATE_PLAN_COMMANDS` from the shell validator wrapper to:

```bash
python3 "$PLUGIN_ROOT/python/cli.py" plan validate "$@"
```

Add a **plugin-root bootstrap** before the validation branch.

Required bootstrap behavior:

- Resolve `REPO_ROOT` from the script location.
- Set `PLUGIN_ROOT` from `CLAUDE_PLUGIN_ROOT` when present.
- Fall back to the resolved repo root when `CLAUDE_PLUGIN_ROOT` is unset.
- Export `CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT"` when filling the fallback.
- Keep the bootstrap compatible with checkout execution without a loaded plugin.
- Ensure the command never expands an empty `PLUGIN_ROOT` into `/python/cli.py`.

Preserve inherited `DESIGN_TMPDIR` so `plan validate` can copy the validator log to `$DESIGN_TMPDIR/validate-plan-commands.log`.

### UPDATED: skills/design/scripts/design-postplan-emit.sh

Cut both plan-quality call sites to the Python CLI.

For plan-size execution, call:

```bash
env LARCH_QUIET_DISABLE=1 python3 "$PLUGIN_ROOT/python/cli.py" plan check-size --design-tmpdir "$DESIGN_TMPDIR"
```

Rewrite `_postplan_run_plan_size` so it no longer requires an executable retired shell script before running plan-size validation.

Keep:

- `LARCH_QUIET_DISABLE=1` behavior.
- stderr capture.
- merged failure rc handling.
- `check-plan-size.validation.log`.
- `run-log append-failure` warning behavior.
- rc 0, 2, and 3 branches.
- display strings unless stale-reference lint requires a Python CLI label.

For post-plan validation, replace the invoke-validator wrapper call with:

```bash
env DESIGN_TMPDIR="$DESIGN_TMPDIR" LARCH_QUIET_DISABLE=1 python3 "$PLUGIN_ROOT/python/cli.py" plan validate --plan-file "$DESIGN_TMPDIR/plan.txt" --design-tmpdir "$DESIGN_TMPDIR"
```

Preserve:

- `set +e` capture.
- `VALIDATE_*` KV parsing from captured stdout.
- `VALIDATE_LOG_FILE` behavior.
- log copy behavior to `$DESIGN_TMPDIR/validate-plan-commands.log`.
- stable log path behavior when no design tmpdir is available.
- `defects-found` and infrastructure-failure handling.
- composed-plan source-kind behavior where this script validates composed plans.
- the retired wrapper behavior where defects are represented by `VALIDATE_STATUS`, not by an infrastructure-failure rc.

### UPDATED: skills/design/scripts/design-publish.sh

Replace the Step 5c composed-plan validator wrapper call with:

```bash
env DESIGN_TMPDIR="$DESIGN_TMPDIR" LARCH_QUIET_DISABLE=1 python3 "$PLUGIN_ROOT/python/cli.py" plan validate --plan-file "$DESIGN_TMPDIR/composed-plan.md" --source-kind composed --design-tmpdir "$DESIGN_TMPDIR"
```

Preserve:

- existing `set +e` capture.
- `VALIDATE_STATUS` parsing from captured stdout.
- `VALIDATE_*` KV parsing.
- `VALIDATE_LOG_FILE` behavior.
- log copy behavior to `$DESIGN_TMPDIR/validate-plan-commands.log`.
- stable log path behavior when no design tmpdir is available.
- `defects-found` exit 4 behavior.
- infrastructure-failure branches.
- composed-plan Tier 3 skip semantics.

### UPDATED: skills/design/scripts/design-step-validator-autofix.sh

Cut auto-fix execution to:

```bash
python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" plan auto-fix-commands ...
```

Preserve:

- cycle key behavior.
- `_autofix_attempted` marker.
- accepted `AUTOFIX_STATUS` values.
- fallback to operator prompt.
- log hash evidence key.
- Gate B snapshot/dedup coupling for `plan.txt` targets through the Python auto-fix implementation.
- `ORIGINAL_VALIDATE_LOG_FILE` preservation based on the stable `plan validate` log contract.
- `REVALIDATE_LOG_FILE` preservation based on the stable `plan validate` log contract.

### UPDATED: skills/design/scripts/design-step2b-postplan.sh

No behavioral rewrite beyond call-site cleanup if needed.

Verify it continues to call `design-postplan-emit.sh`, which now owns Python plan-size and plan validation calls.

### UPDATED: skills/design/scripts/design-step2b5.sh

Cut direct plan-size call to:

```bash
env LARCH_QUIET_DISABLE=1 python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" plan check-size --design-tmpdir "$DESIGN_TMPDIR"
```

Keep stdout parsing and rc branches unchanged.

### UPDATED: skills/design/scripts/review-design-step3-loop.sh

Cut the default revision waterfall call to the Python CLI while preserving the override contract.

Keep the environment override:

```bash
RUN_STEP3_REVISE_PLAN_WITH_WATERFALL_SH
```

Required behavior:

- If `RUN_STEP3_REVISE_PLAN_WITH_WATERFALL_SH` is set, invoke that override exactly as the current loop expects.
- If it is unset, invoke:

```bash
python3 "$PLUGIN_ROOT/python/cli.py" plan revise-waterfall ...
```

Keep:

- phase markers.
- snapshot restore behavior.
- `--patch-format file-replacement`.
- round metadata refresh after `revise.env` appears.
- Gate B post-apply flow.
- compatibility with existing Step 3 loop harness stubs that set `RUN_STEP3_REVISE_PLAN_WITH_WATERFALL_SH`.

### UPDATED: skills/design/scripts/gate-b-dedup-plan.sh

Replace sourced optional-trailer helper usage with direct Python CLI calls.

Keep the script itself in bash.

Required replacements:

- Snapshot keys:

```bash
python3 "$PLUGIN_ROOT/python/cli.py" plan optional-trailers snapshot-keys --plan-file "$plan_path" --output "$TRAILER_KEYS_FILE"
```

- Snapshot values:

```bash
python3 "$PLUGIN_ROOT/python/cli.py" plan optional-trailers snapshot-values --plan-file "$plan_path" --output "$TRAILER_KEYS_FILE.values"
```

- Validate keys:

```bash
python3 "$PLUGIN_ROOT/python/cli.py" plan optional-trailers validate-keys --plan-file "$plan_path" --keys-file "$TRAILER_KEYS_FILE"
```

- Validate values:

```bash
python3 "$PLUGIN_ROOT/python/cli.py" plan optional-trailers validate-values --plan-file "$plan_path" --values-file "$TRAILER_KEYS_FILE.values"
```

Preserve `--snapshot-trailers` composite behavior:

- Write both `$TRAILER_KEYS_FILE` and `$TRAILER_KEYS_FILE.values` before exit 0.
- Match the old bash helper contract that created the values sibling during snapshot mode.
- Keep `test-gate-b-dedup-plan.sh` expectations intact.

Reimplement `dedup_plan_preserve_optional_trailers` behavior locally before deleting `lib-plan-optional-trailers.sh`:

- Snapshot optional trailer values before dedup.
- Run `dedup-plan-lines.py` as the dedup engine.
- Validate optional trailer values after dedup with the Python CLI.
- Restore the original plan on dedup failure.
- Restore the original plan on optional-trailer validation failure.
- Preserve existing breadcrumb files, messages, and exit 1 or 2 semantics.
- Avoid moving dedup ownership into `plan_quality.py`.

### UPDATED: scripts/run-step1-plan-log.sh

Cut composer invocation to the Python CLI.

Default execution must not point at the retired composer path and must not guard that path with `[[ -x "$COMPOSE_SH" ]]`.

Required default call:

```bash
python3 "$PLUGIN_ROOT/python/cli.py" plan compose-goals-test --plan-file "$PLAN_FILE" --goal-text "$GOAL_TEXT"
```

Keep:

- run-id resolution.
- output temp file and atomic move.
- run-log write behavior.

Override handling:

- Keep an override only if survivor tests still need injection.
- If kept, rename it to a CLI command override or make it replace the full Python command.
- Do not keep `RUN_STEP1_COMPOSE_SH` pointing at an absorbed shell script.
- Do not require the retired shell script to be executable before the Python default path runs.

### UPDATED: scripts/relevant-checks.sh

Replace retired path triggers with surviving Python/module/test paths.

Examples:

- Changes to `python/plan_quality.py` or `python/test_plan_quality.py` should select plan-quality pytest and affected harness targets.
- Changes to `review-design-step3-loop.sh` should still select revision waterfall coverage.
- Changes to `design-postplan-emit.sh` and `design-publish.sh` should select their integration harnesses.
- Changes to `design-driver.sh` should select the design driver harness, including the `PLUGIN_ROOT` fallback case.
- Changes to `gate-b-dedup-plan.sh` should select Gate B dedup coverage.
- Changes to `scripts/run-step1-plan-log.sh` should select the run-step1 plan-log harness.
- Remove triggers that point to deleted shell scripts.
- Changes to Step 3 loop override compatibility should select:
  - `test-review-design-step3-loop.sh`
  - `test-design-pause-resume.sh`
  - `scripts/test-design-multi-round-integration.sh`

### UPDATED: Makefile

Keep target names where practical to avoid shard churn.

Retarget fully replaced shell harness targets to focused pytest selections from `python/test_plan_quality.py`.

Affected targets include:

- `test-check-plan-size`
- `test-parse-plan-commands`
- `test-validate-plan-commands`
- `test-trailer-helpers`
- `test-compose-plan-goals-test`
- `test-revise-plan-with-waterfall`
- `test-invoke-plan-validator`
- `test-auto-fix-plan-commands`

Example shape:

```make
test-parse-plan-commands:
	python3 python/cli.py timing harness-mark --label $@ -- pytest -q python/test_plan_quality.py -k parse_plan_commands
```

Update `.PHONY` and shard memberships if any target is removed instead of retargeted.

Keep survivor integration targets for:

- postplan emit.
- publish.
- design driver.
- Gate B dedup.
- Step 3 loop.
- pause/resume.
- multi-round integration.
- run-step1 plan-log.

### UPDATED: survivor shell harnesses

Update surviving integration harness stubs and assertions so they intercept Python CLI calls, not retired shell scripts.

Affected harness areas:

- `test-design-postplan-emit.sh`
  - Stub `python3 ... python/cli.py plan check-size`.
  - Stub `env ... python3 ... python/cli.py plan validate`.
  - Assert `VALIDATE_LOG_FILE` is parsed and propagated.
  - Assert the expected `$DESIGN_TMPDIR/validate-plan-commands.log` copy path where applicable.
  - Preserve coverage of rc branches, validation status branches, and log handling.
- `test-design-publish.sh`
  - Stub `env ... python3 ... python/cli.py plan validate --source-kind composed`.
  - Assert `VALIDATE_LOG_FILE` is parsed and propagated.
  - Preserve `defects-found` exit 4 and infrastructure-failure assertions.
- `test-design-driver.sh`
  - Update validation command expectations to the Python CLI dispatcher.
  - Add coverage where `CLAUDE_PLUGIN_ROOT` is unset.
  - Assert `design-driver.sh` bootstraps `PLUGIN_ROOT` from its checkout root.
  - Assert the validation command targets `$PLUGIN_ROOT/python/cli.py`, not `/python/cli.py`.
  - Preserve inherited `DESIGN_TMPDIR` behavior.
- `test-gate-b-dedup-plan.sh`
  - Assert `--snapshot-trailers` writes the keys file and `.values` sibling before dedup.
  - Assert the local dedup preserve path snapshots, restores, and validates values through the Python CLI.
- `test-run-step1-plan-log.sh`
  - Update composer stubs and expected tool names.
  - Assert the default path invokes `python3 "$PLUGIN_ROOT/python/cli.py" plan compose-goals-test`.
  - Assert no executable guard for the absorbed composer blocks the Python path.
  - Assert any retained override replaces the CLI command without naming the retired shell composer.
- `test-review-design-step3-loop.sh`
  - Assert the default revision waterfall path is the Python CLI.
  - Assert `RUN_STEP3_REVISE_PLAN_WITH_WATERFALL_SH` still overrides the default.
- `test-design-pause-resume.sh`
  - Update Step 3 stubs so they still use `RUN_STEP3_REVISE_PLAN_WITH_WATERFALL_SH`.
- `scripts/test-design-multi-round-integration.sh`
  - Update Step 3 stubs so they still use `RUN_STEP3_REVISE_PLAN_WITH_WATERFALL_SH`.
- Any remaining harness that asserts the old auto-fix, invoke-validator, composer, or check-size script paths.

### UPDATED: python/migrated-scripts.tsv

Append every retired script, harness, `.md` sibling, awk file, and fixture path that is deleted.

Use the tracking issue id for this migration.

Retire at least:

- plan command parser shell, docs, awk, fixtures, and harnesses.
- plan command validator shell, docs, fixtures, and harnesses.
- validate-plan wrapper and docs.
- invoke-validator wrapper and docs.
- plan-size shell.
- optional trailer shell, awk, docs, and harnesses.
- revision waterfall shell, docs, and harnesses.
- auto-fix shell, docs, and harnesses.
- plan-goals composer shell, docs, and harnesses.

Do not append `lib-drift-baseline.sh`.

Do not append `skills/design/scripts/check-plan-size.md` if that doc is retained and updated as the plan-size contract authority.

### UPDATED: agent-lint.toml

Update S030 pins and any related script pins that name absorbed or deleted surfaces.

Repoint or remove pins for retired plan-quality scripts and harnesses, including parser, validator, invoke-validator, plan-size, revision waterfall, auto-fix, and plan-goals composer surfaces.

Preferred replacements:

- `python/plan_quality.py`
- `python/test_plan_quality.py`
- surviving integration harnesses that still exercise shell call sites, such as postplan, publish, design driver, Gate B dedup, Step 3 loop, pause/resume, multi-round integration, and run-step1 plan-log harnesses.

Ensure `make agent-lint` does not require deleted files.

### UPDATED: skills/shared/topology.tsv

Change the plan-command validation topology authority from the retired validator script to the new Python plan-quality surface.

Use the new authority path that best matches the runtime owner.

Preferred authority:

- `python/plan_quality.py`

Keep topology IDs and descriptions stable unless the authority semantics require a small label update.

### UPDATED: .claude/rules/topology-generation.md

Update topology-generation rule paths if they reference the retired plan validator authority.

Keep the generated topology process unchanged.

### UPDATED: docs/topology.md

Regenerate topology docs after `skills/shared/topology.tsv` changes.

Verify generated rows no longer point the plan-command validator at a retired runtime authority.

### UPDATED: docs/python-migration.md

Add a decision-log entry for the plan-quality migration.

Mention:

- the `plan` domain verbs.
- no shims.
- `lib-drift-baseline.sh` remains deferred.
- plan-size inlines only the minimal baseline env semantics it needs.
- `plan validate` preserves `VALIDATE_LOG_FILE` by copying to `$DESIGN_TMPDIR/validate-plan-commands.log` when possible, else by emitting a stable temp log.
- surviving bash callers now invoke Python CLI directly.
- `design-driver.sh` bootstraps `PLUGIN_ROOT` for checkout execution when `CLAUDE_PLUGIN_ROOT` is unset.
- Step 3 keeps `RUN_STEP3_REVISE_PLAN_WITH_WATERFALL_SH` as an override while changing the default implementation to Python.
- `scripts/run-step1-plan-log.sh` now defaults directly to `plan compose-goals-test` without an absorbed shell executable guard.
- shell harnesses were replaced by `python/test_plan_quality.py` where absorbed, with survivor harnesses retained for shell call sites.

Avoid retired full-path literals after they enter `migrated-scripts.tsv` unless the linter excludes this doc or the implementation builds those strings safely.

### UPDATED: docs/linting.md

Replace shell harness descriptions with pytest-backed target descriptions.

Update:

- parser plan-command validation target text.
- validator target text.
- plan-size target text.
- revision waterfall target text.
- auto-fix target text if present.
- invoke-validator target text if present.
- compose plan-goals test target text if present.
- run-step1 plan-log coverage that verifies the Python composer default and no retired executable guard.
- agent-lint pin expectations if this doc names the migrated surfaces.
- survivor Step 3 loop coverage that preserves the override contract.
- design driver coverage that preserves checkout `PLUGIN_ROOT` bootstrap behavior.

Avoid stale retired path literals once the manifest is updated.

### UPDATED: SECURITY.md

Update security-relevant references to migrated validator and auto-fix surfaces.

Keep the change minimal.

Replace absorbed script names with the new Python CLI plan verbs where applicable:

- `python/cli.py plan validate`
- `python/cli.py plan validate-commands`
- `python/cli.py plan auto-fix-commands`
- related Tier 2 or Tier 3 plan-validation wording.

Preserve existing trust-boundary semantics:

- plan content remains untrusted.
- dry-run validation remains constrained.
- captured output remains redacted.
- composed-plan Tier 3 skip remains intentional.
- validator logs remain evidence artifacts and must not be silently dropped.

### UPDATED: skills/design/SKILL.md

Update runtime surface references for Step 2b, Step 2b.5, Step 3, auto-fix, and Step 1 plan-log where mentioned.

Replace absorbed script references with:

- `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" plan validate`
- `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" plan check-size`
- `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" plan revise-waterfall`
- `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" plan auto-fix-commands`
- `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" plan compose-goals-test`

Mention that Step 3 preserves `RUN_STEP3_REVISE_PLAN_WITH_WATERFALL_SH` as a test and integration override.

Keep user-facing behavior unchanged.

### UPDATED: skills/design/references/approval-gates.md

Update normative Gate B and Gate C references that still name absorbed script basenames.

Replace absorbed revision and validation surfaces with the Python CLI owners:

- `python/cli.py plan revise-waterfall`
- `python/cli.py plan validate`
- `python/cli.py plan validate-commands`
- `python/cli.py plan check-size`
- `python/cli.py plan auto-fix-commands`

Repoint the plan-size machine contract to `skills/design/scripts/check-plan-size.md` only after that doc is updated to describe the Python CLI owner.

Preserve:

- Gate B apply semantics.
- Gate B size-brake semantics.
- Gate C validation semantics.
- untrusted-plan trust-boundary wording.
- optional-trailer preservation requirements.
- composed-plan Tier 3 skip semantics.

### UPDATED: skills/design/references/plan-review.md

Update plan-review references that name absorbed revision waterfall, validation, or auto-fix script basenames.

Use Python CLI surface names:

- `python/cli.py plan revise-waterfall`
- `python/cli.py plan validate`
- `python/cli.py plan auto-fix-commands`

Preserve:

- reviewer-finding trust boundary.
- waterfall tier order.
- output path expectations under `$DESIGN_TMPDIR/plan-review/round-N/revise`.
- `revise.env` contract.
- Gate B handoff semantics.

### UPDATED: skills/design/references/design-driver.md

Update validation references to the Python `plan validate` surface.

Document the checkout bootstrap behavior:

- `CLAUDE_PLUGIN_ROOT` may be unset.
- `design-driver.sh` resolves `PLUGIN_ROOT` from the checkout root in that case.
- validation must target `$PLUGIN_ROOT/python/cli.py`, never `/python/cli.py`.

Preserve existing driver phase semantics and validation status handling.

### UPDATED: skills/design/scripts/check-plan-size.md

Keep this doc as the authoritative plan-size contract if it remains referenced by Gate B docs.

Repoint runtime authority to:

- `python/plan_quality.py`
- `python/cli.py plan check-size`

Preserve documented behavior:

- `PLAN_SIZE_STATUS` values.
- rc 0, 2, and 3 meanings.
- thresholds for plan body, `diff_lines`, and `diff_added`.
- `mechanical_churn: true` soft advisory behavior.
- invalid `mechanical_churn` failure before threshold checks.
- minimal drift-baseline env behavior.
- unreadable baseline handling and recovery semantics.
- no dependency on sourcing `lib-drift-baseline.sh`.

Do not describe the deleted shell script as the runtime authority.

### UPDATED: skills/design/scripts/design-postplan-emit.md

Update the contract doc to name the Python CLI plan-size and plan-validation surfaces.

Preserve documented rc behavior, validation status behavior, quiet-parent `LARCH_QUIET_DISABLE=1` capture requirement, and log behavior.

Document `plan validate` log behavior:

- With `DESIGN_TMPDIR`, `VALIDATE_LOG_FILE` points at `$DESIGN_TMPDIR/validate-plan-commands.log`.
- Without `DESIGN_TMPDIR`, `VALIDATE_LOG_FILE` points at a stable temp log that remains readable after the command exits.

### UPDATED: skills/design/scripts/design-publish.md

Update Step 5c composed-plan validation docs to name the Python CLI plan-validation surface.

Preserve documented publish validation status, exit 4 behavior, Tier 3 composed skip, quiet-parent `LARCH_QUIET_DISABLE=1` capture requirement, and log behavior.

Document the same `VALIDATE_LOG_FILE` behavior as postplan.

### UPDATED: skills/design/scripts/review-design-step3-loop.md

Update the happy-path description to use the Python revision waterfall command.

Keep Gate B dedup and postplan semantics unchanged.

Document that `RUN_STEP3_REVISE_PLAN_WITH_WATERFALL_SH` remains a supported override for tests and integration harnesses.

### UPDATED: scripts/run-step1-plan-log.md

Update the composer reference to the Python CLI verb.

Document that the default path invokes:

```bash
python3 "$PLUGIN_ROOT/python/cli.py" plan compose-goals-test --plan-file "$PLAN_FILE" --goal-text "$GOAL_TEXT"
```

Document that no retired composer executable guard is required for the default path.

Keep the batch contract unchanged.

### UPDATED: scripts/test-run-step1-plan-log.md

Update stale composer references and expected tool names if assertions include them.

Assert the Python default path and absence of the retired executable guard.

### UPDATED: AGENTS.md

Update canonical-source or runtime notes only if they mention retired plan-quality scripts.

Keep the change minimal.

## Retired files

Delete absorbed shell and awk files after call-site cutover and parity tests pass.

Delete parser fixtures only after pytest owns equivalent fixtures.

Suggested deletion groups:

- **Plan command parse/validate**
  - Parser shell, awk, docs, fixtures, and harness.
  - Validator shell, docs, fixtures, and harness.
  - Validate-plan wrapper and docs.
  - Invoke-plan-validator wrapper and docs after direct callers are cut over.
- **Plan size and optional trailers**
  - Check-size shell.
  - Keep and update `skills/design/scripts/check-plan-size.md` if Gate B docs continue to cite it as the machine contract.
  - Optional trailer shell, awk, docs.
  - Trailer helper harness scripts and docs.
- **Revision waterfall**
  - Revision shell and docs.
  - Cross-tree shell harness and docs.
- **Auto-fix**
  - Auto-fix shell and docs.
  - Shell harness.
- **Plan-goals composer**
  - Composer shell and docs.
  - Composer shell harness and docs.

Before deletion:

- Rehome Gate B dedup preserve orchestration into `gate-b-dedup-plan.sh`.
- Verify `--snapshot-trailers` writes the keys file and `.values` sibling.
- Verify `plan validate` emits stable `VALIDATE_LOG_FILE` paths with and without `DESIGN_TMPDIR`.
- Verify `design-driver.sh` can run validation from a checkout when `CLAUDE_PLUGIN_ROOT` is unset.
- Verify Step 3 loop override tests still pass with `RUN_STEP3_REVISE_PLAN_WITH_WATERFALL_SH`.
- Verify `scripts/run-step1-plan-log.sh` reaches Python `plan compose-goals-test` without checking a retired shell executable.
- Run targeted stale-reference grep, including basename-only absorbed script names.
- Update topology authority sources.
- Update `agent-lint.toml` pins.
- Update survivor harness stubs.
- Run `make lint-retired-scripts`.

## Edge cases

- **TSV compatibility**
  - Header and row order must match current fixtures.
  - Empty fields must remain tab-separated.
  - No quoting or JSON conversion.
- **Line numbers**
  - Parser `source_line` values are fixture-sensitive.
  - Preserve current line-number quirks, including fence-start and continuation behavior.
- **Shell-ish parsing**
  - Do not replace parser behavior with full shell execution.
  - Never evaluate plan content.
- **Help probes**
  - Scripts may print help to stderr.
  - Scripts may exit 1 or 2 for usage help.
  - Empty help output means skip flag checks, not a defect.
- **Validate-plan wrapper contract**
  - Defects are surfaced through `VALIDATE_STATUS=defects-found`.
  - Preserve the retired wrapper rc behavior for defects so downstream status parsing still runs.
  - Infrastructure failures remain nonzero.
  - `VALIDATE_LOG_FILE` must always point at a readable stable log.
  - With `DESIGN_TMPDIR`, the log path must be `$DESIGN_TMPDIR/validate-plan-commands.log`.
  - Without `DESIGN_TMPDIR`, the temp log must outlive command `EXIT` cleanup.
- **Plugin-root bootstrap**
  - `design-driver.sh` must define `PLUGIN_ROOT` before invoking `python/cli.py`.
  - `CLAUDE_PLUGIN_ROOT` may be unset when the script runs from a checkout.
  - The fallback path must resolve to the repository root, not `/`.
- **Run-step1 composer**
  - Default Step 1 plan-log composition must invoke `plan compose-goals-test`.
  - It must not require an absorbed shell composer to exist or be executable.
  - Any retained override must replace the full CLI command or otherwise avoid retired script paths.
- **Tier 3 safety**
  - Reject unsafe tokens before dry-run.
  - Keep dry-run environment minimal.
  - Preserve redaction of captured output.
- **Quiet parent capture**
  - `design-postplan-emit.sh` and `design-publish.sh` call quiet init before capturing validator output.
  - Wrap captured `plan validate` and plan-size calls with `LARCH_QUIET_DISABLE=1`.
  - Pass or preserve `DESIGN_TMPDIR` for validation log copying.
  - Register contract-emitting plan verbs in `_MACHINE_STDOUT_KEYS`.
- **Composed-plan validation**
  - Preserve Tier 3 skip for composed plans.
  - Preserve `VALIDATE_*` stdout contracts.
  - Preserve `VALIDATE_LOG_FILE` evidence behavior.
- **Optional trailers**
  - `diff_added: 08` and `09` are absent metadata.
  - Duplicate strict trailers count toward metadata-block line count.
  - `mechanical_churn` accepts only lowercase `true` and `false`.
  - Invalid `mechanical_churn` must fail plan-size before threshold calculations.
  - Gate B `--snapshot-trailers` must write both keys and `.values`.
  - Gate B dedup must restore the original plan if dedup or value validation fails.
- **Plan-size drift**
  - Do not silently remove drift advisory behavior.
  - Do not source the drift bash library from Python.
  - Inline only the minimal baseline env behavior required for existing outputs.
  - Keep `skills/design/scripts/check-plan-size.md` aligned with Python behavior if the doc remains authoritative.
- **Revision waterfall**
  - A bad patch must restore the original plan.
  - A failed emit-plan gate must restore the original plan.
  - Unified-diff headers must target only `plan.txt`.
  - File-replacement fallback must still require `diff_lines`.
  - Optional trailer keys must survive revisions.
  - `RUN_STEP3_REVISE_PLAN_WITH_WATERFALL_SH` must still override the default implementation.
- **Auto-fix**
  - External agents may mutate non-target tmpdir files.
  - Restore or fail according to existing guard behavior.
  - A passing revalidation alone must not hide dirty-tree, optional-trailer, dedup, or guard failures.
  - Keep Gate B snapshot/dedup coupling for `plan.txt`.
  - Preserve stable original and revalidation log evidence files.
- **Stale references**
  - Once a path enters `migrated-scripts.tsv`, tests and docs must not include exact retired path literals unless the linter allows them.
  - Also search basename-only absorbed script names because migration lint may not catch them.
- **Topology**
  - Do not leave generated docs or topology rules pointing at retired validator authorities.
- **Agent lint**
  - Do not leave S030 pins pointing at deleted scripts or harnesses.
- **Security docs**
  - Do not leave security docs naming retired validation or auto-fix script surfaces.

## Failure modes

- **Parser drift** can produce false validator defects. Golden TSV parity should catch this.
- **CLI quiet-mode drift** can break orchestrator parsing. Test fd-3 and stdout behavior.
- **Quiet-parent validation drift** can make `VALIDATE_*` KVs disappear from captured stdout. Use `LARCH_QUIET_DISABLE=1`.
- **Validate log drift** can break postplan evidence and auto-fix preservation. Test `VALIDATE_LOG_FILE` with and without `DESIGN_TMPDIR`.
- **Defects rc drift** can route command defects into infrastructure-failure branches. Preserve the validate-plan wrapper status model.
- **Plugin-root bootstrap drift** can make `design-driver.sh` invoke `/python/cli.py` or the wrong checkout. Test with `CLAUDE_PLUGIN_ROOT` unset.
- **Run-step1 composer guard drift** can fail Step 1 before Python runs if the default path still checks a deleted composer script.
- **Path guard regression** can let external agents edit outside `$DESIGN_TMPDIR`. Keep canonical path tests.
- **Revision restore failure** can leave a mutated plan after a rejected patch. Test restoration on each failure branch.
- **Step 3 override drift** can break loop, pause/resume, and multi-round harnesses that stub `RUN_STEP3_REVISE_PLAN_WITH_WATERFALL_SH`.
- **Postplan guard drift** can block Python plan-size validation if a retired shell executable guard remains.
- **Composed validation drift** can break publish if `design-publish.sh` still calls the retired wrapper.
- **Gate B trailer snapshot drift** can break `--snapshot-trailers` consumers if the `.values` sibling is missing.
- **Gate B dedup drift** can drop optional trailers or skip restoration if the library function is deleted before local orchestration exists.
- **Auto-fix dedup drift** can pass revalidation while losing optional trailers.
- **Normative doc drift** can leave `/design` loading Gate B or Gate C docs that still name absorbed script basenames.
- **Plan-size authority drift** can leave `check-plan-size.md` describing a deleted runtime.
- **Stale retired references** can fail `make lint-retired-scripts`. Basename-only references can survive that lint and still confuse runtime docs.
- **Agent-lint pin drift** can fail `make agent-lint` if S030 pins name deleted files.
- **Over-porting drift baseline** can expand scope. Keep `lib-drift-baseline.sh` deferred.
- **Security-doc drift** can leave stale validation surface names after the migration.

## Testing strategy

1. Run focused pytest during development:

```bash
pytest -q python/test_plan_quality.py
pytest -q python/test_cli.py
```

2. Run parity and survivor harness targets after Makefile retargeting:

```bash
make test-parse-plan-commands
make test-validate-plan-commands
make test-invoke-plan-validator
make test-check-plan-size
make test-trailer-helpers
make test-revise-plan-with-waterfall
make test-auto-fix-plan-commands
make test-compose-plan-goals-test
make test-run-step1-plan-log
make test-design-postplan-emit
make test-design-publish
make test-design-driver
make test-gate-b-dedup-plan
make test-plan-review-loop
```

3. Run Step 3 override and workflow survivor harnesses:

```bash
bash skills/design/scripts/test-review-design-step3-loop.sh
bash skills/design/scripts/test-design-pause-resume.sh
bash scripts/test-design-multi-round-integration.sh
```

4. Run migration, topology, and agent lint:

```bash
make lint-retired-scripts
make agent-lint
```

5. Run Python checks:

```bash
make py-lint
make py-test
```

6. Run repo-relevant checks:

```bash
bash scripts/relevant-checks.sh
```

7. Run full lint as required definition-of-done verification:

```bash
make lint
```

## Stale-reference sweep

Search after deletions and manifest updates for:

- retired script paths.
- retired `.md` paths.
- retired fixture paths.
- absorbed script basenames, even when no repo-relative path is present.
- `$SCRIPT_DIR/<retired-basename>` forms.
- `RUN_STEP3_REVISE_PLAN_WITH_WATERFALL_SH`
  - Keep only supported override uses in Step 3 loop and survivor tests.
- `RUN_STEP1_COMPOSE_SH`
  - Remove or rename unless it no longer points at the absorbed composer.
- `LARCH_AUTOFIX_VALIDATE_PLAN_SH`
- `LARCH_PLAN_OPTIONAL_TRAILERS_AWK`
- invoke-validator stubs and assertions in survivor harnesses.
- validate-plan log path assertions that still expect an unstable cleanup temp file.
- topology rows, topology rules, and generated topology docs that point at retired validator authorities.
- `agent-lint.toml` S030 pins that point at deleted scripts or harnesses.
- Gate B and Gate C docs that mention absorbed basenames.
- plan-review and design-driver docs that mention absorbed basenames.
- plan-size docs that describe a deleted shell script as runtime authority.
- security docs that mention retired validation or auto-fix script surfaces.

Keep only test override variables that still make sense with the Python CLI.

diff_added: 3005
diff_deleted: 4420
mechanical_churn: true
diff_lines: 7425

## Acceptance

- [ ] `python/plan_quality.py` importable; all public functions match bash behavior byte-for-byte on golden fixtures
- [ ] `python/cli.py plan parse-commands`, `validate-commands`, `validate`, `check-size`, `revise-waterfall`, `auto-fix-commands`, `optional-trailers`, `compose-goals-test` registered and callable
- [ ] `python/test_plan_quality.py` passes (`make py-test`)
- [ ] All absorbed bash/awk scripts deleted; all harnesses deleted; all fixtures either deleted or ported
- [ ] All consumer call sites cut over: `design-postplan-emit.sh`, `design-driver.sh`, `gate-b-dedup-plan.sh`, `review-design-step3-loop.sh`, `design-step-validator-autofix.sh`, `run-step1-plan-log.sh`, `design-step2b5.sh`
- [ ] Makefile targets retargeted to pytest; shard assignments updated if targets removed
- [ ] `python/migrated-scripts.tsv` updated with all retired paths
- [ ] `make lint-retired-scripts` passes
- [ ] `make py-lint` passes
- [ ] `bash scripts/relevant-checks.sh` passes
- [ ] Stale-reference sweep complete; no retired path literals survive in tracked files (except `CHANGELOG.md`, manifest itself, and linter exclusions)

diff_lines: 7425

## Test plan
(no test plan section in plan-file)
