## Goal
Implement issue #3714: [IMPLEMENTING] logs-size-reduction: Phase 3a: collapse finding/plan duplication in /implement run logs\n\n## Context.

## Implementation Plan
## Context

Phase 3a of the logs-size-reduction series. After #3708/#3709 land, `larch-logs/implement/` still holds ~132 MB, and **~47 MB (36%) is the same finding/plan prose stored in up to five places per round**. Policy decision for this series: committed run logs carry no duplicated content — one canonical store per content type, projections are derived on read.

Blocked on #3708 (touches the same write paths: `scripts/larch-log.sh` round staging, batch table, tally composer).

## The duplication being collapsed (corpus-wide numbers)

| Copy | MB | Disposition |
|---|---|---|
| `review-findings-full.jsonl` (per-finding payloads: `phase`, `outcome`, `category`, `reviewer_slots`, `round_num`, `prose_body`) | 15.6 | **canonical store — keep** |
| `round-N/findings.md` (proposal-stage aggregate of the same prose) | 12.3 | drop |
| `round-N/accepted-findings.md` | 5.5 | drop (projection of `outcome=accepted`) |
| `round-N/oos.md` | 3.5 | drop (projection of `outcome=out_of_scope`) |
| `round-N/rejected-findings-full.md` | 3.4 | drop (projection of `outcome=rejected`) |
| `round-N/oos-accepted-review.md` | 1.3 | **keep** — read by the `oos-silent-drop` audit scan |
| `round-N/review-round-summary.md` | 5.6 | **keep** — the human round digest |
| `round-N/voting-tally.md` + `findings-classification.tsv` | 3.5 | **keep** — vote matrix (audit `exon` scan) + forensic ratings |
| `plan-goals-test.md` (verbatim copy of the tracking issue's `larch:plan` block) | 6.2 | **drop** — the issue body is the canonical plan store; `manifest.json::issue_number` is the pointer |
| Per-voter vote outputs (`claude/cursor/codex-vote-output.txt`, phase2 variants) | 5.9 | **cap**: keep the per-finding vote lines, truncate free-form rationale prose at ~2 KB per voter file |
| `codex-impl-transcript.txt` (117 runs × 89 KB) | 10.4 | **trim** with the same policy family as session transcripts: keep prose/decisions, stub bulk tool/file dumps |

## Changes

1. `scripts/larch-log.sh::round_artifact_included` — deny `findings.md`, `accepted-findings.md`, `oos.md`, `rejected-findings-full.md` (keep `oos-accepted-review.md`, `review-round-summary.md`, `voting-tally.md`, `findings-classification.tsv`, `rejected-findings.md` headline list).
2. Producers keep writing the working files in `$IMPLEMENT_TMPDIR` (the in-run review loop still uses them); only the committed staging changes.
3. `plan-goals-test.md`: remove from `scripts/larch-log-batches.sh`, `docs/run-logs-required-files.tsv` (audit `required-file-presence`), `scripts/verify-run-log-completeness.sh`, and the `docs/run-logs.md` batch section. The plan remains readable at the tracking issue (`larch:plan` block) — note in docs that issue-body edits after the run are possible, accepted by design.
4. Vote-output cap + codex-impl-transcript trim at staging time (deterministic truncation with byte-count markers).
5. **Retroactive sweep included in this issue** (one log-only PR): apply the same deletions/caps to all committed run dirs. Deletions are pure projections — `jq` over `review-findings-full.jsonl` reconstructs any dropped view exactly. Legacy runs predating `review-findings-full.jsonl` (n≈200 with no jsonl): keep their markdown findings files (they are the only copy there) — the sweep deletes a projection only where the canonical store exists.
6. Provide a tiny read-side helper (`scripts/render-findings-view.sh <run-dir> [accepted|rejected|oos|all]`) that renders the dropped markdown views from the jsonl on demand, so browsing convenience survives.

## Consumer safety

- Audit scans: `exon` (voting-tally.md kept), `oos-category-mangle`/`rej-category-blank` (jsonl kept), `oos-silent-drop` (oos-accepted-review.md kept), `required-file-presence` (TSV updated in the same PR as the rule change; the scan registry row for `plan-goals-test.md` removed).
- `/report-tokens`: untouched (`token-report.json`, `manifest.json`).
- `docs/run-logs.md` + `scripts/larch-log.md` updated to name `review-findings-full.jsonl` as the single canonical finding store.

## Expected effect

Corpus: ≈ −39 MB (132 → ~93 MB) and a materially simpler "what is canonical" story. New runs: ~−35–45% on the post-#3708 baseline.

## Test plan
(no test plan section in plan-file)
