# design-postplan-emit.sh

**Consumer**: `/design` Step 2b post-plan emit sequence and prompt-side re-emit sites.

**Callers**: `skills/design/SKILL.md` initial Step 2b (`--with-plan-size --snapshot-original`), Gate A after-discussion re-emit (`--with-plan-size`), `skills/design/references/approval-gates.md` Gate B shared post-apply (`--with-plan-size`), and `skills/design/references/discussion-rounds.md` post-plan Round 2 (`--with-plan-size`). Retained callers still use standalone `check-plan-size.sh` via Step 2b.5 / `plan-review-loop.sh`.

## Argv

| Flag | Required | Notes |
|------|----------|-------|
| `--design-tmpdir PATH` | yes | Canonicalized with `cd … && pwd -P` |
| `--snapshot-original` | no | Enables the initial HARD `plan.txt-original` write-once snapshot |
| `--with-plan-size` | no | Merged mode: run `check-plan-size.sh` after successful validation; action exit codes; display-only FD 3 |

Only the initial Step 2b call passes `--snapshot-original`. Re-emit sites suppress the HARD snapshot. Validation is unconditional for all sites.

## Responsibilities

1. Resolve `CLAUDE_PLUGIN_ROOT`, export `DESIGN_TMPDIR`, read `partition_requested` from `run-params.json` (`json_boolean_or_sed` for bare `true`/`false` without `jq`).
2. Pause checkpoint before each internal step. **`--with-plan-size`**: exit **11** after writing result env (orchestrator `exec`s `design-pause-save.sh`). **Legacy**: `exec` pause-save from the driver.
3. Pipe `ACTION=EMIT_PLAN` to `design-driver.sh`.
4. Optional HARD snapshot when `--snapshot-original`.
5. Run `invoke-plan-validator.sh` unconditionally.
6. **`--with-plan-size`**: after validation succeeds without defects, run `check-plan-size.sh` with `LARCH_QUIET_DISABLE=1`; parse stdout only; stderr to a sidecar on failure paths.

## Result env (`.design-postplan-emit-result.env`)

**Legacy mode** mirrors mandatory KVs to stdout via `emit_kv`.

**Merged mode** writes KVs only to the result env. Display lines use `emit` on FD 3 (no `emit_kv` / no `WARN=` leakage on display). If the result env cannot be created/truncated/written (including symlink refusal), exit **1** with a display diagnostic — no stdout-KV fallback.

Allowlisted keys for orchestrator reads (never `source`):

- `POSTPLAN_EMIT_STATUS`, `EMIT_PLAN_STATUS`, `DIFF_LINES`, `SNAPSHOT_STATUS`
- `VALIDATE_STATUS`, `VALIDATE_DEFECT_COUNT`, `VALIDATE_SKIPPED_COUNT`, `VALIDATE_UNSAFE_TOKEN_COUNT`, `VALIDATE_LOG_FILE`
- `PLAN_SIZE_STATUS`, `HARD_TRIGGER_FIRED`, `TRIGGER_REASONS`, `PLAN_LINES`, `DIFF_ADDED`, `DIFF_DELETED`, `MECHANICAL_CHURN`, `SOFT_ADVISORY`, `PARTITION_REQUESTED`
- `WARN` (repeatable)

## Exit codes

### Legacy (no `--with-plan-size`)

| Code | When |
|------|------|
| `0` | Success, including `VALIDATE_STATUS=defects-found` |
| `1` | `missing-diff-lines`, `emit-failed`, `snapshot-failed`, `validate-driver-failed` |
| `2` | Argv / configuration / precondition error |

### Merged (`--with-plan-size`)

| Code | When |
|------|------|
| `0` | Clean under thresholds; or plan-size rc 2/3 warn-and-continue (nonfatal) |
| `1` | Emit/snapshot/validator infrastructure failure (specific diagnostic emitted on FD 3 before exit) |
| `2` | Argv / configuration error |
| `10` | `VALIDATE_STATUS=defects-found` (plan-size skipped) |
| `11` | Pause requested (orchestrator runs `design-pause-save.sh`) |
| `12` | Hard trigger (`HARD_TRIGGER_FIRED=true`; hard wins over partition) |
| `13` | `partition_requested=true` without hard trigger |

**Precedence**: defects → plan-size skipped; hard → partition when both apply.

## Plan-size nonfatal failures (merged)

On `check-plan-size.sh` rc **2** or **3**: capture stdout+stderr to `check-plan-size.validation.log`, append via `append-tool-failure.sh` (helper stdout/stderr suppressed), emit display `WARN`, exit **0** (under-threshold continuation).

## Soft advisory display

When `SOFT_ADVISORY=true` and `HARD_TRIGGER_FIRED=false`, emit mechanical-churn advisory then exit `0`. When both soft advisory and hard trigger, emit advisory plus hard-section preamble before exit **12**.

## Classification warnings (#3441)

`read-design-classification.sh` stderr is captured into `WARN` result-env lines and replayed via display `emit` (not `WARN=` tokens on FD 3).

## Edit in sync

Update together: `skills/design/SKILL.md`, `references/approval-gates.md`, `references/discussion-rounds.md`, `references/flags.md`, `references/decompose-panel.md`, `check-plan-size.md`, `test-design-postplan-emit.sh`, `scripts/test-design-structure.sh`, and `Makefile`.

## Harness

`skills/design/scripts/test-design-postplan-emit.sh` (`make test-design-postplan-emit`).
