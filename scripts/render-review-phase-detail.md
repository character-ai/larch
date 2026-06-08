# render-review-phase-detail.sh

Renders the **Review Phase Detail** markdown section appended to the
`/implement` final report (issue #3774). It summarizes the multi-round code
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
| `--timing-ledger F` | no | `timing-ledger.tsv`; per-round `type=round` rows supply the Time column. |
| `--skill implement\|design` | no | Default `implement`. Reserved for a future `/design` per-round path (see below). |
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
- **Cost** — always `—`. The dollar-primary cost line is owned exclusively by
  `render-run-summary.sh` (single-source dollar-line invariant), and per-round
  token attribution is not instrumented (the token ledger has no per-round
  delimiters). A footnote points readers at the run **Cost** line.

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

`/design`'s plan-review currently produces no `round-<N>/round-meta.json` and no
`review-findings-full.jsonl` (different data model), so this helper is wired into
`/implement` only. Extending it to `/design` requires upstream instrumentation of
the design plan-review loop (per-round metadata + a `compose-review-findings.sh`
call on the design path); the `--skill design` flag is accepted so the wiring is
forward-compatible.

## Harness

`scripts/test-render-review-phase-detail.sh` (Makefile target
`test-render-review-phase-detail`, shard `test-harnesses-2`).

## Edit-in-sync

- `skills/implement/scripts/write-final-report.sh` (caller) and
  `skills/implement/scripts/write-final-report.md`.
- `scripts/test-render-review-phase-detail.sh` (+ `.md`) and the Makefile target /
  shard registration.
