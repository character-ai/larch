## Goal
Implement issue #3716: [IMPLEMENTING] logs-size-reduction: Phase 3c: consolidate per-round sidecars and archetype definitions\n\n## Context.

## Implementation Plan
## Context

Phase 3c of the logs-size-reduction series: structural consolidation of the long tail — thousands of tiny per-round sidecar files and repeated dynamic-archetype definitions. The byte win is modest (~4–5 MB) but the **file-count win is large** (several thousand files), which is where checkout/status/indexing cost and per-file block overhead live (~4 KB/file on disk).

Blocked on #3708 and #3705 (same staging surfaces on both skills).

## Targets (corpus-wide)

| Family | Today | Change |
|---|---|---|
| Per-round env/log sidecars — implement: `review-tally.env` (1.3 MB / 842), `collector-results.env` (0.9 / 854), `collect-agent-results.log` (0.9 / 841), `review-summary.json` (0.86 / 851), `coder.env` (0.16 / 770), `coder-*.wrapper.log` (0.4 / ~900); design: `round-summary.env`, result `.env` files | ~4.5 MB across ~5,000 tiny files | **one `round-meta.json` per round**: a single JSON object with named sections (`tally`, `collector`, `summary`, `coder`, `wrapper_logs`). Audit `coder-tool` scan migrates from `coder.env::CODER_TOOL` to `round-meta.json::coder.CODER_TOOL` (scan registry row updated in the same PR). |
| `reviewer-dyn-*.md` archetype definitions (1,477 files × 2.2 KB, heavily repeated across rounds/runs) | 3.3 MB | **content-addressed pool**: commit each unique definition once at `larch-logs/shared/archetypes/<sha256-12>.md`; rounds reference the hash from `panel-manifest.ndjson` (new `archetype_ref` field). Existing committed copies retro-migrate to the pool. |
| Remaining `scout-round*-manifest.json` near-dup chains (round N raw vs cooked already handled in #3708; this covers cross-round identical manifests) | ~0.5 MB | stage round N's manifest only when it differs from round N−1's (`cmp -s`) |

## Changes

1. `scripts/larch-log.sh write-round` + the design round stager: compose `round-meta.json` from the section files at staging time (producers keep writing individual files in the session tmpdir; only the committed shape changes).
2. Archetype pool writer with hash-dedup (idempotent: existing hash → no write) + `panel-manifest.ndjson` `archetype_ref` field; `docs/run-logs.md` documents the pool and the reference contract.
3. **Retroactive sweep included** (one log-only PR): consolidate sidecars and migrate archetype copies across all committed dirs; deterministic, reviewable transform script.
4. Audit registry: `coder-tool` scan row updated; `audit-scan-run.sh` env-field type gains a json-path variant (or the scan switches to `jq`).
5. Ripple: `scripts/larch-log.md`, `docs/run-logs.md`, harnesses (`test-larch-log*.sh`, round-artifact tests).

## Consumer safety

- No canonical content moves: findings/votes/tallies/reports untouched.
- `coder-tool` is the only audit scan reading a consolidated file; it migrates in the same PR.
- `round-meta.json` keeps every key currently present in the merged files (lossless merge).

## Expected effect

≈ −4–5 MB bytes, **≈ −6–8K files** (on top of #3708's breadcrumbs consolidation), and a flatter, cheaper-to-scan round layout.

## Test plan
(no test plan section in plan-file)
