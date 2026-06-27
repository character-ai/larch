# Step 5b OOS prepare dispatch

**Consumer**: Legacy/manual `/design` Step 5b dispatch notes.

**Contract**: historical context for `design-step5b-prepare.sh` action routing. Current prompt-side Step 5b must branch on `NEXT_ACTION=` emitted by `python/cli.py design step5b-prepare`; this file is not a prompt-side fallback table.

**When to load**: only for legacy/manual repair of old Step 5b transcripts.

---

## Current contract

Current `python/cli.py design step5b-prepare` must emit a whole-line `NEXT_ACTION=...` row in `oos-filing-prepare.env`.

Valid actions remain:

| Action | Dispatch |
|---|---|
| `skip-pipeline` | Do not call `/larch:issue`. Follow `finalize-step5.md` for skip breadcrumb, warning handling, conditional annotate, and Step 5b.5 continuation. |
| `file-issues` | Invoke `/larch:issue` and annotate per `finalize-step5.md`. |
| `unknown-oos-status` | Stop for repair. Do not continue to Step 5b.5. |

Missing `NEXT_ACTION`, an unknown action, or a disagreement between `NEXT_ACTION` and `FILE_DESIGN_OOS_STATUS` is a repair stop. Do not derive a prompt-side route from `FILE_DESIGN_OOS_STATUS`.

## Legacy note

Older prepare output could emit only `FILE_DESIGN_OOS_STATUS=`. The historical mapping was: `ready` to `file-issues`; `skip-sentinel`, `skip-already-filed-sentinel`, `skip-no-items`, and `skip-all-security` to `skip-pipeline`; every other status to `unknown-oos-status`. That mapping now belongs inside the prepare wrapper, where disagreement checks can fail closed before Step 5b.5.
