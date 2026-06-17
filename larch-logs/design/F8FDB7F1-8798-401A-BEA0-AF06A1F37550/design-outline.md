## Proposed Design Outline

### Goals
- Collapse /implement Step 18's no-stall path from three Bash calls (18a gate, 18b final-report, finalize) plus the separate `.step17-emitted` write into one `step-18.sh` invocation.
- Keep behavior byte-identical: stall recovery, teardown tail, ordering invariants, and the NEVER #17 emission gates.

### Non-goals
- No change to stall classification/recovery semantics or final-report content.
- No change to the Step 16-17 fence or the Step 17 marker-emission contract.
- No new runtime behavior; this is an orchestration consolidation only.

### Approach sketch
- New `skills/implement/scripts/step-18.sh` runs the 18a four-layer stall resolution first. On any layer true, emit `STALL_RECOVERY_REQUIRED=true` + classification inputs and exit; the orchestrator loads stall-recovery.md, runs recovery, and re-invokes the wrapper.
- When all layers clear, run 18b + finalize teardown internally; accept `--step17-emitted true` so the sentinel write rides this call.
- When `EMIT_BODY=true` (WFR_RC=0 and non-empty summary-final.md), print the refreshed body between stable markers before teardown; the orchestrator re-emits it from captured stdout.
- Fold the three legacy scripts' logic into step-18.sh and delete them + their .md siblings; call existing python verbs (e.g. `final-report step18b`) as-is, touching python only if clearly cleaner.

### Surfaces in scope
- Add `skills/implement/scripts/step-18.sh` (+ `step-18.md`); delete `step-18a-gate.{sh,md}`, `step-18b-final-report.{sh,md}`, `step-18-finalize.{sh,md}`.
- `skills/implement/SKILL.md` (Step 18 fences + script-list refs at lines ~99/857/892/899).
- Tests: new `test-step-18.sh`; update `test-implement-structure.sh`, `test-implement-timing-rehydration.sh`, `test-write-final-report.sh`.
- `Makefile`, `docs/linting.md`, `python/migrated-scripts.tsv`.

### Open questions
- None.
