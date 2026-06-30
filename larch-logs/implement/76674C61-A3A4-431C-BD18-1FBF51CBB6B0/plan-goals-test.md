## Goal
Implement issue #5853: [IMPLEMENTING] Retro-fix Cursor pricing on run-logs already checked in.

## Implementation Plan
## Summary

Committed run logs embed Cursor dollar figures computed at the **old, un-surcharged** Cursor rates (~2x too low). After the pricing machinery is corrected (#5854), retro-fix the dollar figures already checked into `larch-logs/` so historical cost reporting reflects actual Cursor spend.

## What is wrong

`/design` and `/implement` write a `**Cost**` line into each run's `final-summary.md`, e.g.:

```
- **Cost**: 💰 TOTAL ~$37.54 — Claude $24.71, Codex $11.01, Cursor $1.82, Claude (subprocess) $0.00  |  Tokens: 38810k
```

The `Cursor $X` component (and therefore the `TOTAL`) was priced at composer-2.5 list ($0.50 / $0.20 / $2.50) with **no Teams $0.25/M surcharge**, so it understates the Cursor lane by roughly 2x (cache reads, ~91% of Cursor tokens, are the dominant error: $0.20 vs actual ~$0.45). The same stale figure is mirrored into each run's tracking-issue `larch:final-summary` comment.

Scope of affected committed artifacts:

- ~**1,040** `larch-logs/{design,implement}/*/final-summary.md` files contain a Cursor dollar figure in the `**Cost**` line (out of ~1,593 runs with token reports).
- The corresponding tracking-issue `larch:final-summary` comments (live projections of the same line).

## What is NOT affected (important — narrows scope)

- **Token counts are correct.** `token-report.json` / `token-report-final.json` store token *counts* (`BUCKETS_cursor`), not dollars. `/report-tokens` prices them at analysis time, so once #5854 lands it **auto-reprices all history correctly with no log rewrite**. No need to touch `token-report*.json`.
- This issue is therefore only about the **embedded dollar text** in `final-summary.md` and the tracking-issue summary comments — the figures a human reads directly without re-running `/report-tokens`.

## Approach

- Land #5854 first (corrected rates are the prerequisite).
- Recompute each affected run's `**Cost**` line from its committed token counts at the corrected rates (reuse `python/cli.py render run-summary` so the format stays byte-identical except the numbers), and rewrite the `final-summary.md` files in place.
- Ship as a **log-only PR** (mirror `/gc-run-logs`): per `docs/run-logs.md` "Plan scope and committed logs", bulk `larch-logs/` edits belong in a dedicated log-only PR so plan-to-diff review stays traceable; do not mix with runtime-surface changes.
- Optionally refresh the tracking-issue `larch:final-summary` comments via the existing upsert path; treat as a separate, best-effort pass (gh API mutation, idempotent on the marker).

## Acceptance criteria

- All affected `final-summary.md` `**Cost**` lines show surcharged Cursor figures and corrected `TOTAL`; diff is limited to the cost numbers.
- A spot-check run's recomputed `Cursor $X` matches `/report-tokens` output for that run under the corrected rates.
- Change ships as a log-only PR; no runtime-surface files touched.

## Open questions

- Backfill the tracking-issue `larch:final-summary` comments too, or only the committed `final-summary.md` files? (Comments are the canonical live projection but require gh mutations across ~1,000 issues.)
- Apply only to runs in the period where the Teams surcharge was in effect, or to all history? (The surcharge is plan-tier-specific; if the plan/tier changed over time, a single rate may misprice older runs.)

## Related

- #5854 — corrected pricing machinery (hard prerequisite).
- #5855 — switching to Auto changes the rate model going forward (does not affect this backfill).
- #5852 — adjacent `token-report.json` serialization bug (`totals.cache_read` null); independent of this backfill.

## Test plan
(no test plan section in plan-file)
