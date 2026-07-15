## Goal
Implement issue #7387: [IMPLEMENTING] split-7010-1: cli.py registry unification.

## Implementation Plan
## Plan

### UPDATED: python/larch/cli.py

- Update `_REGISTRY`’s type annotation to `dict[tuple[str, str], tuple[str, str, bool]]`.
- Change `_REGISTRY` values to `(module, function, machine_stdout)`.
- Transfer every current machine-stdout classification to the boolean field without changing CLI names or behavior.
- Delete `_DESIGN_LIFECYCLE_STDOUT_KEYS` and the hand-maintained `_MACHINE_STDOUT_KEYS` literal; retain `_MACHINE_STDOUT_KEYS` only as an immutable compatibility view derived from true registry rows.
- Repoint 28 design routes to their defining `design_step0_env`, `design_step0`, `design_step1`, `design_router`, `design_terminal`, `design_session`, `design_step2b`, `design_step5b`, `design_step5c`, and `design_step6` modules.
- Repoint six review-pipeline routes to `review_gather`, `review_dispatch_panel`, `review_collect`, `review_threshold`, `review_core_body`, and `review_prune`.
- Repoint `run-log commit` and `run-log publish-breadcrumbs` to `run_log_commit`; repoint `run-log flush`, `run-log refresh`, and `run-log capture-transcript` to `run_log_flush`.
- Update lazy dispatch to unpack the boolean and set `LARCH_QUIET_DISABLE=1` before import and invocation only for machine-stdout rows.

### UPDATED: python/tests/test_cli.py

- Update registry assertions and registry-wide iteration for three-field values.
- Assert representative machine-stdout and human-facing rows retain their respective booleans.
- Assert `_MACHINE_STDOUT_KEYS` exactly equals the keys derived from true registry rows.
- Replace the deleted design-lifecycle stdout-set test with assertions that the repointed design commands retain machine stdout, use their defining modules, and no `_REGISTRY` row targets `larch.design.design_lifecycle`.
- Update mocked module paths for repointed design, review, and run-log commands.
- Keep registry-wide callable-target coverage and direct-dispatch quiet-mode coverage.

### UPDATED: python/tests/skills/_structure_design_specialized.py

- Remove extraction and validation of `_DESIGN_LIFECYCLE_STDOUT_KEYS`.
- Remove the structural requirement that routed design entrypoints use `design_lifecycle`.
- Adjust specialized assertion inventory metadata for those removals while retaining unrelated design structure and lifecycle checks.

### UPDATED: python/tests/design/test_design_cli_ports.py

- Update expected design routes to their defining modules, including the `design_step2b`, `design_step5b`, `design_step5c`, and `design_terminal` targets.
- Adapt registry assertions to compare module and function fields from three-tuples and retain machine-stdout assertions for applicable rows.

### UPDATED: python/tests/design/test_design_gate_render.py

- Adapt the `render-gate` registry assertion to the three-field row while preserving its machine-stdout expectation.

### UPDATED: python/tests/design/test_design_step_log.py

- Adapt the `plan step1-log` registry assertion to the three-field row while preserving its machine-stdout expectation.

### UPDATED: python/tests/implement/test_implement_dispatch.py

- Adapt every direct `_REGISTRY` two-tuple assertion to compare the module/function portion of the three-tuple, including the `step-5-resume` assertion.

## Edge cases

- Keep `False` for human-facing commands and `True` for all existing machine consumers, including design and plan commands formerly covered by the deleted spread set.
- Preserve lazy imports, exit-code propagation, and facade modules for consumers outside `_REGISTRY`.
- Do not retain a second hand-maintained machine-stdout authority.

## Failure modes

- A missing `True` re-enables quiet suppression for `KEY=value` consumers.
- A stale facade route breaks lazy imports, callable lookup, or monkeypatch seams.
- A remaining two-field unpack or equality assertion breaks the Python suite.
- A stale two-field `_REGISTRY` annotation fails strict type checking.
- A registry-wide facade-exclusion test prevents design routes from silently returning to `design_lifecycle`.

## Testing strategy

- Run `python3 -m pytest python/tests/test_cli.py`.
- Run `python3 -m pytest python/tests/design/test_design_cli_ports.py`.
- Run `python3 -m pytest python/tests/design/test_design_gate_render.py python/tests/design/test_design_step_log.py python/tests/implement/test_implement_dispatch.py`.
- Run `make test-design-structure`.
- Run `python3 python/cli.py design step0-session -- --help` and confirm exit code 0.
- Exercise representative machine-stdout commands and confirm `LARCH_QUIET_DISABLE=1`.
- Run `make py-lint`.
- Run `make py-test`.

## Acceptance

- Run `python3 -m pytest python/tests/test_cli.py`.
- Run `python3 -m pytest python/tests/design/test_design_cli_ports.py`.
- Run `python3 -m pytest python/tests/design/test_design_gate_render.py python/tests/design/test_design_step_log.py python/tests/implement/test_implement_dispatch.py`.
- Run `make test-design-structure`.
- Run `python3 python/cli.py design step0-session -- --help` and confirm exit code 0.
- Exercise representative machine-stdout commands and confirm `LARCH_QUIET_DISABLE=1`.
- Run `make py-lint`.
- Run `make py-test`.

diff_added: 700
diff_deleted: 980
mechanical_churn: true
oversize_override: operator
diff_lines: 1680

## Test plan
(no test plan section in plan-file)
