## Decision 1: /design plan-review parity for round-start-s
- **Question**: The buggy `_render_inflight_gantt` is shared; `/design` plan-review (`plan_review.py`) also never writes `round-start-s`. Fix `/design` via its own `round-start-s` persistence, or via the shared renderer fallback only?
- **Resolution**: Persist `round-start-s` at round start on BOTH sides — `review_and_fix.py` (/implement) and `plan_review.py` (/design). Each skill gets a correct primary window; the renderer fallback is genuine defense-in-depth. This adds `plan_review.py` + `test_plan_review.py` beyond the issue's listed files.
- **Source**: user

## Decision 2: Drop suggested defense-in-depth #3 (panel-manifest basename attribution)
- **Question**: The issue suggests restricting the in-flight chart to vendor rows whose output basename is in the current round's `panel-manifest.ndjson`. Implement it, or replace it?
- **Resolution**: DROP #3. The window bound (round-start-s + hardened fallback) is the only viable round-attribution mechanism; implement that alone. No basename filter.
- **Source**: user (grounded in codebase finding below)

## Decision 3: Settled / final per-round charts are IN scope
- **Question**: Should round-attribution also apply to the settled/final per-round charts (`scripts/render-review-phase-detail.sh`, `type=round` windows)?
- **Resolution**: IN SCOPE. Audit the settled per-round charts for the same cross-round leak; harden `render-review-phase-detail.sh` (and its test) if it leaks. If already round-bounded by `round-meta.json`, add a regression assertion confirming no prior-round leak.
- **Source**: user

## Decision 4: Basename attribution cannot distinguish rounds (codebase finding)
- **Question**: Does panel-manifest basename attribution actually filter prior-round rows?
- **Resolution**: No. Verified in committed run logs: reviewer output basenames repeat every round (`codex-vote-output.txt`, `cursor-vote-output.txt`, `aggregator-output.txt`, `cursor-plan-arch-output.txt`, dynamic `dyn-*-output.txt`). The timing-ledger vendor row has no round column (cols: v1/vendor/ts/skill/-/vendor/slot/start/end/dur/output/status). So a basename-membership filter includes prior rounds' rows that share basenames with the current round's manifest. Window-by-time is the only mechanism.
- **Source**: codebase

## Decision 5: round-start-s is absent in ALL committed run logs (codebase finding)
- **Question**: Is defect 1 (round-start-s never written on the normal path) real and universal?
- **Resolution**: Confirmed. Every multi-round run log under `larch-logs/{implement,design}/*/round-*` shows `round-start-s` MISSING even for completed rounds (which have `round-meta.json`). The escalation-only write in `review_and_fix.py` essentially never fires on the normal completion path.
- **Source**: codebase

## Decision 6: In-flight overlap with #4589 on plan_review.py `_LEGACY_ASSETS` — blocked-by edge wired
- **Question**: Does this fix surface overlap any in-flight DESIGNING/DESIGNED/IMPLEMENTING issue, requiring postpone or a blocked-by edge?
- **Resolution**: Initial surface (`progress_report.py`, `review_and_fix.py`) showed no overlap. But Decision 1 (/design parity) expands the surface: the /design plan-review round loop lives in `skills/design/scripts/review-design-step3-loop.sh`, embedded as a `_LEGACY_ASSETS` blob in `python/plan_review.py` (enforced by `test_embedded_review_design_step3_loop_matches_live_script`). In-flight #4589 ([DESIGNED]) regenerates 9 OTHER `_LEGACY_ASSETS` blobs in the SAME dict and edits `python/test_plan_review.py` — a genuine file-surface overlap. No active /implement run on #4589 (it is [DESIGNED], not [IMPLEMENTING]), so no postpone is needed; instead wired `#4546 blocked-by #4589` during design (verified). #4546 was already blocked-by #4543 ([CLOSED], merged sibling). #4542 (Python-rule policy) and #4538 (voter panel) do not touch the surface.
- **Source**: codebase + user (Decision 1)

## Hard constraints (must not break)
- Preserve the timing-ledger TSV vendor-row schema (no new round column).
- Keep the existing escalation-branch `_persist_round_start` call working (idempotent: it no-ops if the file already exists, so a start-time write is compatible).
- `_persist_round_start` writes only if the file does not already exist — round-start captured at round START must win; do not overwrite mid-round.
- Do not rework per-round chart CONTENT (that was #4543, done) — only fix round-window attribution.
- Preserve current behavior for round 1 (no prior round → window starts at round-1 start, no regression).

## Non-goals
- No timing-ledger schema change (no round column).
- No basename/manifest attribution filter (Decision 2/4).
- No rework of per-round chart content or styling.
