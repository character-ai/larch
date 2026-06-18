### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/ci_monitor.py:760-789
- **Concern**: Replay argv tuples are defined in per_job_command() and separately mirrored as module-level constants in python/test_ci_monitor.py. Scenario: Any quoting or PYLINT_JOBS default drift between production and test constants breaks RecordingRunner keyed stubs while CI replay still looks correct; make py-test fails across run_ci_fix / verify_job_locally / evaluate_failure paths
- **Proposed resolution**: Define PYTHON_LINT_REPLAY_ARGV and PYTHON_PYRIGHT_REPLAY_ARGV once in python/ci_monitor.py (module-level tuples used by per_job_command) and import those same objects in python/test_ci_monitor.py for parametrization and RecordingRunner keys

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: .github/workflows/ci.yaml:564-584
- **Concern**: python-pyright job sketch omits the PIP_RETRIES / PIP_DEFAULT_TIMEOUT install env block that python-lint already uses. Scenario: The new job may flake on transient pip failures while sibling lint jobs retry; intermittent CI-only failures not reproduced by local make py-lint
- **Proposed resolution**: Copy the same Install Python lint dependencies env: block (PIP_RETRIES and PIP_DEFAULT_TIMEOUT) onto python-pyright before pip install -r python/requirements-dev.txt

### FINDING_3:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/ci_monitor.py:760-784; Makefile:4
- **Concern**: The planned python-lint replay defaults to PYLINT_JOBS=0 and bypasses the existing local sysconf fallback. Scenario: Restricted local sandboxes that Makefile handles by falling back to one pylint worker can make /implement --merge local replay fail before validating the split CI job
- **Proposed resolution**: Preserve the same local PYLINT_JOBS fallback in the ci_monitor replay command while keeping the CI workflow env override at PYLINT_JOBS=0
