# design-publish.sh

**Consumer**: `/design` Step 5c — deterministic publish tail after final plan composition.

**Caller**: `skills/design/SKILL.md` Step 5c after item 1 (compose `composed-plan.md`) on Gate-C-approved runs; the orchestrator invokes this driver once in the foreground and re-invokes it for validator retries.

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
2. Pre-side-effect pause checkpoint: when `.pause-requested` exists, immediately `exec design-pause-save.sh --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE" ${REPO:+--repo "$REPO"}` before validation, redaction, plan write, publish, rename, or marker side effects.
3. Unless `--skip-validate` is passed, run `invoke-plan-validator.sh DIR/composed-plan.md` under `set +e`, parse the five `VALIDATE_*` KVs, and treat `VALIDATE_STATUS=defects-found` as `exit 4` with no redaction or publish-tail side effects. Empty, `not-run`, or nonzero validator output that is not `defects-found` is validator infrastructure failure (`exit 2`).
4. Redact `composed-plan.md` through `scripts/redact-secrets.sh` (stdin) to `composed-plan.redacted.md`; redactor nonzero is `exit 2` with `redact-secrets.sh failed`, and an empty redacted file is also `exit 2`.
5. Resolve `REPO` once (`resolve-repo.sh` → `gh repo view` → empty).
6. `plan-block-write.sh` with `if !` guard; failure → `failed-plan-write` render, `PLAN_WRITE_OK=false`, `exit 1`.
7. `upsert-diagrams-comment.sh` when architecture file is **non-empty**, when `architecture-diagram.md` is **absent** and `architecture-diagram.skipped` is present (`--clear-architecture`), or when `architecture-diagram.md` is **empty** and `architecture-diagram.skipped` is present (`--clear-architecture`). Subshell stdout capture to `diagrams-architecture-upsert.stdout`; non-blocking failures.
8. When `SESSION_ID` non-empty: run `scripts/design-log-publish.sh` with subshell capture; parse `PUBLISH_OK`, `PR_NUMBER`, `PR_URL`, and recovery branch metadata; unexpected non-zero without `PUBLISH_OK=`, exit 0 without `PUBLISH_OK=`, or `PUBLISH_OK=false` → `PUBLISH_OK=false` + Warnings. Failed publish envelopes keep the existing `append-tool-failure.sh --redact` reporting.
9. When `SESSION_ID` empty: `WARN=` via quiet driver (`add_warn`); skip publish and rename.
10. `render-final-summary.sh --post-publish-only` runs after the publish attempt whenever `PLAN_WRITE_OK=true`, including publish failures, so diagnostics refresh regardless of publish outcome.
11. `[DESIGNED]` rename and `design_reentry_marker_write` run only when `SESSION_ID` is non-empty **and** `PUBLISH_OK=true`; Step 6 cleanup is likewise gated by the publish result outside this driver.

Exports `DESIGN_TMPDIR`, `ISSUE_NUMBER`, and `SESSION_ID` before every `render-final-summary.sh` call.

## Result env (`.design-publish-result.env`)

Allowlist: `PLAN_WRITE_OK`, `VALIDATE_STATUS`, `VALIDATE_DEFECT_COUNT`, `VALIDATE_SKIPPED_COUNT`, `VALIDATE_UNSAFE_TOKEN_COUNT`, `VALIDATE_LOG_FILE`, `PUBLISH_OK`, `PR_NUMBER`, `PR_URL`, `RECOVERY_BRANCH`, `LOG_RECOVERY_BRANCH`, `RENAMED`, `UPSERT_STATUS`, `ARCHITECTURE_SOURCE`, `FINAL_SUMMARY_PATH`, `WARN`.

On success `VALIDATE_STATUS=ok`; on `--skip-validate`, `VALIDATE_STATUS=skipped`.

## Exit codes

| Code | When |
|------|------|
| `0` | Publish tail completed (`PLAN_WRITE_OK=true`) |
| `1` | `plan-block-write.sh` failed (`PLAN_WRITE_OK=false` in result env) |
| `2` | Argv / precondition / validator infrastructure / redaction error |
| `3` | `PLAN_WRITE_OK=true` but result-env write failed after publish tail |
| `4` | Composed-plan validation found defects (`VALIDATE_STATUS=defects-found`); nothing redacted, published, renamed, or marked complete |

## Migration limit

`--clear-architecture` updates only the stable `<!-- larch:diagrams v1 -->` tracking-issue comment. Legacy `<!-- larch:diagrams v1 runid=… -->` orphan comments from older runs are not matched; operators may still see a stale Architecture block on those orphans after a non-architectural re-design.

## Ordering invariants

On validation defects: `invoke-plan-validator.sh` → result env best-effort / stdout KVs → `exit 4`.

On plan-block-write failure: validate (unless skipped) → redact → `plan-block-write.sh` → `render-final-summary.sh` (`--outcome failed-plan-write`, `--post-publish-only`) → result env → `exit 1`.

On success: validate (unless skipped) → redact → `plan-block-write.sh` → `upsert-diagrams-comment.sh` (when architecture file or skipped sentinel) → `design-log-publish.sh` (when `SESSION_ID` non-empty) → `render-final-summary.sh` (`--post-publish-only`) → `tracking-issue-write.sh rename --state designed` (when `SESSION_ID` non-empty and `PUBLISH_OK=true`) → `design_reentry_marker_write`.

## Edit in sync

Update together: `skills/design/SKILL.md` Step 5c, `skills/design/scripts/test-design-publish.sh`, `scripts/test-design-structure.sh`, and `scripts/test-render-cost-line-callsites.sh`. This driver owns the composed-plan `invoke-plan-validator.sh` and `redact-secrets.sh` calls.

## Harness

`skills/design/scripts/test-design-publish.sh` (contract: `test-design-publish.md`).

Orchestrator handoff: `_publish_out` capture + file-first `.design-publish-result.env` read + stdout merge; exit `2` / unexpected non-zero abort; `_publish_rc=1` is the normal plan-write failure path (parse, do not abort); `_publish_rc=4` routes to the shared validator-failure handler.
