## Decision 1: Drift policy (behavior preservation)
- **Question**: The invariant and guideline ship-gate twins have diverged (empty invariants file resolves to `clean` via a `present-empty` precheck and `REASON_INVARIANTS_EMPTY` classifier branch; invariants use a `violation` outcome vocabulary guidelines lack). Preserve these differences or reconcile them?
- **Resolution**: Preserve behavior exactly. Encode each difference as a descriptor field (empty-handling policy, outcome vocabulary, reason-token set). This is a pure behavior-preserving refactor: no guideline or invariant ship-gate behavior changes. Existing tests staying green is the acceptance criterion.
- **Source**: user

## Decision 2: Layer scope (single plan, all layers)
- **Question**: The twins span the core module (`architectural_guidelines.py`, 43 pairs), the ship layer (`ship_guidelines.py` + `ship.py`), 22 CLI verbs, and a shell-script pair. One plan for all layers, or core module first with the rest phased?
- **Resolution**: All layers in one plan, matching the issue's net -900 to -1,200 line reduction target. The core and ship layers are coupled through the shared outcome vocabulary, so the collapse lands once everywhere.
- **Source**: user

## Decision 3: Proven-dead twin removal
- **Question**: `_flush_invariant_outcome_before_pr` in `ship.py` is annotated unused and never wired (only the guideline flush runs). Remove it during the collapse or leave it untouched?
- **Resolution**: Remove it. It never ran, so removal is behavior-neutral; it also drops a misleading twin and reduces lines. The generic flush stays wired for guidelines only.
- **Source**: user

## Hard constraints carried into drafting
- Behavior-preserving: all divergences become descriptor-driven config, not reconciled behavior.
- Skill-facing surfaces stay byte-identical: the 22 `cli.py` `_REGISTRY` keys and their `_MACHINE_STDOUT_KEYS` entries; the `validate_*_ship_outcome_record` JSON-schema contract consumed by `audit_runs.py` / `run_log_batch.py`; the shell verb names.
- Public twin symbols bound by 12 external modules stay callable (keep them as thin partials/wrappers delegating to the generic implementation) unless a call site already selects by `kind`.
