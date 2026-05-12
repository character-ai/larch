## Goal
Fix 4 bugs/improvements in /implement run log behavior: standardize RUN_ID generation, enrich metadata comments, remove token costs from tracking issue, add || true robustness to plan upsert.

## Implementation Plan

### Files to modify
- `skills/implement/SKILL.md` — 4 targeted edits
- `skills/implement/references/summary-comment-template.md` — remove larch:token-report from marker list

### Change 1 — Standardize RUN_ID
Add a RUN_ID initialization block after the "Early exit" check in Step 0.5: derive RUN_ID from $IMPLEMENT_TMPDIR/session-id (via tr -d '\r\n') when --run-id was not provided, with uuidgen as fallback.

### Change 2 — Enrich metadata comments
In Branches 2, 3, and 4 of Step 0.5, replace the single-line printf with a block that reads larch version and adds agent/version info. New format: "Run `$RUN_ID` adopted issue #N. Logs: `larch-logs/implement/$RUN_ID/`.\nAgent: `${coder:-claude}` | Larch: `$LARCH_VER`"

### Change 3 — Remove larch:token-report from tracking issue
In Step 18, remove the summary-token-report.md creation and the larch:token-report upsert. Update summary-comment-template.md to remove larch:token-report from the marker list.

### Change 4 — Add || true to larch:plan upsert
In the Larch-log batches section (Step 1), add `|| true` to the tracking-issue-summary.sh upsert-summary call for larch:plan.

## Test plan
Run /relevant-checks after changes. Verify with grep that larch:token-report no longer appears in upsert calls. The changes are prose-only in SKILL.md.
