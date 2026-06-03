# design-publish.sh

**Consumer**: `/design` Step 5c — deterministic publish tail after compose, validator gate, and redaction.

**Caller**: `skills/design/SKILL.md` Step 5c after items 1–3 on Gate-C-approved runs (orchestrator invokes this driver once in the foreground).

## Argv

| Flag | Required | Notes |
|------|----------|-------|
| `--design-tmpdir PATH` | yes | `cd … && pwd -P` |
| `--issue N` | yes | Positive integer |
| `--session-id STR` | yes | Flag required; value may be empty (newline/CR rejected only) |
| `--claude-pid N` | yes | Positive integer; passed to `design_reentry_marker_write` |
| `--repo OWNER/REPO` | no | Forwarded on REPO-aware helpers |

## Responsibilities

1. Preconditions: `.completed/step-5b` present; `composed-plan.redacted.md` non-empty (`exit 2` otherwise).
2. Resolve `REPO` once (`resolve-repo.sh` → `gh repo view` → empty).
3. `plan-block-write.sh` with `if !` guard; failure → `failed-plan-write` render, `PLAN_WRITE_OK=false`, `exit 1`.
4. `design_reentry_marker_write` before publish/rename; non-zero → Warnings via `append-tool-failure.sh`, continue.
5. `upsert-diagrams-comment.sh` when architecture file is **non-empty**, when `architecture-diagram.md` is **absent** and `architecture-diagram.skipped` is present (`--clear-architecture`), or when `architecture-diagram.md` is **empty** and `architecture-diagram.skipped` is present (`--clear-architecture`). Subshell stdout capture to `diagrams-architecture-upsert.stdout`; non-blocking failures.
6. When `SESSION_ID` non-empty: `render-final-summary.sh --pre-publish-only`, then `scripts/design-log-publish.sh` with subshell capture; parse `PUBLISH_OK`, `PR_NUMBER`, `PR_URL`, and recovery branch metadata; unexpected non-zero without `PUBLISH_OK=`, exit 0 without `PUBLISH_OK=`, or `PUBLISH_OK=false` → `PUBLISH_OK=false` + Warnings. Failed publish envelopes keep the existing `append-tool-failure.sh --redact` reporting.
7. When `SESSION_ID` empty: `WARN=` via quiet driver (`add_warn`); skip pre-publish render, publish, and rename.
8. `render-final-summary.sh --post-publish-only` runs after the publish attempt whenever `PLAN_WRITE_OK=true`, including publish failures, so diagnostics refresh regardless of publish outcome.
9. `[DESIGNED]` rename only when `SESSION_ID` non-empty **and** `PUBLISH_OK=true`; Step 6 cleanup is likewise gated by the publish result outside this driver.

Exports `DESIGN_TMPDIR`, `ISSUE_NUMBER`, and `SESSION_ID` before every `render-final-summary.sh` call.

## Result env (`.design-publish-result.env`)

Allowlist: `PLAN_WRITE_OK`, `PUBLISH_OK`, `PR_NUMBER`, `PR_URL`, `RECOVERY_BRANCH`, `LOG_RECOVERY_BRANCH`, `RENAMED`, `UPSERT_STATUS`, `ARCHITECTURE_SOURCE`, `FINAL_SUMMARY_PATH`, `WARN`.

## Exit codes

| Code | When |
|------|------|
| `0` | Publish tail completed (`PLAN_WRITE_OK=true`) |
| `1` | `plan-block-write.sh` failed (`PLAN_WRITE_OK=false` in result env) |
| `2` | Argv / precondition error |
| `3` | `PLAN_WRITE_OK=true` but result-env write failed after publish tail |

## Migration limit

`--clear-architecture` updates only the stable `<!-- larch:diagrams v1 -->` tracking-issue comment. Legacy `<!-- larch:diagrams v1 runid=… -->` orphan comments from older runs are not matched; operators may still see a stale Architecture block on those orphans after a non-architectural re-design.

## Ordering invariants

On plan-block-write failure: `plan-block-write.sh` → `render-final-summary.sh` (`--outcome failed-plan-write`, `--post-publish-only`) → result env → `exit 1`.

On success: `plan-block-write.sh` → `design_reentry_marker_write` → `upsert-diagrams-comment.sh` (when architecture file or skipped sentinel) → `render-final-summary.sh` (`--pre-publish-only`, when `SESSION_ID` non-empty) → `design-log-publish.sh` (when `SESSION_ID` non-empty) → `render-final-summary.sh` (`--post-publish-only`) → `tracking-issue-write.sh rename --state designed` (when `SESSION_ID` non-empty and `PUBLISH_OK=true`).

## Edit in sync

Update together: `skills/design/SKILL.md` Step 5c, `skills/design/scripts/test-design-publish.sh`, `scripts/test-design-structure.sh`, `scripts/test-render-cost-line-callsites.sh`.

## Harness

`skills/design/scripts/test-design-publish.sh` (contract: `test-design-publish.md`).

Orchestrator handoff: `_publish_out` capture + file-first `.design-publish-result.env` read + stdout merge; exit `2` / unexpected non-zero abort; `_publish_rc=1` is the normal plan-write failure path (parse, do not abort).
