# Discussion Round 1 — Issue #3432

## Decision 1: Removal reach stops at /implement + report-tokens implement side
- **Question**: The HARD/SIMPLE plumbing is shared with /design, whose tier system stays alive. How far should removal reach?
- **Resolution**: Implement-side only. Remove /implement's workflow plumbing and report-tokens' implement-side workflow handling. Leave every /design-side surface untouched, including shared helpers' flags that /design still passes (`render-run-summary.sh --workflow-path`, `read-workflow-path.sh`, timing workflow rows, `write-run-params.sh --workflow-path`, design run-params `workflow_path`, report-tokens `--skill=design` SIMPLE/HARD split).
- **Source**: user

## Decision 2: Implement run summaries drop the Path bullet
- **Question**: /implement's final run summary prints `- **Path**: HARD` via the shared renderer. What should implement summaries show after removal?
- **Resolution**: Drop the bullet. /implement stops passing `--workflow-path`; the renderer omits the Path bullet for implement runs. /design keeps its Path bullet. Format tests and docs/run-logs.md prose update accordingly.
- **Source**: user

## Decision 3: report-tokens removes the workflow dimension fully for implement
- **Question**: For `--skill=implement`, how should the workflow dimension be removed from reports?
- **Resolution**: Remove the dimension fully. Scanner stops reading workflow artifacts for implement runs (no more "lacks SIMPLE/HARD classification" warnings); per-run table drops the workflow column; "Aggregate cost by workflow" and per-phase tables lose the workflow grouping for implement. `--skill=design` keeps its SIMPLE/HARD split.
- **Source**: user

## Decision 4: Launcher timeout stays at 7200s
- **Question**: `step2-implement.sh` forks the external-implementer timeout on `--workflow` (HARD=7200s, SIMPLE=3600s). What timeout survives flag removal?
- **Resolution**: 7200s. /implement hardcodes HARD at every call site today (`run-step2-dispatch.sh:82`, `implement-bootstrap.sh` persist sites), so 7200s is the current effective behavior; preserve it as the single fixed timeout.
- **Source**: codebase

## Decision 5: Historical committed run logs must keep scanning cleanly
- **Question**: report-tokens scans committed `larch-logs/implement/<RUN_ID>/` dirs from historical runs that contain workflow fields. Must they still parse?
- **Resolution**: Yes — hard constraint. Old artifacts keep their fields; new scanner code simply never reads workflow keys for implement runs, so old and new run dirs scan identically with no warnings. Committed logs are immutable; no migration.
- **Source**: codebase

## Decision 6: /design consumers of shared helpers must not break
- **Question**: Which shared surfaces does /design still depend on?
- **Resolution**: `render-run-summary.sh --workflow-path` (passed by `skills/design/scripts/render-final-summary.sh:381`), `read-workflow-path.sh` (timing-report fallback), `timing-ledger.sh workflow-path` subcommand grammar, timing-report workflow rows, `write-run-params.sh --workflow-path`, and report_tokens `workflow_groups()` design labels ("SIMPLE", "HARD"). These keep working unchanged; only /implement call sites and implement-skill code paths are removed.
- **Source**: codebase
