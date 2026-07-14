### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/tests/support/design_wire.py:NEW
- **Concern**: [SCOPE-REDUCTION] run_params_json duplicates Piece 2 seed_run_params / _RUN_PARAMS_SCHEMA_V3 (G-Fix-1 G-Cfg-3). Scenario: session.py already owns schema-v3 defaults and seed_run_params matching session_env.write_run_params; a third builder in design_wire.py will drift and produce non-canonical run-params.json during migration
- **Proposed resolution**: Drop run_params_json from design_wire.py; migrate valid run-params writes to session.seed_run_params and any dict seeds to a single exported constant in session.py

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/tests/design/test_design_lifecycle.py:UPDATED
- **Concern**: [SCOPE-REDUCTION] plan_body migration mandated for files with no firm plan headings. Scenario: test_design_lifecycle.py test_design_publish.py test_design_postplan.py test_design_log_publish_flow.py and test_rendering.py contain zero ### NEW:/UPDATED: literals; forcing plan_body there adds API surface without meeting the one-file heading-edit goal
- **Proposed resolution**: Limit plan_body migration to test_plan_quality.py (and any future heading-heavy fixtures); in the other listed files migrate only diff_lines_trailer write_result_env and seed_run_params while keeping plan prose on seed_plan or inline literals

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/tests/support/design_wire.py
- **Concern**: [SCOPE-REDUCTION] `run_params_json` duplicates Piece 2 `tests.support.session.seed_run_params`. Scenario: Piece 2 already writes schema-v3 `run-params.json` with the same override semantics (`indent=2`, trailing newline). A second serializer in `design_wire.py` reintroduces the drift this piece is trying to remove and can diverge on whitespace or default keys.
- **Proposed resolution**: Drop `run_params_json` from `design_wire.py`. Migrate call sites to `seed_run_params(tmpdir, overrides=...)` (or a one-line re-export alias only if ergonomics require it). Cover defaults/overrides in `test_foundation.py` via `seed_run_params`, not a parallel API.

### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/tests/support/design_wire.py
- **Concern**: [SCOPE-REDUCTION] run_params_json must share schema and serialization with tests.support.session.seed_run_params. Scenario: Piece 2 already owns schema-v3 defaults and indent=2 dumps in session.py; a second copy in design_wire.py can drift from seed_run_params and from write_run_params_main defaults, breaking the one-file wire-edit goal when run-params fields change
- **Proposed resolution**: Implement run_params_json by reusing session._RUN_PARAMS_SCHEMA_V3 (or a single shared helper both modules call); keep seed_run_params as the file writer and run_params_json as the string return for inline writes

### FINDING_11:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/tests/design/test_design_lifecycle.py
- **Concern**: [SCOPE-REDUCTION] Lifecycle migration includes result-env writers beyond the acceptance-critical step3 paths. Scenario: The issue acceptance criteria center on plan headings, diff_lines trailers, and make_design_tmpdir; broad result-env replacement across route/init env files adds multi-allowlist coupling without a stated payoff
- **Proposed resolution**: Narrow test_design_lifecycle.py migration to plan bodies and run-params.json only; keep route/init/malformed result-env literals inline (as test_design_publish.py already does for invalid cases) and limit write_result_env adoption to ordinary step3/postplan env fixtures

### FINDING_12:
- **Reviewer(s)**: Cursor-dyn-Wire Fixture Boundary
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/tests/support/session.py:201-213 vs python/tests/support/design_wire.py (planned)
- **Concern**: [SCOPE-REDUCTION] Planned run_params_json duplicates existing seed_run_params. Scenario: Piece 2 already writes schema-v3 run-params.json with indent=2 and a trailing newline via seed_run_params; a second run_params_json in design_wire.py creates two defaults that can drift on key order whitespace or missing keys
- **Proposed resolution**: Make run_params_json a thin delegate/re-export of session.seed_run_params (or call it internally); do not duplicate _RUN_PARAMS_SCHEMA_V3
