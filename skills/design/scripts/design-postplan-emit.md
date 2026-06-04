# design-postplan-emit.sh

**Consumer**: `/design` Step 2b post-plan emit sequence and prompt-side re-emit sites.

**Callers**: `skills/design/SKILL.md` initial Step 2b, Gate A re-entry rewrites, `skills/design/references/approval-gates.md` Gate B shared post-apply pipeline, and `skills/design/references/discussion-rounds.md` post-plan Round 2 revisions.

## Argv

| Flag | Required | Notes |
|------|----------|-------|
| `--design-tmpdir PATH` | yes | Canonicalized with `cd … && pwd -P` |
| `--snapshot-original` | no | Enables the initial HARD `plan.txt-original` write-once snapshot |

Only the initial Step 2b call passes `--snapshot-original`. Re-emit sites suppress the HARD snapshot. Validation runs on every emit.

## Responsibilities

1. Resolve `CLAUDE_PLUGIN_ROOT`, export `CLAUDE_PLUGIN_ROOT` and `DESIGN_TMPDIR`. Snapshot eligibility is resolved through `read-design-classification.sh`.
2. Pause checkpoint before each internal step. If `.pause-requested` exists, `_postplan_resolve_issue` uses prelude-sourced `ISSUE_NUMBER` or `source-env.sh` (`export ISSUE_NUMBER=...`), `_postplan_resolve_repo` reads `export REPO=...` from `source-env.sh` without sourcing it, and then the driver `exec`s `design-pause-save.sh` with `--repo` only when `REPO` is non-empty.
3. Pipe `ACTION=EMIT_PLAN` to `design-driver.sh` and parse `EMIT_PLAN_STATUS` / `DIFF_LINES`.
4. When `--snapshot-original` and `read-design-classification.sh` resolves `design_classification=HARD`, run `snapshot-plan-round.sh write-original --design-tmpdir DIR`; otherwise emit a skipped snapshot status.
5. Run `invoke-plan-validator.sh DIR/plan.txt` on every successful emit.
6. Stop before Step 2b.5 and before the prompt-side `AskUserQuestion` for plan-command validator defects.

The driver wraps existing helpers; it does not duplicate `emit-plan.sh`, `snapshot-plan-round.sh`, or validator logic.

## Result env (`.design-postplan-emit-result.env`)

Allowlist / stdout KV contract:

- `POSTPLAN_EMIT_STATUS`
- `EMIT_PLAN_STATUS`
- `DIFF_LINES`
- `SNAPSHOT_STATUS`
- `VALIDATE_STATUS`
- `VALIDATE_DEFECT_COUNT`
- `VALIDATE_SKIPPED_COUNT`
- `VALIDATE_UNSAFE_TOKEN_COUNT`
- `VALIDATE_LOG_FILE`
- `WARN` (optional, repeatable)

Default/status matrix:

| Key | Initial default | EMIT failure | Snapshot skipped | After snapshot | Success |
|-----|-----------------|--------------|------------------|-------------------|---------|
| `POSTPLAN_EMIT_STATUS` | `pending` | `missing-diff-lines` or `emit-failed` | unchanged | unchanged | `ok` |
| `EMIT_PLAN_STATUS` | `not-run` | parsed value | parsed value | parsed value | parsed value |
| `DIFF_LINES` | empty | empty unless emitted | parsed value | parsed value | parsed value |
| `SNAPSHOT_STATUS` | `not-run` | `not-run` | `skipped-not-hard` or `skipped-suppressed` | current value | `taken`, `preserved`, or skipped |
| `VALIDATE_STATUS` | `not-run` | `not-run` | `not-run` | parsed status | parsed status |
| Validator counts/log | `0` / empty | `0` / empty | `0` / empty | `0` / empty | parsed values |

## Exit codes

| Code | When |
|------|------|
| `0` | Success, including `VALIDATE_STATUS=defects-found` |
| `1` | Operation failure: `missing-diff-lines`, `emit-failed`, `snapshot-failed`, or `validate-driver-failed` |
| `2` | Argv / configuration / precondition error |

`POSTPLAN_EMIT_STATUS=missing-diff-lines` is the orchestrator repair route for `plan.txt`. `VALIDATE_STATUS=defects-found` is not a driver failure; the orchestrator fires the shared Plan command validator failure body.

## `set -e` child-call invariant

The script runs under `set -euo pipefail`, but every child helper is called inside a local `set +e` capture. A child non-zero exit must never skip `_postplan_write_result_and_emit`. On every `0` / `1` exit path, `_postplan_write_result_and_emit` writes the result env and mirrors the mandatory KVs to stdout so the orchestrator can fall back to stdout when the file is absent or refused as a symlink.

## Orchestrator handoff

Prompt-side callers use the same pattern as `design-route.sh` and `design-publish.sh`:

1. `set +e` capture to `_postplan_out` and `_postplan_rc`, then `set -e`.
2. Initialize every allowlisted variable to empty before parsing.
3. Prefer `$DESIGN_TMPDIR/.design-postplan-emit-result.env` when it exists and is not a symlink; never `source` it.
4. Merge stdout from `_postplan_out` only for still-unset allowlisted keys so file-first values win. Replay `WARN=` lines from stdout only when the file parse did not succeed.
5. When `_postplan_rc` is `0` or `1`, abort if routing keys such as `POSTPLAN_EMIT_STATUS` or `VALIDATE_STATUS` remain empty after the merge.

## Edit in sync

Update together: `skills/design/SKILL.md` Step 2b and Gate A re-entry prose, `skills/design/references/approval-gates.md`, `skills/design/references/discussion-rounds.md`, `skills/design/references/flags.md`, `skills/design/scripts/test-design-postplan-emit.sh`, `scripts/test-design-structure.sh`, and `Makefile`.

## Harness

`skills/design/scripts/test-design-postplan-emit.sh` (Makefile target: `test-design-postplan-emit`).

## Snapshot classification gate

`--snapshot-original` resolves eligibility with `${CLAUDE_PLUGIN_ROOT}/scripts/read-design-classification.sh` against `run-params.json`. Missing, unreadable, or invalid `design_classification` resolves to HARD for snapshot purposes. Legacy `workflow_path` cannot suppress the original snapshot when classification resolves HARD; SIMPLE classification emits `SNAPSHOT_STATUS=skipped-not-hard`.

## Classification warnings

Classification warnings from `read-design-classification.sh` are operator-visible under default quiet mode. `WARN_LINES=()` is initialized before the classification read, stderr from the classification helper is captured, and non-empty warning lines are emitted as repeatable `WARN=` stdout KVs by `_postplan_write_result_and_emit`. If the helper exits non-zero without stderr, the driver appends a synthetic `WARN=` noting the non-zero exit and the HARD fallback. The stdout classification value and `HARD` fallback semantics are unchanged.
