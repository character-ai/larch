# Difficulty Rating

Difficulty rating records model judgment for each larch run. It is not a computed complexity score.

## Tiers

- **TRIVIAL**: localized, low-risk edits with obvious validation.
- **MODERATE**: multi-file or workflow-affecting changes with integration risk.
- **HARD**: cross-cutting lifecycle, security-sensitive, concurrency, CI, merge, or prompt-contract changes with high blast radius.

## Confidence

Raters emit `confidence` as `low`, `medium`, or `high`. Low confidence bumps the recorded tier by one level, capped at `HARD`.

## Seeded examples

These examples seed the rubric from committed run-log evidence and are refreshed when calibration misses identify better anchors.

| Tier | Examples |
|---|---|
| `TRIVIAL` | `run-2026-06-27-doc-typo`: doc-only stale phrase. `run-2026-06-29-test-pin`: single harness literal refresh. `run-2026-07-01-small-cli`: one bounded flag-parser test. |
| `MODERATE` | `run-2026-06-28-review-prune`: review-loop metadata. `run-2026-06-30-design-trailer`: plan trailer validation. `run-2026-07-01-run-log-batch`: persisted run-log batch. |
| `HARD` | `run-2026-06-26-ship-merge`: merge routing. `run-2026-06-30-redaction`: secret handling. `run-2026-07-02-session-bootstrap`: session-env materialization. |

## Floors

`docs/difficulty-floor-globs.tsv` is the only mechanical floor source. Floors raise only. They never lower a model tier. The seeded floor globs force at least `MODERATE` for hooks, redaction or secret handling, ship and merge drivers, session-env writers, and CI workflows.

This issue is instrumentation only. The companion tiered-panels work may later use the rating for routing, but this change does not change panel size or behavior.

## `difficulty-rating.json`

Each record is a JSON object with `schema_version: 1` and these fields:

- `rater`, `rater_tool`, `rater_model`.
- `predicted_tier`, `confidence`, and bounded `rationale`.
- `design_tier` and `implement_tier` when available.
- `applied_tier`, the most severe of design, implement, fallback, and floors.
- `override_source`, usually `none` or `floor`.
- `floors_applied`, a list of matched path/glob/floor/reason rows.
- `audit_upgrade`, `escalations`, and `panel_skipped` for later analysis.
