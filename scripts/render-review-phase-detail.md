# render-review-phase-detail.sh

Renders the **Review Phase Detail** markdown section appended to the
`/implement` final report and the `/design` final summary (issue #3774). It summarizes the multi-round code
review: one table row per review round, a Total row, the top-N reviewers by
suggestions accepted, and a count of failed reviewer slots — each broken down
by `vendor/archetype`.

## Primary caller

`skills/implement/scripts/write-final-report.sh` invokes it before composing the
`render-run-summary.sh --note-lines-file` appendix and `cat`s the result into the
note block, so the section lands after the `<!-- larch:run-summary v=1 -->`
sentinel in `summary-final.md` / the tracking-issue `larch:final-summary` comment.

## Inputs / argv

| Flag | Required | Meaning |
|------|----------|---------|
| `--rounds-root DIR` | yes | Directory containing `round-<N>/` subdirs (live: `$IMPLEMENT_TMPDIR`; committed: the run-log dir). |
| `--findings-file F` | no | `review-findings-full.jsonl` for top-reviewer attribution. |
| `--timing-ledger F` | no | `timing-ledger.tsv`; per-round `type=round` rows supply the Time column **and** the per-round cost window. |
| `--token-ledger F` | no | `larch-tokens-<hash>.jsonl`; vendor token records (timestamp-windowed to each round) supply the per-round vendor Cost column. |
| `--skill implement\|design` | no | Default `implement`; `design` renders the same table from design plan-review round artifacts. |
| `--top-n N` | no | Top-reviewers cap (default `7`). |
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
- **Time** — `timing-ledger.tsv` `type=round` rows (`max(end_s) - min(start_s)` per
  round number, column 6). Renders `—` when no ledger / round timing is present
  (committed logs do not carry the ledger).
- **Cost** — the per-round **vendor** cost (Codex + Cursor + Claude subprocess).
  Vendor token records from `--token-ledger` are attributed to a round by
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

## Vendor/archetype attribution

`round-<N>/panel-manifest.ndjson` maps each reviewer output basename to
`tool/slot` (vendor/archetype) — authoritative, including dynamic slots. The
top-reviewers pass joins accepted findings' `reviewer_slots` basenames (from
`review-findings-full.jsonl`, with a `reviewer` singular fallback for older
schema) against that map; a basename-parsing fallback (`derive.awk`) handles
basenames absent from the map. Failed slots come from `round-meta.json`
`.collector` blocks whose `STATUS` is non-empty and not `OK`, attributed by the
block's `TOOL` plus archetype from the `REVIEWER_FILE` basename.

## Output / exit codes

- Renders the section to `--output` (or stdout) and exits `0`.
- When there are no numeric `round-<N>/` dirs with a `round-meta.json` (e.g.
  `--self-review` runs, or review skipped), it renders **nothing** (empty output)
  and exits `0`, so the final report is unchanged.
- Observability-only: missing `jq`, unreadable artifacts, or partial data
  degrade gracefully and still exit `0`. Usage / bad-argument errors exit `2`.

## `/design` scope

`/design` plan-review now feeds this renderer through `skills/design/scripts/render-final-summary.sh --skill design`. `scripts/write-design-round-meta.sh` emits per-round `round-meta.json` and `panel-manifest.ndjson` under `plan-review/round-N/` from snapshotted `voting-tally.md`, fallback `findings-classification.tsv`, and `plan-review-slots.ndjson`; it never reads mutable session-root tally files for counts. The design tally contract uses the same six keys as implement (`ACCEPTED_COUNT`, `REJECTED_COUNT`, `EXONERATED_COUNT`, `NEUTRAL_COUNT`, `OOS_ACCEPTED_COUNT`, `OOS_REJECTED_COUNT`) and `summary.panel.total_slot_count`. When collection fails before reviewer records exist, the writer inserts placeholder collector blocks with `TOOL=unknown`, `STATUS=FAILED`, and `REVIEWER_FILE=collector-failure-N.txt`, allowing the failed-slot count to render instead of a false zero. `render-final-summary.sh` composes design `review-findings-full.jsonl` before invoking this renderer.

## Harness

`scripts/test-render-review-phase-detail.sh` (Makefile target
`test-render-review-phase-detail`, shard `test-harnesses-2`).

## Edit-in-sync

- `skills/implement/scripts/write-final-report.sh` and
  `skills/implement/scripts/write-final-report.md`.
- `skills/design/scripts/render-final-summary.sh` and
  `skills/design/scripts/render-final-summary.md`.
- `scripts/test-render-review-phase-detail.sh` (+ `.md`) and the Makefile target /
  shard registration.
