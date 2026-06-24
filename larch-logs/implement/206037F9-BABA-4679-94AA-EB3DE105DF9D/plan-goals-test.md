## Goal
Implement issue #5255: [IMPLEMENTING] [BUG] Reviewer prune-to-empty should converge the review loop, not re-probe.

## Implementation Plan
## Summary

When reviewer pruning removes **every** reviewer slot from a round, the panel is empty, the round produces zero findings, and **both `/design` and `/implement` treat this as non-convergence and force another review round** (the "re-probe"). This report requests the opposite semantics: a prune-to-empty panel should be read as a **convergence signal** and **complete the review loop immediately**. Pruning drops reviewers whose recent net contribution is non-positive; when that drops the whole panel, the review has effectively run dry, so launching another round is wasteful and produces confusing zero-reviewer rounds in operator-facing reports.

## Original report

If pruning reduces the set of reviewers to 0, it should result in immediate convergence, causing completion of review process, for both /design and /implement

## Reproduction scenario

Data-dependent; describe rather than force.

1. Run `/design` (or `/implement`) on a change that takes several review rounds.
2. By round 3 or 4, reach a state where **every** surviving reviewer slot has a trailing-2-round net `accepted - rejected <= 0` (or acceptance rate `< 1/3`). This is common near convergence because the net test prunes break-even reviewers (the threshold is `<= 0`, not `< 0`).
3. Pruning (active only in rounds 3-4) drops all slots → `PANEL_PRUNED_EMPTY=true` → a round runs with **0 reviewers and 0 findings**.
4. Observe that the loop does **not** complete: it launches another round (for `/design`, the round-5 unpruned re-probe; for `/implement`, `round_num += 1`).

**Concrete instance**: `/design` run `E5335A4D-CE96-43E7-833A-7BB49872413A` (issue #5157). Per-round panel sizes were 8, 5, 4, **0**, 5. Round 4 had 0 reviewers / 0 suggestions, yet round 5 launched. Committed forensics are in the design-log PR for that run (`larch-logs/design/E5335A4D-CE96-43E7-833A-7BB49872413A/`).

## Expected behavior

When pruning reduces the reviewer set to 0, the review loop should **declare convergence and complete** the review process. The plan (`/design`) or code (`/implement`) from the last round that actually ran reviewers becomes final. No additional round is launched. This applies to both:

- `/design` Step 3 plan review.
- `/implement` Step 5 code review.

## Observed behavior

Both skills force another round on a prune-to-empty panel:

- **`/design`**: the round exits with `LOOP_STATUS=zero-findings-degraded-panel` / `AGGREGATOR_STATUS=skipped-pruned-empty`, and the continuation decision maps `PANEL_PRUNED_EMPTY=true` to "continue" (`PLAN_REVIEW_CONTINUE=true`, reason `pruned-empty`). The loop increments the round and runs again, culminating in the round-5 re-probe with the **full unpruned panel**.
- **`/implement`**: the round returns status `prune-skipped`; if `round_num < round_cap`, the loop does `round_num += 1; continue` and runs another round.

Net effect: a wasted zero-reviewer round, a forced extra round, and a confusing `0 / 0 / 0 / 0` row in the operator-facing review table and final summary.

## Root cause analysis

The behavior is intentional today (a "re-probe" safety net against over-aggressive pruning), not an accidental defect. The request is to change that policy to convergence. Root mechanics:

- The prune filter sets `PANEL_PRUNED_EMPTY=true` whenever **all** slots are pruned, with **no floor** to retain at least one reviewer (`python/review_pipeline.py:525`: `"true" if not eligible and rows else "false"`).
- Pruning runs only in rounds 3-4 (`python/review_pipeline.py:489`); rounds 1, 2, and 5 use the full unpruned manifest. A slot is prunable only with `>= 2` rounds of recorded history and trailing-2-round net `<= 0` or acceptance rate `< 1/3` (`python/review_pipeline.py:502-518`).
- `/design`: `plan_review_continuation` routes `panel_pruned_empty == "true"` to continue (`python/plan_review.py:1779-1781`); the `awaiting-continuation` loop handler then increments the round (`python/plan_review.py:2076` onward). The loop driver also treats `zero-findings-degraded-panel` as a continue-eligible status (`python/plan_review.py:1986-2022`).
- `/implement`: `prune-skipped` status routes to `round_num += 1; continue` when below the cap (`python/review_and_fix.py:2929-2932`).

**Honest tradeoff to weigh.** The re-probe exists because a zero-reviewer round is not positive evidence that the plan is clean, and the unpruned re-probe gives previously-pruned reviewers another pass. In the exact run that motivated this report (`E5335A4D`), the round-5 re-probe **did surface a genuine accepted finding** from a reviewer (`codex-plan-generic`) that pruning had dropped. So converging on prune-empty trades some thoroughness for determinism and token efficiency. The net threshold being `<= 0` (break-even reviewers get pruned) is also why whole-panel pruning is reachable; that threshold is an adjacent lever worth considering. The requested change is a deliberate policy decision, and `/design` should weigh the thoroughness cost explicitly.

## Evidence

- Per-round table for design run `E5335A4D` (issue #5157), from the run's `larch:final-summary` projection: rounds 1-5 reviewer counts `8, 5, 4, 0, 5`; round 4 = 0 suggestions / 0 accepted / 0 reviewers; round 5 = 4 suggestions / 1 accepted / 5 reviewers.
- Round 4 `round-summary.env` (committed under the run's design log): `LOOP_STATUS=zero-findings-degraded-panel`, `AGGREGATOR_STATUS=skipped-pruned-empty`, `COLLECT_OK_COUNT=0`, `ACCEPTED_COUNT=0`, `DEGRADED_PANEL=0` (i.e., treated as a clean, complete round, not a failure).
- Round 4 `panel-manifest.ndjson` = 0 lines; `reviewer-status.tsv` = header only (no reviewer launched).
- Prune ledger (`reviewer-prune-ledger.tsv`) shows all 5 slots entering round 4 had trailing-2-round net `<= 0`, so every slot was pruned; `plan-review-slots.pre-prune.ndjson` = 5 slots, round-4 dispatched panel = 0.
- `/design` continue locus: `python/plan_review.py:1779-1781`.
- `/implement` continue locus: `python/review_and_fix.py:2929-2932`.
- No-floor prune locus: `python/review_pipeline.py:525`.
- Documented re-probe intent: `skills/design/references/plan-review.md` (panel-pruning bullet: "continuation proceeds toward the round-5 re-probe").

## Affected files

- `python/plan_review.py` — `/design` continuation decision (`plan_review_continuation`, line ~1779) and the `awaiting-continuation` loop handler (line ~2076). Primary change site for `/design`. Note the round-provenance persistence for `zero-findings-degraded-panel` (lines ~1993-2012, issue #5194) so a converged prune-empty round still publishes the plan with non-zero round provenance.
- `python/review_and_fix.py` — `/implement` `prune-skipped` routing (line ~2929). Primary change site for `/implement`.
- `python/review_pipeline.py` — shared prune filter and `derive_prune_status` (`pruned-empty`); the empty-panel short-circuit at lines ~1207 and ~2132. Relevant if the fix is implemented at the prune layer (e.g., a keep-one floor) instead of the loop layer.
- `python/plan_review_round.py` / `python/plan_review_panel.py` — set/propagate `PANEL_PRUNED_EMPTY` and `AGGREGATOR_STATUS=skipped-pruned-empty` for `/design`; relevant for status semantics.
- `skills/design/references/plan-review.md` — documents the round-5 re-probe; must be updated to reflect convergence-on-prune-empty.
- `docs/configuration-and-permissions.md` — `LARCH_REVIEWER_PRUNE` section describes prune behavior; update if semantics change.
- `python/implement_dispatch.py` — operator-facing `/implement` Step 5 banner text describing prune behavior (line ~438); update for accuracy.
- Tests: `python/test_plan_review.py` (continuation), `python/test_review_and_fix.py` (`test-review-and-fix-convergence`), `python/test_review_pipeline.py`, `python/test_plan_review_panel.py`, `python/test_plan_review_round.py`, and the `make test-reviewer-prune` all-pruned-markers harness.

## Suggested fix(es)

Two clean loop-layer changes, symmetric across skills:

1. **`/design`**: in `plan_review_continuation` (`python/plan_review.py:1779`), change the `panel_pruned_empty == "true"` branch from `cont = True` (reason `pruned-empty`) to `cont = False` with a distinct reason such as `converged-pruned-empty`. Verify the `zero-findings-degraded-panel` round-provenance write (lines ~1993-2012) still records the completed round count so `design_publish.review_provenance()` publishes the plan (do not regress issue #5194).
2. **`/implement`**: in `python/review_and_fix.py:2929`, route `prune-skipped` to `terminal_status = "complete"` directly (i.e., fold it into the convergence branch at line ~2934) instead of `round_num += 1; continue`.
3. Update `skills/design/references/plan-review.md`, `docs/configuration-and-permissions.md`, and the `/implement` Step 5 banner to describe convergence-on-prune-empty rather than the re-probe.
4. Update the affected tests/harnesses in the same change (the launcher/convergence harness rule requires same-PR coverage for these reject/accept-path changes).

Alternative / adjacent levers (if `/design` prefers a different shape for the same symptom): add a keep-at-least-one-reviewer floor in `reviewer_prune_filter` so the panel never empties; or change the net prune threshold from `<= 0` to `< 0` so break-even reviewers survive. These avoid empty rounds entirely instead of converging on them.

## Open questions

- **Round attribution**: should the prune-empty round itself count as a completed round, or should convergence be attributed to the last round that actually ran reviewers (e.g., round 3 in the `E5335A4D` case)? This affects the reported round count and the `rounds_completed` provenance used at publish.
- **Thoroughness tradeoff**: in the motivating run, the re-probe caught a real accepted finding that pruning had hidden. Confirm this thoroughness loss is acceptable, or specify a middle ground (e.g., one re-probe with the **reduced/pruned** panel rather than the full panel; or converge only when the last staffed round had zero high-severity accepted findings).
- **Loop-layer vs prune-layer fix**: should this be fixed by converging on the empty round (loop layer) or by preventing the empty panel (a keep-one floor / threshold change at the prune layer)? They produce different operator-visible round shapes.
- **Scope guard**: the change must affect only the prune-empty path (`zero-findings-degraded-panel` / `prune-skipped`). It must **not** alter handling of genuine panel failures (`panel-failed`, `panel-init-failed`, `degraded-empty-collector`), which already exit the loop via separate paths.

## Test plan
(no test plan section in plan-file)
