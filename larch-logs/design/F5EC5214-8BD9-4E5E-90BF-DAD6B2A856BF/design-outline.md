## Proposed Design Outline

### Goals
- Collapse the guideline/invariant twin function families into single generic functions driven by a frozen `AssessmentKind` descriptor.
- Hit the issue's net -900 to -1,200 line reduction; drop the edit fan-out from two copies per layer to one.
- Preserve current behavior exactly. Every twin divergence becomes descriptor config, not a behavior change.

### Non-goals
- No ship-gate behavior change. The empty-invariants and `violation`-vocab drift is preserved via the descriptor, not reconciled.
- No change to skill-facing surfaces: the 22 `cli.py` verb keys, their `_MACHINE_STDOUT_KEYS` entries, the `validate_*_ship_outcome_record` JSON schema, and the shell verb names.
- No new invariant functionality for guideline-only asymmetries (staged-write, pin/invalidate helpers stay as they are).

### Approach sketch
- Add a frozen `AssessmentKind` descriptor with two instances (GUIDELINES, INVARIANTS) carrying artifact paths, KV prefix, status-field name, reason-token set, heading regex, outcome vocabulary, and empty-handling policy.
- Rewrite the ~37 mechanical-rename twins in `architectural_guidelines.py` as one generic function each, keeping every public twin name as a thin partial that delegates to the generic.
- Fold the ~6 truly divergent twins (present-empty precheck, the two validators, `parse_*_entries`, the ship classifiers) into descriptor-branched single functions.
- Collapse the ship layer (`ship_guidelines.py` GateResult/ShipOutcome + classify/read/load; `ship.py` gate/flush/outcome-match helpers) the same way; delete the dead invariant flush.
- Keep the 22 CLI verbs as 2-line partials; reduce the shell-script pair to thin wrappers over one parameterized verb path.

### Surfaces in scope
- `python/larch/core/architectural_guidelines.py`, `config.py`
- `python/larch/implement/ship_guidelines.py`, `ship.py`
- `python/larch/cli.py` (registry keys unchanged; partial targets)
- `skills/implement/scripts/step-architectural-{guidelines,invariants}-write-compose.sh`
- `python/tests/core/test_architectural_guidelines.py`, `python/tests/implement/test_ship.py`

### Open questions
- Descriptor home: extend `config.py` vs. a small new `assessment_kind.py` module. Resolve in drafting.
- Shell pair: two thin wrappers vs. one shared parameterized script. Resolve in drafting.
