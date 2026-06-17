# render-review-phase-detail.sh

Renders the **Review Phase Detail** markdown section appended to the
`/implement` final report and the `/design` final summary (issue #3774). It summarizes the multi-round code
review: one table row per review round, a Total row, the top-N reviewers by
suggestions accepted, and a count of failed reviewer slots — each broken down
by `vendor/archetype`.

## Primary caller

`python/pr_body.py::write_final_report` appends the section to `/implement`
final reports. `python/design_summary.py::render_final_summary_main` appends the
section to `/design` final summaries. `python/progress_report.py` invokes the
same renderer for live progress reporting.

Final-report callers append the section after the `<!-- larch:run-summary v=1 -->`
sentinel in `summary-final.md` / the tracking-issue `larch:final-summary`
comment.

## Inputs / argv

| Flag | Required | Meaning |
|------|----------|---------|
| `--rounds-root DIR` | yes | Directory containing `round-<N>/` subdirs (live: `$IMPLEMENT_TMPDIR`; committed: the run-log dir). |
| `--findings-file F` | no | `review-findings-full.jsonl` for top-reviewer attribution. |
| `--timing-ledger F` | no | `timing-ledger.tsv`; per-round `type=round` rows supply the Time column through the `--skill`-filtered table window, per-round Cost attribution through the same filtered table window, and reviewer timing chart candidate windows through the unfiltered Gantt window. |
| `--token-ledger F` | no | `larch-tokens-<hash>.jsonl`; vendor token records (timestamp-windowed to each round) supply the per-round vendor Cost column. |
| `--skill implement\|design` | no | Default `implement`; `design` renders the same table from design plan-review round artifacts. |
| `--top-n N` | no | Top-reviewers cap (default `7`). |
| `--no-gantt` | no | Suppress ASCII reviewer timing charts only. Intended for callers that need table-only output. |
| `--output F` | no | Write the section to `F`; otherwise print to stdout. |

## Data sources (per round)

- **Counts** — `round-<N>/round-meta.json` `.tally`: suggestions made =
  `ACCEPTED_COUNT + REJECTED_COUNT + EXONERATED_COUNT + NEUTRAL_COUNT`; accepted =
  `ACCEPTED_COUNT`; OOS proposed = `OOS_ACCEPTED_COUNT + OOS_REJECTED_COUNT`; OOS
  accepted = `OOS_ACCEPTED_COUNT`. Falls back to `.summary.finding_counts`. Because
  reclassified-OOS findings are tallied under `OOS_*` (not `ACCEPTED/REJECTED/
  EXONERATED`), "suggestions reclassified to OOS count against OOS, not
  suggestions" is satisfied by the source tally itself.
- **Reviewers launched** — `round-<N>/round-meta.json` `.summary.panel.total_slot_count`
  (falls back to `static_slot_count + dynamic_slot_count`).
- **Time** — `timing-ledger.tsv` `type=round` rows are filtered by `--skill`
  for the table window, then measured as `max(end_s) - min(start_s)` per round
  number, column 6. Renders `—` when no ledger / round timing is present
  (committed logs do not carry the ledger).
- **Reviewer timing charts**: `timing-ledger.tsv` `type=vendor` rows provide
  round-agent task windows. Column 8 is `start_s`; column 9 is `end_s`. Round
  windows aggregate `type=round` rows by round number only and are not filtered
  by `--skill`. Vendor rows are selected by overlap only and are not filtered by
  `--skill`. The chart is a filtered round-agent view: reviewers, aggregators,
  voters, scouts, and apply coders appear when they already emit chartable vendor
  rows. CI-fix, CI-test, CI-output, verification, and launcher probe timing rows
  are excluded before sorting and before the 25-task cap. Excluded basenames
  include `ci.out`, `*-ci.out`, `ci-fix-*.out`, `claude.out`, `codex.out`, and
  `cursor.out`. Apply coder rows render as `codex/apply` or `cursor/apply` by
  task kind. `/design` plan-review apply rows use the existing
  `codex-plan-autofix` / `cursor-plan-autofix` vendor timing from
  `plan revise-waterfall`, with `codex-output.txt` / `cursor-output.txt`
  outputs. Matching rows are clamped to absolute round bounds before TSV
  emission. The shell sorts by absolute `start_s`, then absolute `end_s`, then
  label with a tab-delimited sort because label is the first TSV field. It caps
  at 25 displayed tasks after sorting. Chart axes and title spans use the
  ledger `gantt_rrange` round window (`gw_start` / `gw_end` from unfiltered
  `type=round` rows), not `round-meta.json` and not the displayed-task min/max.
  The table Time column still uses the `--skill`-filtered round timing row. A
  tail gap can remain when post-apply verification time is uncharted.
- **Cost** — the per-round **vendor** cost (Codex + Cursor + Claude subprocess).
  Per-round Cost attribution uses the same `--skill`-filtered table window as
  Time. Vendor token records from `--token-ledger` are attributed to a round by
  timestamp window (`jq fromdateiso8601` on each record's `ts` against the
  round's epoch `start_s`/`end_s` from `timing-ledger.tsv`), summed per vendor,
  and priced with `python/report_tokens_cost.py` (the ledger's combined `cache_create` is mapped
  to the 5m cache-write bucket). It **excludes** main-agent Claude, so it is the
  per-round vendor spend and is less than the run-total dollar-primary Cost line
  in the summary (which additionally includes main-agent Claude) — i.e. it is a
  distinct datum, not a duplicate of that single-source line. Renders `—` when
  the token ledger or per-round timing is unavailable, and `$0.00` when the
  ledger is present but no vendor records fall in the round's window. The Total
  row sums the per-round vendor costs.

## ASCII timing format

Reviewer timing uses plain fenced ASCII charts. The Python renderer owns bars,
axis placement, and box drawing. The shell script owns timing-ledger extraction,
round windowing, row cap, sorting, label attribution, absolute clamping before
TSV emission, and best-effort subprocess failure handling.

The shell-to-CLI contract is absolute-time based: TSV `start_s` and `end_s` are
absolute clamped overlap bounds, and `--window-start-s` / `--window-end-s` use
the ledger `gantt_rrange` round window. Relative offsets are not accepted at
this call site. Chart title windows use `m:ss`, not the table `fmt_hms` output.

Renderer non-zero status, an unreadable CLI path, or missing `python3` must not
abort the report. The no-task note means no overlapping rows were extracted, or
a successful renderer returned no rows. Renderer failure must not be misreported
as no overlapping tasks.

## Vendor/archetype attribution

`round-<N>/panel-manifest.ndjson` maps each reviewer output basename to
`tool/slot` (vendor/archetype) — authoritative, including dynamic slots. The
top-reviewers pass joins accepted findings' `reviewer_slots` basenames (from
`review-findings-full.jsonl`, with a `reviewer` singular fallback for older
schema) against that map; a basename-parsing fallback (`derive.awk`) handles
basenames absent from the map. `derive.awk` normalizes the basename to lowercase
before pattern matching so mixed-case dynamic slot names (e.g. `Cursor-dyn-*`)
are attributed correctly instead of falling through to `unknown/`. Failed slots come from `round-meta.json`
`.collector` blocks whose `STATUS` is non-empty and not `OK`, attributed by the
block's `TOOL` plus archetype from the `REVIEWER_FILE` basename.

## Output / exit codes

- Renders the section to `--output` (or stdout) and exits `0`.
- Omitted `--rounds-root` remains a usage error and exits `2`.
- Valid readable roots with zero completed rounds render `## Review Phase Detail`
  plus `No review rounds completed.`. Existing in-flight `round-<N>/`
  directories without completed metadata use the same no-completed-round message.
- Provided missing roots, unreadable roots, missing `jq`, unreadable artifacts, or
  partial data degrade gracefully and still exit `0` with empty or partial output.
- ASCII Gantt charts appear after the table and before `**Top reviewers**` unless
  `--no-gantt` is passed. Missing timing ledgers mean no charts. Rounds without
  usable round windows omit that round chart. A usable round window with no
  overlapping vendor rows renders a short no-task note under that round timing
  heading.

## `/design` scope

`/design` plan-review now feeds this renderer through `python/cli.py design render-final-summary --skill design`. `scripts/write-design-round-meta.sh` emits per-round `round-meta.json` and `panel-manifest.ndjson` under `plan-review/round-N/` from snapshotted `voting-tally.md`, fallback `findings-classification.tsv`, and `plan-review-slots.ndjson`; it never reads mutable session-root tally files for counts. The design tally contract uses the same six keys as implement (`ACCEPTED_COUNT`, `REJECTED_COUNT`, `EXONERATED_COUNT`, `NEUTRAL_COUNT`, `OOS_ACCEPTED_COUNT`, `OOS_REJECTED_COUNT`) and `summary.panel.total_slot_count`. When collection fails before reviewer records exist, the writer inserts placeholder collector blocks with `TOOL=unknown`, `STATUS=FAILED`, and `REVIEWER_FILE=collector-failure-N.txt`, allowing the failed-slot count to render instead of a false zero. The Python final-summary helper points at an existing design `review-findings-full.jsonl` when present; it does not compose a new findings file before invoking this renderer.

## Harness

`scripts/test-render-review-phase-detail.sh` (Makefile target
`test-render-review-phase-detail`, shard `test-harnesses-2`).

## Edit-in-sync

- `python/pr_body.py` (`python/cli.py final-report write`).
- `python/design_summary.py` (`python/cli.py design render-final-summary`).
- `python/review_phase_detail.py`.
- `skills/implement/scripts/test-write-final-report.sh`.
- `python/progress_report.py` and `python/test_progress_report.py`.
- `scripts/test-render-review-phase-detail.sh` (+ `.md`) and the Makefile target /
  shard registration.
