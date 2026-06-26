### OOS_1: [SCOPE-REDUCTION] Optional env_name and constant exemption scoping adds complexity beyond issue needs
- **Description**: [SCOPE-REDUCTION] Optional env_name and constant exemption scoping adds complexity beyond issue needs. Scenario: The issue asks for allowlist/suppression with documented reason. Subprocess uses file+reason only. Optional env_name/constant keys plus conjunctive matching rules add schema, load validation, matching logic, and four extra pytest cases without a stated requirement for finer-grained exemptions.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: plan.txt:172-179
- **Phase**: design



### OOS_2: [SCOPE-REDUCTION] Dual duplicate ENV_* value policies add asymmetric complexity
- **Description**: [SCOPE-REDUCTION] Dual duplicate ENV_* value policies add asymmetric complexity. Scenario: The plan requires fail-closed exit 2 on synthetic fixture duplicates but first-sorted-wins when bootstrapping live config.py, plus dedicated pytest for both branches. Live config.py appears to have unique literal mappings today.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: plan.txt:226-301
- **Phase**: design



### OOS_3: [SCOPE-REDUCTION] Store-context os.environ subscript detection expands v1 beyond read-path debt
- **Description**: [SCOPE-REDUCTION] Store-context os.environ subscript detection expands v1 beyond read-path debt. Scenario: The binding issue targets os.environ.get("X") and os.environ["X"] read access. Adding subscript_store detection, a distinct access dimension in the identity tuple, and cli.py assignment fixtures increases AST handling and baseline cardinality for write-side literals not cited in verified examples (plan_review.py, phantom.py, design_legacy.py are get/subscript_load paths).
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: plan.txt:151-152
- **Phase**: design



### OOS_4: [OUT_OF_SCOPE] `os.environ["X"] = ...` Store-context detection adds a broader write-access ratchet that the issue did not ask for.
- **Description**: [OUT_OF_SCOPE] `os.environ["X"] = ...` Store-context detection adds a broader write-access ratchet that the issue did not ask for.. Scenario: The repo already uses many env writes in `python/bootstrap.py:421,1017,1609`, `python/design_lifecycle.py:537,1344-1427,1970,3410,3609,3870-3877,4275`, `python/logging_util.py:97-99`, and `python/agents.py:623,694,703,865,880,2506-2513,4202,4212,4432,4450,4721,4734,5091-5094`; flagging them would balloon the baseline with write-only mutation sites.
- **Reviewer**: Codex-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/lint_env_via_config_constant.py:147-151
- **Phase**: design



### OOS_5: Env Scope does not exclude pytest helper modules by filename the way subprocess does.
- **Description**: Env Scope does not exclude pytest helper modules by filename the way subprocess does.. Scenario: conftest.py and test_support.py are production-adjacent paths that subprocess already skips; if bare os.environ.get literals are added there later, the env linter would flag them and seed avoidable baseline debt.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/lint_env_via_config_constant.py:138-141
- **Phase**: design



