# design-init-runparams.sh

**Consumer**: `/design` Step 0b — post-gate phase driver (tier-derived `run-params.json`, env refresh, `[DESIGNING]` rename, router-flag jq-merge).

**Caller**: `skills/design/SKILL.md` Step 0b after clarify / already-planned / cancel gates clear on `ROUTE=proceed` (orchestrator writes `feature-description.txt` first).

## Argv

| Flag | Required | Notes |
|------|----------|-------|
| `--design-tmpdir PATH` | yes | `cd … && pwd -P` |
| `--issue N` | yes | Positive integer |
| `--session-id STR` | yes | No embedded newline/CR |
| `--claude-pid N` | yes | Positive integer |
| `--classification SIMPLE\|HARD` | yes | From orchestrator tier resolution |
| `--partition-requested true\|false` | yes | |
| `--brainstorm-requested true\|false` | yes | Includes title-prefix auto-enable |
| `--approve-requested true\|false` | yes | Public `--per-round-approval` (restores per-round Gate B prompt) |
| `--skip-approve-requested true\|false` | yes | Public `--skip-approve`/`-s` (auto-approves Step 1d.7 outline and Gate C final plan) |
| `--repo OWNER/REPO` | no | Forwarded for `tracking-issue-write.sh` rename |

## Responsibilities

1. Tier map: SIMPLE → `sketch_budget=0`, `workflow_path=SIMPLE`; HARD → `sketch_budget=3`, `workflow_path=HARD`; `source=caller-forwarded`.
2. **Single** `write-design-current-env.sh` **before** `[DESIGNING]` rename; child diagnostics preserve quiet mode with the same `[ "${LARCH_QUIET_PID:-}" = "$$" ]` / FD 4 bridge (`>/dev/null 2>&4` only under quiet, `>/dev/null` otherwise); non-zero → detailed `larch_err` banner, `INIT_STATUS=env-refresh-failed`, exit `1`.
3. `tracking-issue-write.sh rename --state designing` with `${REPO:+--repo}`; rename failure → `WARN=`.
4. `write-run-params.sh` → `run-params.json`; non-zero → detailed `larch_err` contract-drift banner including `contract drift`, `aborting before silent tier downgrade`, and `bash python/test_session_env.py`, then `INIT_STATUS=contract-drift`, exit `1`.
5. Full router-flag jq-merge block (guard, `mktemp` paths, filter, `mv`, `run-log append-failure` on jq failure, both warning strings). The guard and jq filter cover `partition_requested`, `brainstorm_requested`, `approve_requested`, and `skip_approve_requested` so any router flag survives subshell boundaries (`$merge_p` / `$merge_b` / `$merge_a` / `$merge_s` OR-merge arms).

## Result env (`.design-init-runparams-result.env`)

Allowlist: `INIT_STATUS` (`ok` \| `contract-drift` \| `env-refresh-failed`), `RENAMED`, `RUN_PARAMS_PATH`, `DESIGN_CLASSIFICATION`, `WARN`.

## Exit codes

| Code | When |
|------|------|
| `0` | Success |
| `1` | `write-design-current-env.sh` failure (`INIT_STATUS=env-refresh-failed`) or `write-run-params.sh` contract drift (`INIT_STATUS=contract-drift` in result env) |
| `2` | Argv / repo config error |

## LLM boundary

Stops before Step 0c; does not write `feature-description.txt` (orchestrator-owned). Contract-drift and env-refresh-failed operator messages are driver-owned and printed via `larch_err`.

## Idempotency

Rename and run-params writes are idempotent on replay.

## Partial-state retry

Rename runs before `write-run-params.sh`. If rename succeeds but `write-run-params.sh` exits non-zero (`INIT_STATUS=contract-drift`), the issue title may already show `[DESIGNING]` without a fresh `run-params.json`. Retries must re-run the full driver from Step 0b; do not route from a stale or missing `run-params.json` until `INIT_STATUS=ok` and the file exist.

## Orchestrator handoff

The result-env schema is unchanged: `.design-init-runparams-result.env` carries `INIT_STATUS`, `RENAMED`, `RUN_PARAMS_PATH`, `DESIGN_CLASSIFICATION`, and `WARN` records.

`skills/design/SKILL.md` captures producer stdout to a temp file and reads `.design-init-runparams-result.env` through `scripts/read-result-env.sh`. The orchestrator allowlists `INIT_STATUS`, `RENAMED`, `RUN_PARAMS_PATH`, and `DESIGN_CLASSIFICATION`, then sources only the helper-generated safe env file.

Producer stdout is used only as a narrow compatibility fallback when the primary result-env is missing, symlinked, or non-regular. A regular result-env remains the source of truth; fallback does not mask malformed regular result-env contents. If fallback is used because the result-env is symlinked, `read-result-env.sh` preserves the operator-visible symlink-refusal breadcrumb before parsing fallback.

WARN/ERROR replay is handled by `read-result-env.sh`. Result-env and fallback stdout parsing use the same grammar: blank lines ignored, nonblank no-`=` lines rejected, and first-`=` splitting with embedded `=` preserved in values.

Exit `2` / unexpected non-zero aborts remain orchestrator-owned. `_init_rc=1` may carry `INIT_STATUS=contract-drift` or `INIT_STATUS=env-refresh-failed`; the driver has already printed detailed `larch_err` diagnostics for both statuses, so the orchestrator propagates status + exit with only the short generic abort.

## Harness

`scripts/test-design-structure.sh` (env-before-rename line-order, jq-merge greps, `read-result-env.sh` handoff shape); `scripts/test-step0b-router-flag-recovery.sh` replicates jq-merge.

## Recent contract coverage

- When `--repo` is present, init forwards it to `write-design-current-env.sh` so `source-env.sh` and the current-design-env symlink preserve the non-default repo.
