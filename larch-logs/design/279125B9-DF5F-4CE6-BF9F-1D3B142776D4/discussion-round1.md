## Decision 1: Sentinel writes required in step1d7
- **Question**: Does the entry fence write sentinels on the skip path that must be preserved for pause/resume?
- **Resolution**: Yes. `_step1d5_entry_main` writes `.completed/step-1c`, `.completed/step-1d`, and `.completed/step-1d.5` (when skip) before `check_pause_and_exit`. `_determine_step` walks the registry in order, so without those sentinels a pause at `step1d7` would resume at step `1c`. Must fold those writes into `step1d7_main` before its existing `check_pause_and_exit` call.
- **Source**: codebase (design_lifecycle.py lines 2978–2999, design_pause.py lines 68–99)

## Decision 2: Brainstorm-on path unaffected
- **Question**: Should the entry fence be elided on the brainstorm-on path too?
- **Resolution**: No. Elision applies only when `brainstorm_requested=false`. On the brainstorm-on path the entry fence writes step-1c/step-1d and may return `STEP1D5_ACTION=run` or `skip/already-complete`; that logic stays unchanged.
- **Source**: issue body + codebase

## Decision 3: Timing mark not needed on skip path
- **Question**: Should the timing mark (`design Step 1d.5 — brainstorm`) be preserved for the skip path?
- **Resolution**: The mark is only meaningful when brainstorm actually runs. Drop it on the skip path; no downstream consumer reads brainstorm timing when brainstorm was disabled.
- **Source**: codebase

1 scope decision resolved (sentinel-folding); 2 derived from codebase evidence.
