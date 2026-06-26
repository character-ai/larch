## Proposed Design Outline

### Goals
- New `skills/rejected-analysis/` skill with a `--n DAYS` interface: collect borderline-rejected code-review findings, pre-filter cheaply, verify per-finding via an Agent, cluster confirmed findings into coherent issues, file via `/issue`, and record to a committed idempotency ledger.
- Python-first core in `python/rejected_analysis.py` (frozen dataclasses, typed, offline-testable) behind `python/cli.py rejected-analysis <verb>`.
- Idempotency ledger at `larch-logs/rejected-analysis-ledger.tsv` (committed, content-hashed) that makes re-runs incremental and file-nothing on repeat windows.

### Non-goals
- `/design` plan-review rejections (v1 scope: code-review only, from `larch-logs/implement/` and `larch-logs/review/`).
- Voter performance scoring (stays in `/voter-calibration`).
- `--dry-run` flag or approval gate (v1 keeps `--n DAYS`-only interface; safety is the verify bar + ledger + `/issue` dedup).

### Approach sketch
- **Collector**: scan `larch-logs/{implement,review}/*/review-findings-full.jsonl`, filter by `manifest.json::started_at` within N days, keep `outcome=rejected` rows with ≥1 YES vote (from `findings-classification.tsv`); log dropped counts.
- **Pre-filter**: dedup by (file+concern hash) across runs; probe open GitHub issues for coverage; demote findings whose target file was touched by a post-run merge commit; sort high-severity (major/blocker) to front; cap at 100 advancing to verify.
- **Verify**: one Agent per surviving finding reads current file at the cited location and returns `confirmed`/`stale`/`already-fixed`; only `confirmed` proceed.
- **Cluster + file**: group confirmed findings by subsystem/file-area with a per-issue size cap; delegate batch to the `/issue` Skill tool with provenance in each issue body.
- **Record**: append every triaged finding (with verdict and disposition) to `larch-logs/rejected-analysis-ledger.tsv`; emit a voter-verdicts sidecar for `/voter-calibration` consumption.

### Surfaces in scope
- `skills/rejected-analysis/SKILL.md` (thin coordinator)
- `skills/rejected-analysis/scripts/rejected-analysis.sh` (thin wrapper → `python/cli.py rejected-analysis run`)
- `python/rejected_analysis.py` (collector, pre-filter, clustering, ledger; frozen dataclasses per G-Py-1)
- `python/cli.py` (new `rejected-analysis` domain per G-CLI-1)
- `python/test_rejected_analysis.py` (collector, pre-filter, ledger, clustering coverage)
- `larch-logs/rejected-analysis-ledger.tsv` (committed idempotency ledger; gitignored? — open)

### Open questions
- Should the per-finding verify Agent be a shared Python module (for #5468 reuse) from the start, or inline in `rejected_analysis.py` and extracted later?
- Ledger gitignore: the ledger must be committed (issue requirement) — does it need an explicit `.gitignore` exclusion carve-out or does it land directly in the tracked tree?
