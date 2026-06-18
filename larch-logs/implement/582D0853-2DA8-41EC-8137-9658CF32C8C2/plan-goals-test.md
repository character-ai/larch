## Goal
Implement issue #4733: [IMPLEMENTING] [BUG] /design final summary: empty Top reviewers + unknown/collector-failure-N labels.

## Implementation Plan
## Summary

The `/design` final summary's `## Review Phase Detail` section mis-renders reviewer attribution in two independent ways. Despite 5 review rounds with 26 accepted suggestions (each round's Reviewer Competition Scoreboard correctly attributed accepted findings to specific slots), the whole-run **Top reviewers (by suggestions accepted)** list renders empty, and the single reviewer slot failure is labeled **`unknown/collector-failure-1`** instead of the real failing slot (`cursor/requirements`). Both are observability bugs in the design review-phase-detail rendering pipeline. The design plan itself is unaffected.

## Original report

> In the above final report, despite 5 review rounds (which means there must have been lots of accepted suggestions on every round), you output:
>  Top reviewers (by suggestions accepted, whole run):
>   - (no accepted suggestions attributed to a reviewer slot)
>
>   Reviewer slot failures: 1
>   - unknown/collector-failure-1: 1
> I want both failures root caused and /bug filed

Observed on design run `FF5F334D-6020-4831-B5CE-EB907B9E4CAC` (issue #4720): 26 suggestions accepted across 5 rounds; the round-5 failed `cursor-plan-requirements` slot rendered as `unknown/collector-failure-1`.

## Reproduction scenario

1. Run `/design <issue>` to completion through Step 5 (finalize), with at least one review round that accepts suggestions and at least one collector failure (a reviewer slot that does not return `STATUS=OK`).
2. Read the `## Review Phase Detail` block in the rendered final summary.

Observed:
- `**Top reviewers** (by suggestions accepted, whole run):` followed by `- (no accepted suggestions attributed to a reviewer slot)`.
- `**Reviewer slot failures**: N` followed by `- unknown/collector-failure-1: 1` (and `-2`, `-3`, ... for additional failures) instead of the real vendor/archetype.

The per-round Reviewer Competition Scoreboard in `voting-tally.md` shows attribution works per round (for example `Codex-Generic`, `Cursor-Arch`), so the data exists; only the whole-run aggregation and the failure labels are wrong.

## Expected behavior

- **Top reviewers (by suggestions accepted, whole run)** lists the vendor/archetype slots that proposed the accepted suggestions, aggregated across rounds, using the same attribution the per-round scoreboard already computes.
- **Reviewer slot failures** names the real failing slot (for example `cursor/requirements`), not `unknown/collector-failure-N`.

## Observed behavior

For every `/design` run:
- Top reviewers is structurally always empty: `- (no accepted suggestions attributed to a reviewer slot)`.
- Each collector failure is labeled `unknown/collector-failure-<i>`.

## Root cause analysis

Two independent root causes, both in the `/design` review-phase-detail pipeline. `/implement` is likely unaffected because it produces the artifacts the renderer expects.

**Bug 1 — Top reviewers always empty (findings source missing for design).**
`render-review-phase-detail.sh` computes "Top reviewers" only from a `--findings-file` (JSON-lines with `.outcome == "accepted"` and `.reviewer_slots`/`.reviewer`). When that file is absent or empty, it falls through to the literal `- (no accepted suggestions attributed to a reviewer slot)`.
`review_phase_detail.render_design_review_detail()` looks for `design_tmpdir/review-findings-full.jsonl` and passes `--findings-file` only when that file exists. But `review-findings-full.jsonl` is an `/implement` code-review artifact (written by `review_and_fix.py` and `run_logs.py`). `/design`'s `plan_review.py` never writes it; it writes per-round `plan-review/round-N/findings-classification.tsv` instead. So for every `/design` run the file is missing, `--findings-file` is never passed, and the top-reviewers section is structurally always empty, even though per-round attribution exists (the `vN_tool` / accepted columns of `findings-classification.tsv`, which is the same data behind the per-round scoreboard).

**Bug 2 — slot failures rendered as `unknown/collector-failure-N` (attribution discarded at the source).**
`scripts/write-design-round-meta.sh` builds round-meta.json's `.collector` field from only the failure count: it reads `COLLECT_FAILURE_COUNT` from `round-summary.env`, then loops emitting hardcoded placeholder records `TOOL=unknown` / `STATUS=FAILED` / `REVIEWER_FILE=collector-failure-<i>.txt`. It never reads the actual per-slot collector records, so the real failing slot's tool and output basename (available in `reviewer-status.tsv` / `collector-results.env`, for example `cursor` and `cursor-plan-requirements-output.txt`) are discarded. The renderer's collector/`derive` awk then cannot map `collector-failure-1.txt` to a vendor/archetype: it is absent from the panel slot-map, and `derive()` returns `unknown/collector-failure-1`. The renderer faithfully renders the placeholder it was handed.

## Evidence

- Renderer empty-branch text: `scripts/render-review-phase-detail.sh` prints `- (no accepted suggestions attributed to a reviewer slot)` when the top-reviewers temp file is empty (the `else` branch after `if [ -s "$top_file" ]`, near the `**Top reviewers**` print).
- Top-reviewers gated on a JSON findings file: `scripts/render-review-phase-detail.sh` "top-N reviewers by suggestions accepted" block guards on `[ -n "$FINDINGS_FILE" ] && [ -f "$FINDINGS_FILE" ]` and parses `.outcome == "accepted"` + `.reviewer_slots`.
- Design findings-file selection: `python/review_phase_detail.py` `render_design_review_detail` sets `findings_file = design_tmpdir / "review-findings-full.jsonl"` and passes it only `if findings_file.is_file()`.
- `review-findings-full.jsonl` is `/implement`-only: written by `python/review_and_fix.py` and `python/run_logs.py`; `python/plan_review.py` writes `findings-classification.tsv`, not `review-findings-full.jsonl`.
- Placeholder failure synthesis: `scripts/write-design-round-meta.sh` `_collect_failures` loop emits `printf 'TOOL=unknown\nSTATUS=FAILED\nREVIEWER_FILE=collector-failure-%s.txt\n' "$_i"`.
- A test already encodes the placeholder shape: `python/test_design_summary.py` fixture `"collector":"TOOL=unknown\\nSTATUS=FAILED\\nREVIEWER_FILE=collector-failure-1.txt\\n"`.
- Attribution exists per round for the same run: `voting-tally.md` Reviewer Competition Scoreboard attributed accepted findings to slots; `latest-reviewer-status.tsv` showed `cursor-plan-requirements ... failed` in round 5.
- Related prior work on the same renderer (both closed/DONE, both distinct root causes): #4057 fixed a `derive()` case-sensitivity mis-attribution in this same Top reviewers section; #4038 fixed the same "renderer needs an artifact the pipeline never writes" shape for the `/implement` Review Phase Detail table (round-meta.json).
- Possible regression signal: #4057's symptom shows the design Top reviewers section was populated (as `unknown/Cursor-dyn-contract-parity`) circa larch v49, whereas it is now empty. Bug 1 may have regressed when design stopped producing the findings-file the renderer reads (hedged; needs a bisect).

## Affected files

- `scripts/render-review-phase-detail.sh` — whole-run top-reviewers aggregation and collector-failure labeling (renders what it is given).
- `python/review_phase_detail.py` — `render_design_review_detail` selects the findings-file; points at an `/implement`-only artifact for design.
- `scripts/write-design-round-meta.sh` — synthesizes count-based `unknown/collector-failure-N` placeholder records instead of real per-slot records.
- `python/plan_review.py` — owns the per-round `findings-classification.tsv`; candidate source for whole-run attribution.
- Tests: `python/test_design_summary.py`, `scripts/test-render-review-phase-detail.sh` (and a design-path case is missing).

## Suggested fix(es)

**Bug 1 (Top reviewers).** Either:
- Change the design path to aggregate accepted-suggestion attribution from the per-round `plan-review/round-N/findings-classification.tsv` (`vN_tool` / accepted columns) rather than the `/implement`-only `review-findings-full.jsonl`; or
- Have `plan_review.py` emit a `review-findings-full.jsonl`-shaped file (objects with `.outcome` and `.reviewer_slots`) into the design tmpdir so the existing renderer path works unchanged.
Add a design-path test asserting non-empty Top reviewers when accepted findings exist.

**Bug 2 (slot failures).** In `write-design-round-meta.sh`, build the `.collector` records from the real per-slot collector results (`reviewer-status.tsv` / `collector-results.env`) so each failed slot carries its true `TOOL=` and `REVIEWER_FILE=<slot>-output.txt`. The renderer's slot-map / `derive` will then resolve the true vendor/archetype. Add a test asserting a failed `cursor-plan-requirements` slot renders as `cursor/...`, not `unknown/collector-failure-N`.

## Open questions

- Should the whole-run top-reviewers aggregation read `findings-classification.tsv` directly (renderer-only change, no new artifact) or should design emit a `review-findings-full.jsonl` (engine change, reuses the existing renderer path)? Either fixes Bug 1; the former avoids a new artifact.
- Are there `/design` collector-failure paths that genuinely lack any slot identity (where `unknown/...` is unavoidable)? If so, keep a graceful fallback while attributing the slots that are known.
- Is `/implement`'s equivalent attribution actually correct, or does it share Bug 2's count-only failure synthesis through a different `write-*-round-meta` path? Worth a quick check during the fix.
- Both affected scripts (`render-review-phase-detail.sh`, `write-design-round-meta.sh`) appear to be in scope for the open sh-to-py port #4640 (`rendering + round-meta`). The fix should target whichever version is live to avoid rework or conflict; coordinate ordering with that port.

## Test plan
(no test plan section in plan-file)
