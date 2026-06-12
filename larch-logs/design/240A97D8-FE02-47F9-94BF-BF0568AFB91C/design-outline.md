## Proposed Design Outline

### Goals
- Remove all HARD-tier-specific code, scripts, references, and tests from the `/design` skill.
- Rename plan-size machine tokens (`HARD_TRIGGER_FIRED` → `SIZE_TRIGGER_FIRED`, related tokens) without changing plan-size braking behavior.
- Eliminate all `SIMPLE` and `HARD` string literals from the codebase so `git grep -nE 'SIMPLE|HARD' -- ':!larch-logs'` produces no output.

### Non-goals
- Changing the behavior of the remaining design flow (SIMPLE characteristics stay intact).
- Altering the plan-size threshold values or the Split/Cancel/Override braking behavior.
- Touching `/implement`, `/review`, or other skills beyond what is required to remove SIMPLE/HARD references.

### Approach sketch
- Delete HARD-exclusive scripts and references: `design-step2a2-record-launches.sh`, `design-step2a3-collect.sh`, `design-step2a5.sh`, `design-step2a-zero-sketch.sh`, `snapshot-plan-round.sh`, and their `.md` sibling / test files.
- Delete HARD-exclusive reference files: `sketch-prompts.md`, `sketch-launch.md`, `dialectic-execution.md`, `dialectic-debate.md`.
- Simplify surviving scripts that branch on `design_classification` / `is_hard()` / `sketch_budget`: remove HARD branches, remove `read-classification` calls, remove `step3_loop_is_hard()` and `step3_loop_run_hard_snapshots()`.
- Rename `HARD_TRIGGER_FIRED` → `SIZE_TRIGGER_FIRED` and cascade related tokens in `check-plan-size.sh`, `design-postplan-emit.sh`, `design-step2b-postplan.sh`, `review-design-step3-loop.sh`, `SKILL.md`, docs, and tests.
- Remove tier fields from `run-params.json` schema: `design_classification`, `design_classification_reason`, `design_classification_source`, `sketch_budget`, `workflow_path` in `session_env.py`, `design-init-runparams.sh`.
- Remove `--workflow-path` from `render-run-summary.sh` and callers; remove per-tier grouping from `/report-tokens` (`report_tokens_render.py`, fixture updates).
- Rename sentinel `NO_SKETCHES_CLASSIFIED_SIMPLE` → `NO_SKETCHES` in `design-step2a.sh` and consuming code.
- Update all docs (`SKILL.md`, reference .md files, README, SECURITY.md, docs/*.md) to remove SIMPLE/HARD language.
- Run `make lint` to verify no regressions.

### Surfaces in scope
- `skills/design/SKILL.md` and all `skills/design/references/*.md`
- `skills/design/scripts/` (deletions and edits as above)
- `scripts/render-run-summary.sh`, `scripts/render-run-summary.md`, and test harnesses
- `python/session_env.py`, `python/timing.py`, `python/gh.py`, `python/report_tokens_render.py`
- `python/fixtures/report_tokens_design_golden.md` and affected Python tests
- `README.md`, `SECURITY.md`, `docs/*.md`
- `scripts/test-design-structure.sh` and other test harnesses that assert on SIMPLE/HARD
- `agent-lint.toml` (any SIMPLE/HARD lint pins)

### Open questions
- None.
