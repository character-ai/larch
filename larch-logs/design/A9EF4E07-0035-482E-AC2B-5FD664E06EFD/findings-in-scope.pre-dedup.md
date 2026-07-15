### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/tests/skills/skill_structure_pins.py:340-357; python/tests/skills/_structure_implement_specialized.py:258-261,809
- **Concern**: Structure pins still substring-match two-field registry rows; FINDING_3 coverage is incomplete. Scenario: After every `_REGISTRY` value gains a third `machine_stdout` field, needles like `("design", "render-gate"): ("larch.design.design_gate_render", "render_gate_main")` and ship/implement registry pins no longer appear in `python/larch/cli.py`, so `make test-design-structure` and full `make py-test` fail even when repointing and dispatch are correct
- **Proposed resolution**: Add `### UPDATED: python/tests/skills/skill_structure_pins.py` and `### UPDATED: python/tests/skills/_structure_implement_specialized.py` to relax or extend needles for three-tuples (for example allow an optional trailing `, True`/`False`) while keeping module/function checks



### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/cli.py:16
- **Concern**: Plan changes registry row shape but not the annotated `_REGISTRY` type. Scenario: Strict pyright (`make py-lint` → `py-typecheck`) will reject `(module, func, bool)` values against `dict[tuple[str, str], tuple[str, str]]` and may reject the new three-value unpack in dispatch
- **Proposed resolution**: Explicitly update the `_REGISTRY` annotation to `dict[tuple[str, str], tuple[str, str, bool]]` in the cli.py section alongside the value migration ### 1. [risk-integration] Structure skill pins still assume two-field registry rows `python/tests/skills/skill_structure_pins.py` and `python/tests/skills/_structure_implement_specialized.py` pin exact `_REGISTRY` substrings that end after the module/function pair. After the planned three-tuple migration, lines like `("design", "render-gate"): ("larch.design.design_gate_render", "render_gate_main", True)` will not match. Round 1 **FINDING_3** is only partly addressed: the listed pytest files are covered, but not these structure harnesses. The plan’s testing strategy includes `make test-design-structure` and `make py-test`, so this is an in-scope gap. **Suggested revision:** Add both skill-structure files to the firm plan and update pins to accept the third boolean field without dropping module/function checks. ### 2. [correctness] Update the `_REGISTRY` type annotation The plan changes row values to `(module, function, machine_stdout)` and dispatch to unpack three fields, but it does not mention updating the annotation at `python/larch/cli.py:16`. Under strict pyright, that mismatch fails `make py-lint`. **Suggested revision:** Include the annotation change explicitly in the `python/larch/cli.py` section.



### FINDING_3:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Focus area**: code-quality
- **Location**: plan.txt:Testing strategy
- **Concern**: [SCOPE-REDUCTION] Remove `make py-test` from the validation plan. Scenario: The focused changed-file suites already cover this registry change; the repository instructs contributors to test only changed files and reserves the full sweep for CI.
- **Proposed resolution**: Delete the `make py-test` step.



