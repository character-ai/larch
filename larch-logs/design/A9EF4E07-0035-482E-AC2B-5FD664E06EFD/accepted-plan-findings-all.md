### FINDING_1: Update design CLI port expectations
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-Registry Contract Auditor, Codex-dyn-Registry Contract Auditor
- **Severity**: major
- **Concern**: `python/tests/design/test_design_cli_ports.py` still expects repointed verbs to target `larch.design.design_lifecycle`; the three-tuple and direct-module migration must update these expectations and focused validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add ### UPDATED: python/tests/design/test_design_cli_ports.py with defining-module targets for every repointed verb and include python3 -m pytest python/tests/design/test_design_cli_ports.py in Testing strategy
  - From Cursor-Innovation: Update `EXPECTED` targets to defining modules (e.g. `design_step2b`, `design_step5c`, `design_step5b`, `design_terminal`) and add this file to firm plan headings or testing strategy (`pytest python/tests/design/test_design_cli_ports.py`).
  - From Cursor-Pragmatic: Add ### UPDATED: python/tests/design/test_design_cli_ports.py; retarget EXPECTED modules to defining design_step2b design_step5b design_step5c design_terminal modules; extend testing strategy to run that file
  - From Cursor-Requirements: Add make py-test to acceptance and Testing strategy, and add ### MAY_UPDATE entries for the failing registry-assertion tests (at minimum python/tests/design/test_design_cli_ports.py) to compare entry[:2] and update repointed module paths; or document that piece 1 is intentionally non-mergeable until a follow-up partition updates those tests.
  - From Codex-Requirements: Update these tests for `(module, function, machine_stdout)` rows and the direct design-module routes, then include them in focused validation.
  - From Cursor-dyn-Registry Contract Auditor: Add ### UPDATED: python/tests/design/test_design_cli_ports.py: refresh EXPECTED modules to defining design_* modules and expected machine_stdout flags
  - From Codex-dyn-Registry Contract Auditor: Add these test files to the plan and update their registry assertions to compare the module and entrypoint fields while retaining their machine-stdout checks


### FINDING_2: Add a registry-wide facade exclusion assertion
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: minor
- **Concern**: Spot checks do not enforce the acceptance rule that no `_REGISTRY` entry targets `larch.design.design_lifecycle`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Replace test_design_lifecycle_registry_entries_are_machine_stdout with an explicit scan over cli._REGISTRY values asserting module_name != larch.design.design_lifecycle plus representative per-verb defining-module targets for the 28 repointed commands
  - From Cursor-Pragmatic: In test_cli replacement add a registry-wide scan asserting no _REGISTRY module_name equals larch.design.design_lifecycle
  - From Cursor-Requirements: In test_cli.py add one assertion that scans every _REGISTRY value and rejects module_name == larch.design.design_lifecycle (and optionally fails if any row still references larch.review.review_pipeline or larch.report.run_logs for the 11 repointed review/run-log verbs).


### FINDING_3: Update all three-tuple registry consumers
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation, Cursor-Requirements, Codex-Requirements, Cursor-dyn-Registry Contract Auditor, Codex-dyn-Registry Contract Auditor
- **Severity**: major
- **Concern**: Existing tests outside `python/tests/test_cli.py` compare or unpack two-field registry values; converting `_REGISTRY` rows to three-tuples will break the full Python suite.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add `### UPDATED: python/tests/implement/test_implement_dispatch.py` (and the same tuple-slice/`[:2]` pattern in `test_design_step_log.py` and `test_design_gate_render.py`) or extend the `test_cli.py` section to cover every `_REGISTRY[...] ==` consumer.
  - From Codex-Innovation: Add the affected registry-contract tests to the plan and compare module/function fields while asserting the machine-stdout boolean where relevant.
  - From Cursor-Requirements: Add make py-test to acceptance and Testing strategy, and add ### MAY_UPDATE entries for the failing registry-assertion tests (at minimum python/tests/design/test_design_cli_ports.py) to compare entry[:2] and update repointed module paths; or document that piece 1 is intentionally non-mergeable until a follow-up partition updates those tests.
  - From Codex-Requirements: Update these tests for `(module, function, machine_stdout)` rows and the direct design-module routes, then include them in focused validation.
  - From Cursor-dyn-Registry Contract Auditor: Extend the plan test_cli.py tuple-migration note to cover every test file that compares _REGISTRY[...] to a 2-tuple (slice [:2] or include the bool)
  - From Codex-dyn-Registry Contract Auditor: Add these test files to the plan and update their registry assertions to compare the module and entrypoint fields while retaining their machine-stdout checks


### FINDING_2: Update `_REGISTRY` type annotation
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Concern**: The plan changes `_REGISTRY` values to three-tuples but does not explicitly update its type annotation, potentially causing strict pyright failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Explicitly update the `_REGISTRY` annotation to `dict[tuple[str, str], tuple[str, str, bool]]` in the cli.py section alongside the value migration
  - From Cursor-Innovation: Include the annotation change explicitly in the `python/larch/cli.py` section.


