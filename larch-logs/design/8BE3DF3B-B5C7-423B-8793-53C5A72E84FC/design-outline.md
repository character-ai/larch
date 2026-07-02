## Proposed Design Outline

### Goals
- Capture a TRIVIAL/MODERATE/HARD rating on every /implement, /review, /design run; commit it as `difficulty-rating.json`.
- Extend run-log schema (round-meta, panel-manifest, final-summary) plus the tracking-issue wire field and label so ratings are analyzable.
- Keep panel behavior unchanged. Instrumentation only.

### Non-goals
- No tier-adaptive panel routing or escalation behavior (the tiered-panels child owns that).
- No computed complexity meter. Rating stays pure model judgment.
- No backfill of past runs. Forward-only.

### Approach sketch
- One shared core `python/larch/calibration/difficulty.py` plus a `difficulty` cli.py verb: Tier domain type, confidence bump, mechanical floors, applied-tier, record and batch write.
- Register a `difficulty-rating` run-log batch; add it to the required-files TSV and gc keep sets.
- Rate at each site: /design plan writer stamps a wire field and `difficulty:<tier>` label; /implement coder self-rates in its manifest (plus a Claude main-agent branch); /review scout emits a rating.
- Add per-slot vendor and resolved model to panel-manifest; add a `difficulty` section to round-meta; add a `- **Difficulty**:` bullet to each final-summary.

### Surfaces in scope
- `python/larch/calibration/`, `python/larch/report/` (run_log_batch, gc_run_logs, progress_report, final_report), `python/larch/review/`, `python/larch/design/`, `python/larch/implement/`.
- `agents/*implementer.md`, `skills/implement/references/codex-manifest-schema.md`, `skills/gc-run-logs/SKILL.md`, `skills/implement/SKILL.md`, `skills/design/SKILL.md`.
- `docs/issue-anchored-plan.md`, `docs/run-logs-required-files.tsv`, a new rubric+examples doc, a new floor-glob manifest.

### Open questions
- Corpus depth: seed a concise set now, defer full curation to calibration. Floors: deterministic path-glob manifest. Both resolved from Round 1.
