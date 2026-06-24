# Step 5b OOS prepare dispatch

**Consumer**: `/design` Step 5b after `design-step5b-prepare.sh` returns on normal prepare output.

**Contract**: single canonical prose table for orchestrator dispatch on `design-step5b-prepare.sh` machine actions. This file documents prompt-side branching only; it does not change wrapper behavior, Python-owned prepare statuses, or annotate semantics.

**When to load**: immediately before the orchestrator branches on `$DESIGN_TMPDIR/oos-filing-prepare.env` at Step 5b after prepare returns (wrapper rc `0` on normal paths; wrapper rc `2` only for `NEXT_ACTION=unknown-oos-status`; not `STEP5B_STATUS=prepare-failed-continue`).

---

## Dispatch key

Primary key: branch on the whole-line `NEXT_ACTION=...` row from `oos-filing-prepare.env` (captured from `design-step5b-prepare.sh` stdout).

Fallback key: when the action row is missing, parse `FILE_DESIGN_OOS_STATUS=` from `oos-filing-prepare.env` and map it to `NEXT_ACTION` using the fallback table below. Do not invent actions from `STEP5B_STATUS=` alone.

If `NEXT_ACTION` and the status-derived action disagree, stop for repair rather than silently choosing one.

---

## Branch on NEXT_ACTION

| Action | Dispatch |
|---|---|
| `skip-pipeline` | Do not call `/larch:issue`. Follow Step 5b item 2 in `SKILL.md` (skip breadcrumb, `WARN=` handling for `skip-already-filed-sentinel`, conditional annotate, continue to Step 5b.5). |
| `file-issues` | Invoke `/larch:issue` and annotate per Step 5b item 3 in `SKILL.md`. |
| `unknown-oos-status` | Stop for repair. Parse from `oos-filing-prepare.env` even when the prepare wrapper exits non-zero. Do not continue to Step 5b.5. |

---

## Fallback: branch on FILE_DESIGN_OOS_STATUS

When `NEXT_ACTION` is absent, derive it from `FILE_DESIGN_OOS_STATUS=`:

| Status | Derived `NEXT_ACTION` | Notes |
|---|---|---|
| `skip-sentinel` | `skip-pipeline` | Re-emit `OOS_SKIP_BREADCRUMB` when present. Prepare writes `.completed/step-5b`. No annotate. |
| `skip-already-filed-sentinel` | `skip-pipeline` | Parse non-empty `WARN=` into `execution-issues.md`. `STEP5B_NEEDS_ANNOTATE=true` only when `oos-issue.stdout.txt` is non-empty. Annotate is best-effort under that guard. Prepare writes `.completed/step-5b` when annotate is not needed. Never use annotate-before-issue manual recovery. |
| `skip-no-items` | `skip-pipeline` | Re-emit `OOS_SKIP_BREADCRUMB` when present. Prepare writes `.completed/step-5b`. No annotate. |
| `skip-all-security` | `skip-pipeline` | Re-emit `OOS_SKIP_BREADCRUMB` when present. Prepare writes `.completed/step-5b`. No annotate. |
| `ready` | `file-issues` | Always `STEP5B_NEEDS_ANNOTATE=true`. Prepare does not write `.completed/step-5b`; annotate owns completion. |

Any other status value: stop for operator repair. Do not silently route.

---

## Compatibility note

Older prepare output may emit only `FILE_DESIGN_OOS_STATUS=` without `NEXT_ACTION=`. Current `python/cli.py design step5b-prepare` emits both keys on success paths. Prepare failure emits `NEXT_ACTION=skip-pipeline` with `STEP5B_STATUS=prepare-failed-continue` and is handled before this dispatch table applies.
