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
| `--manual-requested true\|false` | yes | |
| `--repo OWNER/REPO` | no | Forwarded for `tracking-issue-write.sh` rename |

## Responsibilities

1. Tier map: SIMPLE → `sketch_budget=0`, `workflow_path=SIMPLE`; HARD → `sketch_budget=4`, `workflow_path=HARD`; `source=caller-forwarded`.
2. **Single** `write-design-current-env.sh` **before** `[DESIGNING]` rename (`--manual-requested true` only when manual); non-zero → `INIT_STATUS=env-refresh-failed`, exit `1`.
3. `tracking-issue-write.sh rename --state designing` with `${REPO:+--repo}`; rename failure → `WARN=`.
4. `write-run-params.sh` → `run-params.json`; non-zero → `INIT_STATUS=contract-drift`, exit `1`.
5. Full router-flag jq-merge block (guard, `mktemp` paths, filter, `mv`, `append-tool-failure.sh` on jq failure, both warning strings).

## Result env (`.design-init-runparams-result.env`)

Allowlist: `INIT_STATUS` (`ok` \| `contract-drift` \| `env-refresh-failed`), `RENAMED`, `RUN_PARAMS_PATH`, `DESIGN_CLASSIFICATION`, `WARN`.

## Exit codes

| Code | When |
|------|------|
| `0` | Success |
| `1` | `write-design-current-env.sh` failure (`INIT_STATUS=env-refresh-failed`) or `write-run-params.sh` contract drift (`INIT_STATUS=contract-drift` in result env) |
| `2` | Argv / repo config error |

## LLM boundary

Stops before Step 0c; does not write `feature-description.txt` (orchestrator-owned).

## Idempotency

Rename and run-params writes are idempotent on replay.

## Harness

`scripts/test-design-structure.sh` (env-before-rename line-order, jq-merge greps); `scripts/test-step0b-router-flag-recovery.sh` replicates jq-merge.

Orchestrator handoff: `_init_out` capture + file-first `.design-init-runparams-result.env` read + stdout merge; exit `2` / unexpected non-zero abort; `INIT_STATUS=contract-drift` only after `_init_rc=1` with successful KV merge.
