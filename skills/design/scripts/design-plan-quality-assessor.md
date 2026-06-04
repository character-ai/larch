# design-plan-quality-assessor.sh

**Consumer**: `/design` Step 3.6 plan-quality assessor lane between Gate B settled paths and Step 3b.

**Callers**: `skills/design/SKILL.md` Step 3.6 fence. The orchestrator runs the cheap classification gate: HARD invokes this driver, and the driver renders the HARD `🔶` banner; non-HARD prints the skip breadcrumb and writes the Step 3.6 sentinel without invoking the driver.

## Argv

| Flag | Required | Notes |
|------|----------|-------|
| `--design-tmpdir PATH` | yes | Canonicalized with `cd … && pwd -P` |
| `--codex-present true\|false` | yes | Forwarded to `assess-plan-round.sh` on HARD paths |
| `--cursor-present true\|false` | yes | Forwarded to `assess-plan-round.sh` on HARD paths |
| `--timeout SECS` | no | Default `1860`; forwarded to `assess-plan-round.sh` |

Unknown flags → exit `2`.

## Derived / session inputs

- `run-params.json` `design_classification` via `read-design-classification.sh` as the lane authority. Legacy `workflow_path` is read only to emit a mismatch `WARN=` when it disagrees; it cannot suppress a HARD assessor lane.
- `CODEX_PRESENT` / `CURSOR_PRESENT` from argv (not re-read from session-env in the driver)
- Child script overrides (hermetic harness):
  - `LARCH_SNAPSHOT_PLAN_ROUND_SH` — default `$PLUGIN_ROOT/skills/design/scripts/snapshot-plan-round.sh`
  - `LARCH_ASSESS_PLAN_ROUND_SH` — default `$PLUGIN_ROOT/skills/design/scripts/assess-plan-round.sh`

Every `read-cursor`, `write-after`, rollback `write-cursor`, and assessor-round call resolves through these bindings.

## Responsibilities

1. Resolve `CLAUDE_PLUGIN_ROOT`, export `DESIGN_TMPDIR`, bind child script seams.
2. Pause checkpoint (awk-only `ISSUE_NUMBER`; never `source` `source-env.sh`). On `.pause-requested`, write `ASSESSOR_STATUS=paused` to the result env, emit the paused note, and exit `11`; prompt-side orchestration executes `design-pause-save.sh` with repo passthrough. Re-check `.pause-requested` immediately before every settled `_write_result_and_emit` (write-after-failed, assess-failed, happy assess tail, and non-HARD skip).
3. Non-HARD `design_classification` → `ASSESSOR_STATUS=skipped`, `WORKFLOW_PATH` from the aligned classification, `ROUND_NUM` from read-cursor (or `1`), write+emit, exit `0`.
4. HARD: `read-cursor` → `write-after` for current round.
5. `write-after` failure → `WARN=` with the post-Gate-B snapshot-failure sentence, `append-tool-failure.sh`, round rollback (`review-round-count.txt` = `ROUND_NUM-1`, best-effort `write-cursor`), `ASSESSOR_STATUS=write-after-failed`, write+emit, exit `0`.
6. `write-after` success → `assess-plan-round.sh`. Non-zero assess child exit → `append-tool-failure.sh`, `ASSESSOR_STATUS=assess-failed`, `WARN=` with assess exit code, write+emit, exit `0` (do not treat empty stdout as intentional skip). On assess exit `0`, parse assessor KVs; when `ASSESSOR_VERDICT=not-worse` and `EFFECTIVE_ASSESSORS=0`, append the 0/3 `WARN=` line; write+emit, exit `0`.
7. Non-zero `read-cursor` on the HARD lane → `ASSESSOR_STATUS=cursor-read-failed`, `WARN=` + `append-tool-failure.sh`, skip `write-after` and assess. Non-HARD skip still uses `ROUND_NUM=1` when read-cursor fails. On `write-after` failure rollback: decrement `review-round-count.txt` to `ROUND_NUM-1`, then best-effort `write-cursor --value ROUND_NUM`; `write-cursor` failure adds `WARN=` without restoring the count.

Stops before the WORSE Continue/Stop `AskUserQuestion` (LLM boundary in `SKILL.md`).

## Result env (`.step3.6-assessor.env`)

Driver result-env for audit and settled-path state only. It is not a control input for the WORSE Continue/Stop branch, which uses the trusted trailer frame in driver stdout.

Result-env allowlist (not stdout):

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
| `10` | WORSE-majority action branch with trusted trailer frame |
| `11` | Pause-save handoff; prompt-side orchestrator runs `design-pause-save.sh` |

Never exit `1`.

## `set -e` child-call invariant

Under `set -euo pipefail`, every `"$SNAPSHOT_SH"` and `"$ASSESS_SH"` invocation uses local `set +e` capture. A child non-zero exit must not skip `_write_result_and_emit` on settled exit-`0` paths.

## Orchestrator handoff

Prompt-side `SKILL.md` Step 3.6 fence:

1. Cheap `design_classification` pre-read. When `_design_classification=HARD`, invoke the driver; the driver renders `> **🔶 /design 3.6: assessor**`. When non-HARD, print `⏩ 3.6: assessor — design_classification=…; skipped` and write the Step 3.6 sentinel without invoking the driver.
2. `set +e` capture to `_assessor_out` / `_assessor_rc` via `"${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/design-plan-quality-assessor.sh"` (qualified path — never bare script name).
3. For rc `10`, parse only the final exact `LARCH_ASSESSOR_TRUSTED_TRAILERS_BEGIN` frame from driver stdout. Filter that frame from chat, require exactly one numeric `LARCH_ASSESSOR_ROUND_NUM`, and abort fail-closed before Continue/Stop if validation fails.
4. Print filtered driver-rendered display text and diagnostic `ASSESSOR_RC=` / trusted `ASSESSOR_ROUND_NUM=` scalars for the prompt-side branch. Do not source or route from `.step3.6-assessor.env`.
5. rc=`0` writes the Step 3.6 sentinel and continues to Step 3b; rc=`2` aborts as configuration error; rc=`10` fires the Continue/Stop prompt using the trusted trailer scalar; any unexpected rc aborts.
6. On rc `11`, `exec design-pause-save.sh --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}`. The paused result env is audit data only; it must not be treated as a settled skip.

## Edit in sync

Update together: `skills/design/SKILL.md` Step 3.6, `skills/design/references/assessor.md`, `SECURITY.md`, `skills/design/scripts/test-design-plan-quality-assessor.sh`, `scripts/test-design-structure.sh`, and `Makefile`.

## Harness

`skills/design/scripts/test-design-plan-quality-assessor.sh` (Makefile target: `test-design-plan-quality-assessor`).

Cross-links: `assessor.md`, `assess-plan-round.md`, `snapshot-plan-round.md`, `lib-phase-driver.md`, `design-postplan-emit.md`.

## Thin-fence exit contract

Exit codes are now: `0` settled (including `missing-snapshot` fail-open/degraded statuses), `2` argv/configuration error, `10` WORSE-majority action branch, and `11` pause-save handoff. Exit `1` is reserved. The driver writes paused state and exits `11`; the prompt-side orchestrator executes `design-pause-save.sh`.

The driver renders the HARD banner, warnings, paused note, and WORSE-majority display via `emit`. On rc=`10`, it appends a trusted trailer frame after display text; the orchestrator filters trailer lines from chat, parses only the last exact marker frame, and requires a numeric `LARCH_ASSESSOR_ROUND_NUM` before Continue/Stop. General machine KVs stay in `.step3.6-assessor.env` as audit/settled-path state and are not emitted on FD 3 or used for Continue/Stop control.
