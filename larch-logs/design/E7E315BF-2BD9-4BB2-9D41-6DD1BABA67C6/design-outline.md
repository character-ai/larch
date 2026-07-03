## Proposed Design Outline

### Goals
- Retrospective difficulty-calibration analyzer: join committed `difficulty-rating.json` records with realized run outcomes and report predicted-vs-realized calibration.
- New diagnostic-only verb `python3 python/cli.py difficulty-calibration analyze` plus a thin `/difficulty-calibration` skill entry point, mirroring `/voter-calibration`.
- Emit all six reports: confusion matrix per skill and per rater, under-rating misses with links, per-tier cost and latency, audit-run deltas, escalation statistics, tier-distribution drift.

### Non-goals
- No changes to thresholds, panels, points, or any live run behavior; diagnostic only.
- No new run-time log writers or artifacts; reads committed `larch-logs/` only.
- No severity-based realized formula; severities are excluded on purpose.

### Approach sketch
- New module in `python/larch/calibration/` (sibling to `difficulty.py`), registered in the `python/larch/cli.py` dispatch table as `("difficulty-calibration", "analyze")`.
- Per-run join: `difficulty-rating.json` + findings-classification TSVs (implement `round-N/`, design `plan-review/round-N/`, review `review-findings-classification-round-N.tsv`) + token/timing reports + `larch-logs/rejected-analysis-verdicts.tsv`.
- Realized tier per the issue formula: escalated, substantiality trip, or >= 3 accepted in-scope findings → HARD; 0 accepted → TRIVIAL; else MODERATE.
- Markdown report on stdout with `--log-root` / `--out` flags; skill stays a thin coordinator over the verb.
- Offline synthetic-fixture harness plus pytest coverage; degrade gracefully on pre-initiative and gc-slimmed dirs.

### Surfaces in scope
- `python/larch/calibration/` (new analyzer module), `python/larch/cli.py` (dispatch row), `python/tests/calibration/`.
- `skills/difficulty-calibration/SKILL.md` (new skill), README.md skill matrix, `docs/skills.md`, `docs/linting.md` (harness row), Makefile test target.

### Open questions
- Substantiality-gate trips lack an explicit committed key; drafting must pick a committed proxy (escalations array, round counts, or round-summary artifacts) and tolerate its absence.
