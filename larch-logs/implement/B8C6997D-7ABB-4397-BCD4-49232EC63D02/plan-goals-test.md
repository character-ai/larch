## Goal
Implement issue #3709: [IMPLEMENTING] logs-size-reduction: Phase 2: retroactive cleanup of committed /implement run logs\n\n## Context.

## Implementation Plan
## Context

Phase 2 of the logs-size-reduction series for `/implement`: retroactively prune committed `larch-logs/implement/` run dirs. **Blocked on #3708** (Phase 1) — the retroactive deletion/transform set must match the finalized publish-time rule set. Companion `/design` issues: #3705 / #3706.

Committed `larch-logs/implement/` today: 608 run dirs, **216.6 MB actual bytes / 51,699 files** (~342 MB on disk).

## Simulated cleanup (classifier run against all 608 committed dirs)

| Action | Bytes | Files |
|---|---|---|
| Delete `round-N/dyn-*-prompt.md` (rendered dynamic-reviewer prompts; context duplicated per archetype) | −61.2 MB | −1,477 |
| Delete `round-N/aggregator-output.txt` where byte-identical to sibling `findings.md` (`cmp -s` guard, keep on mismatch) | −3.9 MB | −~430 |
| Delete `scout-round*-manifest.json.raw` (byte-dup of cooked `.json`) | −1.7 MB | −511 |
| Delete refresh sidecars (`token-report-refresh.json`, `timing-report-refresh.json`, `session-transcript-refresh.*`) | −0.5 MB | −105 |
| Delete `cursor-specialist-*-output-phase*.txt` / `-retry.txt` (deny-gap variants; **keep `-ns-retry`** — audit anomaly signal) | −0.8 MB | −187 |
| Delete stray `python/larch-logs/` run tree (root-cause bug filed separately) | −3.2 MB | −320 |
| Re-render `session-transcript.jsonl` with the Phase 1 trim policy (content rewrite, file kept; deterministic transform of `tool_call` blocks) | −13 MB (−37% of 35.9 MB) | 0 |
| Concatenate `breadcrumbs/larch-quiet-*.log` → one `quiet.log` per run | ~0 (0.9 MB kept) | −5,330 (5,512 → 182) |
| Optional stretch: rewrite `code-review-tally.json` bodies to drop embedded rejected-findings prose (3rd copy; jq transform of `.body`) | −~3.5 MB | 0 |
| **Total** | **≈ −85 MB of 216.6 (−39%)** | **≈ −8,300 of 51.7K (−16%)** |

Result: `larch-logs/implement/` lands at ~132 MB actual / ~43.4K files. Combined with the `/design` Phase 2 (#3706), the whole `larch-logs/` tree drops from ~340 MB / 106K files to ~188 MB / ~65K files (working tree `du`: ~576 → ~310 MB).

## Guards

- **Preserve every `docs/run-logs-required-files.tsv` row** — the audit `required-file-presence` scan checks existence per run dir; nothing in the deletion set is a required file (verified). Transforms (transcript re-render, tally rewrite) keep the files present.
- **Keep `*-ns-retry*.txt`** — the `ns-retry-sidecars` audit scan reads their presence as the anomaly evidence.
- Keep `review-findings-full.jsonl`, `round-N/findings.md`, `voting-tally.md`, `panel-manifest.ndjson`, `coder.env`, `codex-generalist-output.txt`, `oos-accepted*.md`, `oos-issues.ndjson`, `codex-impl-transcript*.txt`, token/timing reports, `execution-issues.ndjson` — all read by audit scans, `/report-tokens`, or core forensics.
- Transcript re-render must preserve assistant text blocks untouched (`oos-silent-drop` greps `Inline-triage rule` prose from `session-transcript.jsonl`).
- Ship as a dedicated **log-only PR** per `docs/run-logs.md` bulk-edit guidance; disclose the bulk nature in the PR title/body. The `python/larch-logs/` deletion is outside `larch-logs/` — call it out explicitly in the PR body.
- **No git history rewrite** (no `filter-repo`); the win is working-tree size, file count, and cheaper LLM scans.
- Deterministic classify-then-transform script; byte-identity deletions verify with `cmp -s` before deleting, keep on mismatch.


## Test plan

- `/report-tokens --skill=implement` scans clean after the PR.
- `.claude/skills/audit-runs/scripts/audit-scan-run.sh --skill implement` passes on a sample of surviving dirs (including `required-file-presence` and `oos-silent-drop`).
- `bash scripts/relevant-checks.sh` passes.
- Spot-check one multi-round run: findings → classification → votes → tally → accepted/rejected/OOS chain intact; re-rendered transcript parses (header `v` bump) and still contains assistant prose.
