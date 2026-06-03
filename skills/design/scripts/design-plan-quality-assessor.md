# design-plan-quality-assessor.sh

**Consumer**: `/design` Step 3.6 plan-quality assessor lane between Gate B settled paths and Step 3b.

**Callers**: `skills/design/SKILL.md` Step 3.6 fence (orchestrator prints HARD `🔶` banner or non-HARD skip breadcrumb, then invokes this driver).

## Argv

| Flag | Required | Notes |
|------|----------|-------|
| `--design-tmpdir PATH` | yes | Canonicalized with `cd … && pwd -P` |
| `--codex-present true\|false` | yes | Forwarded to `assess-plan-round.sh` on HARD paths |
| `--cursor-present true\|false` | yes | Forwarded to `assess-plan-round.sh` on HARD paths |
| `--timeout SECS` | no | Default `1860`; forwarded to `assess-plan-round.sh` |

Unknown flags → exit `2`.

## Derived / session inputs

- `run-params.json` `workflow_path` and `design_classification` (`jq` primary, `sed` fallback). When `workflow_path` is missing/empty, the driver aligns to `design_classification` (`HARD` → HARD lane, else `SIMPLE`). When both are present and disagree, a `WARN=` is emitted and the lane follows `design_classification`.
- `CODEX_PRESENT` / `CURSOR_PRESENT` from argv (not re-read from session-env in the driver)
- Child script overrides (hermetic harness):
  - `LARCH_SNAPSHOT_PLAN_ROUND_SH` — default `$PLUGIN_ROOT/skills/design/scripts/snapshot-plan-round.sh`
  - `LARCH_ASSESS_PLAN_ROUND_SH` — default `$PLUGIN_ROOT/skills/design/scripts/assess-plan-round.sh`

Every `read-cursor`, `write-after`, rollback `write-cursor`, and assessor-round call resolves through these bindings.

## Responsibilities

1. Resolve `CLAUDE_PLUGIN_ROOT`, export `DESIGN_TMPDIR`, bind child script seams.
2. Pause checkpoint (awk-only `ISSUE_NUMBER`; never `source` `source-env.sh`). On `.pause-requested`, write `ASSESSOR_STATUS=paused` to the result env, then `exec design-pause-save.sh`. Re-check `.pause-requested` immediately before every settled `_write_result_and_emit` (write-after-failed, assess-failed, happy assess tail, and non-HARD skip).
3. Non-HARD `workflow_path` → `ASSESSOR_STATUS=skipped`, `WORKFLOW_PATH` from run-params, `ROUND_NUM` from read-cursor (or `1`), write+emit, exit `0`.
4. HARD: `read-cursor` → `write-after` for current round.
5. `write-after` failure → `WARN=` with the post-Gate-B snapshot-failure sentence, `append-tool-failure.sh`, round rollback (`review-round-count.txt` = `ROUND_NUM-1`, best-effort `write-cursor`), `ASSESSOR_STATUS=write-after-failed`, write+emit, exit `0`.
6. `write-after` success → `assess-plan-round.sh`. Non-zero assess child exit → `append-tool-failure.sh`, `ASSESSOR_STATUS=assess-failed`, `WARN=` with assess exit code, write+emit, exit `0` (do not treat empty stdout as intentional skip). On assess exit `0`, parse assessor KVs; when `ASSESSOR_VERDICT=not-worse` and `EFFECTIVE_ASSESSORS=0`, append the 0/3 `WARN=` line; write+emit, exit `0`.
7. Non-zero `read-cursor` on the HARD lane → `ASSESSOR_STATUS=cursor-read-failed`, `WARN=` + `append-tool-failure.sh`, skip `write-after` and assess. Non-HARD skip still uses `ROUND_NUM=1` when read-cursor fails. On `write-after` failure rollback: decrement `review-round-count.txt` to `ROUND_NUM-1`, then best-effort `write-cursor --value ROUND_NUM`; `write-cursor` failure adds `WARN=` without restoring the count.

Stops before the WORSE Continue/Stop `AskUserQuestion` (LLM boundary in `SKILL.md`).

## Result env (`.step3.6-assessor.env`)

Dual-purpose: driver result-env and cross-turn state for the WORSE-Stop branch.

Allowlist / stdout KV contract:

- `ASSESSOR_STATUS`
- `ASSESSOR_VERDICT`
- `EFFECTIVE_ASSESSORS`
- `ASSESSOR_VERDICT_FILE`
- `ASSESSOR_VERDICT_ENV`
- `ROUND_NUM`
- `WORKFLOW_PATH`
- `WARN` (optional, repeatable)

## Exit codes

| Code | When |
|------|------|
| `0` | Settled (any `ASSESSOR_STATUS`, including skips and degraded paths) |
| `2` | Argv / configuration error |

Never exit `1`.

## `set -e` child-call invariant

Under `set -euo pipefail`, every `"$SNAPSHOT_SH"` and `"$ASSESS_SH"` invocation uses local `set +e` capture. A child non-zero exit must not skip `_write_result_and_emit` on settled exit-`0` paths.

## Orchestrator handoff

Prompt-side `SKILL.md` Step 3.6 fence:

1. Cheap `workflow_path` and `design_classification` pre-read. When both are set and disagree, align `_wp` to `design_classification` (same rule as the driver) and print the mismatch `WARN` once before the banner. When aligned `_wp=HARD`, print `> **🔶 /design 3.6: assessor**` **before** driver invoke; when non-HARD, print `⏩ 3.6: assessor — workflow_path=…; skipped` then invoke.
2. `set +e` capture to `_assessor_out` / `_assessor_rc` via `"${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/design-plan-quality-assessor.sh"` (qualified path — never bare script name).
3. Initialize seven allowlisted routing keys to empty; `_assessor_parse_ok=false`.
4. When driver stdout contains `design-plan-quality-assessor: result env write failed`, set `_assessor_force_stdout=true` and skip file-read (stale env must not win).
5. File-first read of `.step3.6-assessor.env` when present, not a symlink, and `_assessor_force_stdout` is false; on symlink, `printf '%s\n' "**⚠ Step 3.6: refusing symlink .step3.6-assessor.env; using stdout fallback.**" >&2` and skip file-read.
6. File-read loop: allowlisted keys → `printf -v`; set `_assessor_parse_ok=true` only when `ASSESSOR_STATUS` is populated from the file. `WARN)` → `printf '%s\n'` verbatim (chat-visible on successful file parse).
7. Stdout merge: when `_assessor_force_stdout`, overwrite routing keys from stdout; otherwise fill-only-unset. `WARN)` when `_assessor_parse_ok` is false or `_assessor_force_stdout` is true.
8. Fail-closed abort: rc=`2` config error; rc=`0` with empty `ASSESSOR_STATUS`; rc not in `{0,2}` catch-all — each prints stderr banner and `exit 1`.
9. When merged `ASSESSOR_STATUS=paused`, `exec design-pause-save.sh` (driver may have already attempted pause inside `$()` capture; result env must not read as empty or `skipped`).

## Edit in sync

Update together: `skills/design/SKILL.md` Step 3.6, `skills/design/references/assessor.md`, `SECURITY.md`, `skills/design/scripts/test-design-plan-quality-assessor.sh`, `scripts/test-design-structure.sh`, and `Makefile`.

## Harness

`skills/design/scripts/test-design-plan-quality-assessor.sh` (Makefile target: `test-design-plan-quality-assessor`).

Cross-links: `assessor.md`, `assess-plan-round.md`, `snapshot-plan-round.md`, `lib-phase-driver.md`, `design-postplan-emit.md`.

## Thin-fence exit contract

Exit codes are now: `0` settled (including `missing-snapshot` fail-open/degraded statuses), `2` argv/configuration error, `10` WORSE-majority action branch, and `11` pause-save handoff. Exit `1` is reserved. The driver writes paused state and exits `11`; the prompt-side orchestrator executes `design-pause-save.sh`.

The driver renders the HARD banner, warnings, paused note, and WORSE-majority display via `emit`. On rc=`10`, it appends a trusted trailer frame after display text; the orchestrator filters trailer lines from chat, parses only the last exact marker frame, and requires a numeric `LARCH_ASSESSOR_ROUND_NUM` before Continue/Stop. General machine KVs stay in `.step3.6-assessor.env` and are not emitted on FD 3.
