## Goal
Implement issue #3706: [IMPLEMENTING] logs-size-reduction: Phase 2: retroactive cleanup of committed /design run logs\n\n## Context.

## Implementation Plan
## Context

Phase 2 of the logs-size-reduction series: retroactively prune committed `larch-logs/design/` run dirs. **Blocked on #3705** (Phase 1) — the retroactive deletion set must match the finalized publish-time rule set, so the rules land first and this issue applies them historically in one bulk log-only PR.

Committed `larch-logs/design/` today: 245 run dirs, **123.0 MB actual bytes / 54,721 files** (~234 MB on disk; ~47% of `du` is 4K-block waste from tiny files). Most bytes are legacy debris that current publish rules no longer produce (pre-#3534 rendered prompts, raw lane outputs + sidecar swarms, and `revise/` trees from the since-removed inter-round revise mechanism).

## Simulated cleanup (classifier run against all 245 committed dirs)

| Rule class | Bytes | Files |
|---|---|---|
| A: apply today's exclusions retroactively (`render-plan-*.prompt`, raw lane outputs + sidecars, `revise/` trees, quiet logs) | −55.3 MB | −29,176 |
| B: apply Phase-1 (#3705) rules retroactively (derived/static/intermediate artifacts; delete round≥2 `plan.txt` outright — do not generate historical diffs) | −24.1 MB | −3,210 |
| C: top-level review artifacts byte-identical to the final round copy | ~−3 MB | ~−700 |
| Rider: delete `larch-logs/measure-md-cost/` (stale one-off markdown token-cost snapshot from 2026-05-18; reproducible on demand via `scripts/measure-md-cost.sh`) | −0.1 MB | −1 |
| **Total** | **≈ −80 MB of 123 (−67%)** | **≈ −33K of 54.7K (−60%)** |

Result: `larch-logs/design/` lands at ~40 MB actual / ~21.5K files (du ~234 → ~75–80 MB).

## Guards

- **Skip any run dir containing `pause-state.txt`** — paused runs restore their session tmpdir from the committed snapshot on resume (`scripts/design-pause-load.sh`); deleting their files breaks resume.
- Ship as a dedicated **log-only PR** per `docs/run-logs.md` bulk-edit guidance; disclose the bulk nature in the PR title/body so reviewers can separate log churn from substantive work.
- **No git history rewrite** — old blobs stay in the pack (whole-repo pack is 97 MB, already delta-compressed). No `git filter-repo`: it would break every PR link and run-log commit reference for marginal pack savings. The win is working-tree size, file count (status/checkout/indexing speed), and cheaper LLM scans over `larch-logs/`.
- Deletion must be deterministic and reviewable: a classify-then-delete script whose output is fully visible in the PR diff. Byte-identity rules (class C, `composed-plan.redacted.md`, `ballot.txt`) must verify with `cmp -s` before deleting, falling back to keep on mismatch.


## Test plan

- `/report-tokens --skill=design` scans clean after deletion (reads `manifest.json`, `token-report-final.json`, `timing-report-final.json`, `run-params.json` — all retained).
- `.claude/skills/audit-runs/scripts/audit-scan-run.sh --skill design` passes on a sample of surviving dirs (design registry reads `manifest.json` only).
- `bash scripts/relevant-checks.sh` passes (no lint regressions from removed files).
- Spot-check one multi-round run dir: findings → classification TSV → vote outputs → tally → accepted/rejected → round-1 plan retained.
