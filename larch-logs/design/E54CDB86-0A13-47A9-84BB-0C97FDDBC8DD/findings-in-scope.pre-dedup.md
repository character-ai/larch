### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/report/timing.py:35-42
- **Concern**: Missing forced-plan-fidelity timing kinds. Scenario: The plan removes the auto-only plan-fidelity task kinds but never adds the surviving `plan-fidelity-forced` variants, so new forced-row launches will still record unknown timing kinds and emit warnings on every run.
- **Proposed resolution**: Add the forced-row timing kinds that the launcher will emit, or retarget the forced row to an already-allowlisted kind.



### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/review/review_dispatch_panel.py:243-248
- **Concern**: python/larch/review/plan_review_panel.py:261-266. Scenario: [SCOPE-REDUCTION] Plan duplicates resolved_model=auto at every Cursor manifest builder instead of teaching _with_attribution to prefer row cursor_model
- **Proposed resolution**: Each static, dynamic, and forced row must set cursor_model and resolved_model in parallel; _with_attribution still defaults Cursor rows to composer-2.5 via resolve_model_args when resolved_model is absent, so one missed call site revives the plan's launch-on-auto but attribute-as-composer-2.5 failure mode across four edit surfaces In both _with_attribution helpers, when tool is cursor and row already has a non-empty cursor_model, set resolved_model from cursor_model before the resolve_model_args fallback; then manifest builders only need cursor_model=config.CURSOR_AUTO_MODEL (or slot.cursor_model) and forced-row cursor_model=auto, dropping repeated resolved_model assignments and paired test assertions except where launch attribution is explicitly overridden



### FINDING_3:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/report/timing.py:37-42
- **Concern**: The allowlist drops the deleted auto literals, but it also omits the surviving forced-plan-fidelity timing kinds.. Scenario: The retained `plan-fidelity-forced` row will launch as `cursor-phase1-plan-fidelity-forced` or `codex-phase1-plan-fidelity-forced`, so `TimingLedger.record_vendor_task` will warn on every forced run and `timing task-kinds` will not cover the live path.
- **Proposed resolution**: Add the forced phase1 kinds to `TIMING_TASK_KINDS_ALLOWED` and keep the auto entries removed.



