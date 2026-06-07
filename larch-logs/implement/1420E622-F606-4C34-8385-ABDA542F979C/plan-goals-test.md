## Goal
Implement issue #3708: [IMPLEMENTING] logs-size-reduction: Phase 1: stop committing redundant /implement log artifacts\n\n## Context.

## Implementation Plan
## Context

Size audit of committed `larch-logs/implement/` (608 run dirs): **216.6 MB actual bytes across 51,699 files** (~342 MB on disk). Recent runs are already reasonably slim (~300 KB, ~70 files avg over the last 20), but the corpus-wide pattern table shows a small number of families dominate, and several of them are pure duplication that current write-time rules still commit.

This is Phase 1 of the logs-size-reduction series for `/implement`: stop generating the waste in **new** runs. Phase 2 (separate issue, blocked on this one) applies the finalized rule set retroactively. Companion `/design` issues: #3705 / #3706.

## Measured duplication (verified on committed runs)

| Corpus item | Total | Count | Finding |
|---|---|---|---|
| `round-N/dyn-*-prompt.md` | **61.2 MB (28% of corpus)** | 1,477 × 42.5 KB | each rendered dynamic-reviewer prompt re-embeds the same diff instructions + feature description + full implementation plan (already committed as `plan-goals-test.md` / `parent-issue.md`); only the small archetype section differs, and that is already captured by the committed `reviewer-dyn-*.md` definition (~2 KB). Currently **allowlisted** in `round_artifact_included` (`scripts/larch-log.sh`). |
| `session-transcript.jsonl` | 35.9 MB | 414 × 87 KB | ~2/3 of block bytes are `tool_call` input bodies (sample decomposition: Edit 37%, Bash 30%). Edit/Write inputs duplicate what the PR diff records. Measured trim: Edit/Write/NotebookEdit input → `{file_path, input_bytes}` stub + 1 KB cap on other tool inputs = **−37%** (137 → 86 KB/run on the last 20 runs) while preserving prose, Bash commands, errors, and tool sequence. |
| `round-N/aggregator-output.txt` | 4.6 MB | 541 × 8.5 KB | byte-identical to sibling `findings.md` in 8/10 recent rounds (raw aggregator output vs staged aggregate). |
| `code-review-tally.json` | 5.5 MB | 450 × 12.2 KB | `body` embeds the full `## Rejected Code Review Findings` prose — the **third copy** (also in `round-N/rejected-findings-full.md` and `review-findings-full.jsonl`). No programmatic reader consumes the body prose (audit scans read `voting-tally.md` + the JSONL). |
| `scout-round*-manifest.json.raw` | 1.7 MB | 511 | byte-identical to the cooked `.json` in 10/10 checked. |
| `token-report-refresh.json`, `timing-report-refresh.json`, `session-transcript-refresh.txt` | 0.5 MB | 105 | byte-identical to the canonical batch in 12/14 recent runs; canonical reports are refreshed at the same CI/rebase boundaries. In-loop volatile snapshots that ride into the commit via the run-tree copy. |
| `cursor-specialist-*-output-phase3.txt`, `-retry.txt` | 0.8 MB | 187 | deny-list gap: the exact-form deny (`cursor-specialist-*-output.txt`) misses phase/retry variants, which fall through to the broad `*-output-*.txt` allow. (`-ns-retry` files must stay committed — the `ns-retry-sidecars` audit scan reads their presence as an anomaly signal.) |
| `breadcrumbs/larch-quiet-*.log` | 0.9 MB | **5,512 files** | 11% of all implement files holding <1 MB — pure block-overhead/file-count waste (~20 MB on disk). |

## Consumer safety (verified against actual readers)

- `/report-tokens --skill=implement` reads `token-report.json` + `manifest.json` — unaffected.
- `audit-runs` `scans-implement.tsv`: `required-file-presence` (none of the cut files are in `docs/run-logs-required-files.tsv`), `exon` (`voting-tally.md` kept), `oos-category-mangle`/`rej-category-blank` (`review-findings-full.jsonl` kept in full), `ns-retry-sidecars` (ns-retry files kept), `cursor-ci-stall-causes` (kept), `codex-round1-adherence` (`panel-manifest.ndjson` kept), `codex-generalist-waste` (`codex-generalist-output.txt` kept), `coder-tool` (`coder.env` kept), `oos-silent-drop` (reads `session-transcript.jsonl` for `Inline-triage rule` prose — the trim policy only stubs `tool_call` inputs; assistant text blocks are untouched).
- `scripts/verify-run-log-completeness.sh` — checks required files only; unaffected.

## Proposed changes

1. `scripts/larch-log.sh::round_artifact_included` — deny `dyn-*-prompt.md` (keep `reviewer-dyn-*.md` archetype definitions and `dyn-*-output*` finding outputs).
2. Same function — close the deny gap: `cursor-specialist-*-output-phase*.txt`, `cursor-specialist-*-output-retry.txt` (and codex equivalents), explicitly keeping `*-ns-retry*.txt`.
3. `write-round` staging — stage `aggregator-output.txt` only when it differs from `findings.md` (`cmp -s` guard); same for `aggregator-output-phase*.txt` vs their staged aggregates if applicable.
4. Deny `scout-round*-manifest.json.raw` (cooked `.json` is canonical).
5. Stop committing the in-loop refresh sidecars (`token-report-refresh.json`, `timing-report-refresh.json`, `session-transcript-refresh.*`) — producer-side change in `python/run_logs.py` flush + `scripts/refresh-run-logs.sh` (write them outside the committed run tree, or delete before commit).
6. `scripts/render-session-transcript.py` — trim policy: for `Edit`/`Write`/`NotebookEdit` tool calls, replace `input` with `{file_path, input_bytes}` (PR diff carries the content); cap all other tool-call inputs at 1 KB with an `elided_bytes` marker. Bump the header `v` and document in `scripts/render-session-transcript.md`.
7. Tally composer (`scripts/write-tally.sh` / `scripts/compose-tally-record.sh` path) — drop the embedded rejected-findings prose from the `code-review-tally.json` body; keep envelope counters and round summaries (prose stays canonical in `round-N/rejected-findings-full.md` + `review-findings-full.jsonl`).
8. `larch_log_publish_breadcrumbs_shared` — concatenate per-script quiet logs into a single `breadcrumbs/quiet.log` (with per-file header lines) instead of N tiny files; shared helper also benefits `/design` publishes.
9. Ripple: `docs/run-logs.md`, `scripts/larch-log.md`, `scripts/larch-log-batches.md`, `scripts/render-session-transcript.md`, SECURITY.md breadcrumb-redaction paragraph, and the relevant `test-*` harnesses.

## Expected effect

Recent-baseline runs: ~−45–55% bytes per run (~300 → ~140–170 KB); runs with dynamic-archetype rounds cut much more (one measured round: 212 → ~74 KB, −65%). File count: −10–20 per run plus the breadcrumbs consolidation. Finalizes the rule set Phase 2 applies retroactively (−85 MB / −8,300 files projected).

## Out of scope

- Retroactive cleanup of committed logs (Phase 2 issue, blocked on this one).
- The stray `python/larch-logs/` committed run tree (root-cause bug filed separately; deletion happens in Phase 2).

## Test plan
(no test plan section in plan-file)
