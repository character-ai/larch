# design-publish.sh

**Consumer**: `/design` Step 5c — deterministic publish tail after final plan composition.

**Caller**: `skills/design/SKILL.md` Step 5c after item 1 (compose `composed-plan.md`) on Gate-C-approved runs; the orchestrator invokes the `design-step5c.sh` wrapper in immediate-background mode and waits for `<task-notification>` before parsing this driver's result env or stdout fallback.

## Argv

| Flag | Required | Notes |
|------|----------|-------|
| `--design-tmpdir PATH` | yes | `cd … && pwd -P` |
| `--issue N` | yes | Positive integer |
| `--session-id STR` | yes | Flag required; value may be empty (newline/CR rejected only) |
| `--claude-pid N` | yes | Positive integer; passed to `design_reentry_marker_write` |
| `--repo OWNER/REPO` | no | Forwarded on REPO-aware helpers |
| `--skip-validate` | no | Skips only composed-plan validation for the operator accept / proceed-anyway path; redaction still runs |

## Responsibilities

1. Preconditions: `.completed/step-5b` present; `composed-plan.md` non-empty (`exit 2` otherwise).
2. Pre-side-effect pause checkpoint: when `.pause-requested` exists, immediately `exec design-pause-save.sh --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE" ${REPO:+--repo "$REPO"}` before validation, redaction, plan write, rename, publish, or marker side effects.
3. Unless `--skip-validate` is passed, run `python/cli.py plan validate DIR/composed-plan.md` under `set +e`, parse the five `VALIDATE_*` KVs, and treat `VALIDATE_STATUS=defects-found` as `exit 4` with no redaction or publish-tail side effects. Empty, `not-run`, unexpected status (anything other than `ok` after the defects-found branch), or nonzero validator output that is not `defects-found` is validator infrastructure failure (`exit 2`).
4. Redact `composed-plan.md` through `python/cli.py redact secrets` (stdin) to `composed-plan.redacted.md`; redactor nonzero is `exit 2` with `redact secrets failed`, and an empty redacted file is also `exit 2`.
5. Resolve `REPO` once (`resolve-repo.sh` → `gh repo view` → empty).
6. `python/cli.py named-block write --marker plan` with `if !` guard; failure → `failed-plan-write` render, `PLAN_WRITE_OK=false`, `exit 1`.
7. `python/cli.py diagrams upsert` when architecture file is **non-empty**, when `architecture-diagram.md` is **absent** and `architecture-diagram.skipped` is present (`--clear-architecture`), or when `architecture-diagram.md` is **empty** and `architecture-diagram.skipped` is present (`--clear-architecture`). Subshell stdout capture to `diagrams-architecture-upsert.stdout`; non-blocking failures.
8. When `SESSION_ID` non-empty: after the best-effort diagram upsert block, run `python3 "$PLUGIN_ROOT/python/cli.py" tracking-issue rename --state designed` best-effort and parse `RENAMED`; this rename is not gated on `PUBLISH_OK` and may still run when diagram upsert skipped or failed. Rename-failure `WARN=` text reports the runtime diagram upsert state instead of asserting that a diagram was posted.
9. When `SESSION_ID` non-empty: run `scripts/design-log-publish.sh` with subshell capture; parse `PUBLISH_OK`, `PR_NUMBER`, `PR_URL`, and recovery branch metadata; unexpected non-zero without `PUBLISH_OK=`, exit 0 without `PUBLISH_OK=`, or `PUBLISH_OK=false` → `PUBLISH_OK=false` + Warnings. Failed publish envelopes keep the existing `run-log append-failure --redact` reporting.
10. When `SESSION_ID` empty: `WARN=` via quiet driver (`add_warn`); skip publish and rename.
11. Before rendering, export design-log recovery metadata plus `RENAMED`, `NEW_TITLE`, `UPSERT_RAN`, `UPSERT_STATUS`, and `DESIGNED_ADMISSION_READY` so failed-publish summary notes match the publish-tail admission state. `DESIGNED_ADMISSION_READY` uses the same `[DESIGNED]` plus required-space prefix shape as `/implement` admission and is forced false when the diagram upsert ran but did not return `UPSERT_STATUS=ok`. `render-final-summary.sh --post-publish-only` runs after the publish attempt whenever `PLAN_WRITE_OK=true`, including publish failures, so diagnostics refresh regardless of publish outcome.
12. `design_reentry_marker_write` runs after publish/summary only when `SESSION_ID` is non-empty **and** `PUBLISH_OK=true`; Step 6 cleanup is likewise gated by the publish result outside this driver.

Exports `DESIGN_TMPDIR`, `ISSUE_NUMBER`, and `SESSION_ID` before every `render-final-summary.sh` call.

## Result env (`.design-publish-result.env`)

Allowlist: `PLAN_WRITE_OK`, `VALIDATE_STATUS`, `VALIDATE_DEFECT_COUNT`, `VALIDATE_SKIPPED_COUNT`, `VALIDATE_UNSAFE_TOKEN_COUNT`, `VALIDATE_LOG_FILE`, `PUBLISH_OK`, `PR_NUMBER`, `PR_URL`, `RECOVERY_BRANCH`, `LOG_RECOVERY_BRANCH`, `RENAMED`, `NEW_TITLE`, `DESIGNED_ADMISSION_READY`, `UPSERT_STATUS`, `ARCHITECTURE_SOURCE`, `FINAL_SUMMARY_PATH`, `WARN`.

On success `VALIDATE_STATUS=ok`; on `--skip-validate`, `VALIDATE_STATUS=skipped`.

## Exit codes

| Code | When |
|------|------|
| `0` | Publish tail completed (`PLAN_WRITE_OK=true`) |
| `1` | `python/cli.py named-block write --marker plan` failed (`PLAN_WRITE_OK=false` in result env) |
| `2` | Argv / precondition / validator infrastructure / redaction error |
| `3` | `PLAN_WRITE_OK=true` but result-env write failed after publish tail |
| `4` | Composed-plan validation found defects (`VALIDATE_STATUS=defects-found`); nothing redacted, published, renamed, or marked complete |

## Migration limit

`--clear-architecture` updates only the stable `<!-- larch:diagrams v1 -->` tracking-issue comment. Legacy `<!-- larch:diagrams v1 runid=… -->` orphan comments from older runs are not matched; operators may still see a stale Architecture block on those orphans after a non-architectural re-design.

## Ordering invariants

On validation defects: `python/cli.py plan validate` → result env best-effort / stdout KVs → `exit 4`.

On issue-wire plan write failure: validate (unless skipped) → redact → `python/cli.py named-block write --marker plan` → `render-final-summary.sh` (`--outcome failed-plan-write`, `--post-publish-only`) → result env → `exit 1`.

On success: validate (unless skipped) → redact → `python/cli.py named-block write --marker plan` → `python/cli.py diagrams upsert` (when architecture file or skipped sentinel) → `python3 "$PLUGIN_ROOT/python/cli.py" tracking-issue rename --state designed` (when `SESSION_ID` non-empty) → `design-log-publish.sh` (when `SESSION_ID` non-empty) → `render-final-summary.sh` (`--post-publish-only`) → `design_reentry_marker_write` (when `SESSION_ID` non-empty and `PUBLISH_OK=true`).

## Edit in sync

Update together: `skills/design/SKILL.md` Step 5c, `skills/design/scripts/render-final-summary.md`, `skills/design/scripts/test-design-publish.sh`, `skills/design/scripts/test-design-publish.md`, `scripts/test-design-structure.sh`, and `scripts/test-render-cost-line-callsites.sh`. This driver owns the composed-plan `python/cli.py plan validate`, `redact secrets`, summary admission/recovery prose, and publish-tail ordering contract.

## Harness

`skills/design/scripts/test-design-publish.sh` (contract: `test-design-publish.md`).

Orchestrator handoff: stdout captured to a temp file (`_publish_stdout_file`); `read-result-env.sh --input .design-publish-result.env --fallback-input _publish_stdout_file` reads allowlisted keys (file-first, stdout fallback); `_publish_rc=3` forces a guaranteed-absent primary path so the stdout fallback wins (stdout authority on rc=3); WARN bodies from the parsed result are replayed to top-chat verbatim; exit `2` / unexpected non-zero (outside `{0,1,3,4}`) abort before result env parse; `_publish_rc=1` is the normal plan-block-write failure path (parse, do not abort); `_publish_rc=4` routes to the shared validator-failure handler.

## Recent contract coverage

- Non-zero `design-log-publish.sh` exits are fail-closed even when stdout contains `PUBLISH_OK=true`; empty `SESSION_ID` renders `publish-skipped`.

Before `design-log-publish.sh`, the driver deletes stale top-level `timing-report-final.*` artifacts, renders fresh timing JSON through temporary unpublished paths, atomically moves only validated `timing-report-final.json` into `$DESIGN_TMPDIR`, and logs a warning without publishing stale siblings when render fails.
