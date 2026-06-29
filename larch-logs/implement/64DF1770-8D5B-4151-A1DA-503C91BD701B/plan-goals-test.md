## Goal
Implement issue #5838: [IMPLEMENTING] [BUG] Reviewer attribution credits slot name, not executing tool, on vendor fallback.

## Implementation Plan
## Summary

The `/design` (and `/review`) final-summary **Top reviewers** list and the **reviewer-status table** credit the panel-assigned **slot label** (e.g. `Cursor-Arch`, `Cursor-Innovation`), not the tool that actually executed the slot. When a vendor is unavailable and its slots **fall back** to another tool, the slot keeps its original name, so the summary reports a vendor as having reviewed when it contributed nothing. The actual executing tool is already recorded (`collector-results.env` `TOOL=`) but is never reconciled into the attribution, so the report is misleading on any fallback.

## Original report

Reported during the `/design` run on issue #5778 (run `B65ABAAF-0FDB-4DE7-BCE1-D19FF7B972C1`). The final summary listed Cursor slots in **Top reviewers** (`Cursor-Arch`, `Cursor-Pragmatic`) and the reviewer-status table showed every `Cursor-*` slot as `✅`, even though Cursor was unavailable for the entire run. Re-running the Step 0 health probe (`python3 python/cli.py status check`) afterward still returned `CURSOR_STATE=probe-failed` / `CURSOR_PRESENT=false`. The committed run log showed every Cursor lane had failed and each `Cursor-*` slot had been executed by Codex via fallback. The report asks to (a) flag the mis-attribution and (b) correct it so reviewer attribution reflects the tool that actually ran the slot.

## Reproduction scenario

1. Make one external vendor unavailable while its binary is still on `PATH` (so the panel still attempts it). Example trigger observed: Cursor returns `ActionRequiredError: You have an unpaid invoice ...` with exit 1 / 0 bytes.
2. Run `/design <issue>` (or `/review --diff`). At Step 0 the degraded-tools gate fires; choose Continue.
3. Let the plan-review panel run. Each `Cursor-*` slot fails to launch and falls back to Codex (or Claude).
4. Inspect the final summary's **Top reviewers** block and the reviewer-status table.

Observed in run `B65ABAAF-0FDB-4DE7-BCE1-D19FF7B972C1` (PR #5834, merged); the run log under `larch-logs/design/B65ABAAF-0FDB-4DE7-BCE1-D19FF7B972C1/` is a permanent fixture for this repro.

## Expected behavior

Reviewer attribution should reflect the tool that actually produced the output. On fallback, the summary should either credit the executing tool, or annotate the slot to show fallback (e.g. `Cursor-Innovation (via Codex)`), and the reviewer-status table should distinguish a fallback-executed slot from one the named vendor actually ran. A vendor that produced zero output should not appear as a contributing reviewer.

## Observed behavior

- **Top reviewers** lists `Cursor-Arch` and `Cursor-Pragmatic` with accepted-point scores; the single distinct accepted finding (`FINDING_1`) is attributed to `Cursor-Innovation Phase2`.
- The reviewer-status table shows all `Cursor-*` slots as `✅`.
- In reality Codex executed every one of those slots; Cursor produced 0 bytes on every lane.

## Root cause analysis

The summary keys reviewer attribution on the **panel-assigned slot label**, which is decoupled from the **executing tool** after fallback. The two are produced and stored separately and never reconciled:

- Slot label (assignment): `panel-manifest.ndjson` `slot` (`cursor-plan-*`), surfaced via `plan_review_round._slot_human_label` and the per-finding `finding_reviewers` / `reviewer_slots` columns in `findings-classification.tsv`. This name persists regardless of which tool actually ran.
- Executing tool (truth): `collect_results.derive_tool()` parses the launched argv (`cursor agent` vs `codex exec`) and writes `TOOL=` into `collector-results.env`. On fallback the `cursor-plan-*` output file is recorded with `TOOL=codex`.

`progress_report._top_reviewers_from_classification` / `_accepted_reviewers_from_classification` / `_human_attribution_labels` aggregate accepted-point scores purely from the slot-label columns and the slot manifest; they never read `collector-results.env`'s `TOOL=`. The reviewer-status table is likewise rendered from `reviewer-status.tsv`, whose `slot` column is the slot label and whose `status=done` only means the slot's lifecycle completed (via fallback), not that the named vendor ran it.

This is a reporting/attribution defect, not a logic error in the panel itself: fallback worked correctly; only the post-run attribution misrepresents which vendor reviewed.

## Evidence

From run log `larch-logs/design/B65ABAAF-0FDB-4DE7-BCE1-D19FF7B972C1/`:

- `plan-review/round-1/dyn-cursor-plan-lint-ratchet-auditor.txt.failure-diag`, `cursor-vote-output.txt.failure-diag`, `plan-review/round-1/revise/cursor-output.txt.failure-diag` all contain: `ActionRequiredError: You have an unpaid invoice ... Failed with exit code 1. Output size: 0 bytes.` (every Cursor lane failed with 0 bytes).
- `collector-results.env`: every `cursor-plan-*-output-phase2.txt` record has `TOOL=codex`, `STATUS=OK` (Codex executed the Cursor-named slots).
- `plan-review/round-1/reviewer-status.tsv` and `latest-reviewer-status.tsv`: all `Cursor-*` slots show `done`.
- `proposer-map.tsv`: `FINDING_1` attributed to `Cursor-Innovation Phase2` (the one accepted finding, slot-labeled Cursor, produced by Codex).
- Final summary (`final-summary.md`): **Top reviewers** lists `Cursor-Arch — 2`, `Cursor-Pragmatic — 2`; reviewer-status table shows all `Cursor-*` slots `✅`; `Exec Issues` count 13 (`cursor-review failed ...`).
- Step 0 envelope and a fresh post-run `python3 python/cli.py status check`: `CURSOR_BINARY_FOUND=true`, `CURSOR_PRESENT=false`, `CURSOR_STATE=probe-failed`.

Code paths:

- `python/larch/report/progress_report.py:776` `_top_reviewers`, `:842` `_accepted_reviewers_from_classification`, `:891` `_top_reviewers_from_classification`, `:793` `_human_attribution_labels` — attribution keyed on slot label only.
- `python/larch/agents/collect_results.py:326` `derive_tool`, plus `CollectorRecord.tool` and the `TOOL=` field written to `collector-results.env` — the authoritative executing-tool provenance that is never consulted by the renderer.

## Affected files

- `python/larch/report/progress_report.py` — Top-reviewers scoring and human attribution labels; the reviewer-status table emit. Primary fix site.
- `python/larch/agents/collect_results.py` — owns `derive_tool()` / `TOOL=`; the provenance source the renderer must consume.
- `python/larch/review/plan_review_round.py` — `_slot_human_label` and `reviewer-status.tsv` writer (slot label as the table identity); candidate site to carry/emit the executing tool alongside the slot.
- `python/larch/design/design_summary.py` (and the review-side summary assembler) — assemble the final-summary block; verify they pass through the reconciled attribution.
- Tests: `python/test_progress_report*`, `python/test_collect_results*` (or equivalents) need fallback-attribution coverage.

## Suggested fix(es)

Reconcile slot label with executing tool when rendering attribution:

1. Join the per-slot `TOOL=` from `collector-results.env` (keyed by reviewer output file / slot) into the Top-reviewers scoring in `progress_report._accepted_reviewers_from_classification`. When the executing tool differs from the slot's nominal vendor, either credit the executing tool or render an explicit fallback annotation (e.g. `Cursor-Innovation (via Codex)`), so a vendor that produced 0 bytes is not credited.
2. In the reviewer-status table, mark fallback-executed slots distinctly (e.g. a separate icon or a `→ codex` suffix) instead of a plain `✅` under the original vendor name.
3. Keep the slot label for topology/identity, but make the executing tool the source of truth for any "which vendor reviewed" claim.
4. Consider also threading the executing tool into `findings-classification.tsv` / `proposer-map.tsv` so attribution is correct at the data layer, not only at render time.

Minimal first cut: render-time reconciliation against `collector-results.env` `TOOL=` (no schema change), with a fallback annotation. The data-layer change (item 4) is the more durable fix.

## Open questions

- Preferred presentation on fallback: credit the executing tool outright, or keep the slot name with a `(via <tool>)` annotation? (Annotation preserves which lens reviewed while being honest about the tool.)
- Should `collector-results.env` retained in the committed run log be treated as the single source of truth for executing tool, or should the executing tool be persisted into `findings-classification.tsv` at write time?
- Scope: fix `/design` plan-review summary only, or also `/review` code-review summaries and `/implement` reviewer reporting, which share `progress_report.py`?

## Test plan
(no test plan section in plan-file)
