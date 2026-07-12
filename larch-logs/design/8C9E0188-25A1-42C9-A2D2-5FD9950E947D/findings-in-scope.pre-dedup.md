### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/tests/state/test_bootstrap.py
- **Concern**: Bootstrap tmpdir layout differs from dispatch `impl/` convention. Scenario: Many bootstrap cases set `implement_tmpdir=str(tmp_path)` and write `plan.txt`/`session-env.sh` at `tmp_path` root, while `make_implement_tmpdir` always seeds `tmp_path/impl`; blind replacement leaves artifacts under `impl/` while bootstrap still reads the parent directory
- **Proposed resolution**: In `test_bootstrap.py` migration notes, require directory alignment: use `seed_plan`/`seed_feature_description`/`write_session_env` on the same path passed as `implement_tmpdir`, or switch `implement_tmpdir` to the path returned by `make_implement_tmpdir`; reserve `make_implement_tmpdir` for dispatch-style bindings only



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/tests/support/session.py
- **Concern**: `write_session_env` allowed-key policy is undefined for non-writer keys. Scenario: Migrated final-report and closeout fixtures need `MODE`, `ISSUE_NUMBER`, and other reader keys that are not in `WRITE_ENV_KEYS`; if the helper treats "invalid keys" as writer-only allowlist, `_write_minimal_state` refactors and ordinary overrides will fail validation or force unintended raw rewrites
- **Proposed resolution**: Document that implement `write_session_env` accepts any `_KEY_RE`-valid key for overrides (value hygiene only), while `write_design_source_env` stays restricted to `WRITE_DESIGN_ENV_KEYS`; for minimal fixtures, require omitting every implement baseline key before writing sparse overrides such as `REPO`+`MODE` only



### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/tests/support/session.py
- **Concern**: Default `seed_plan` / `seed_feature_description` bytes are unspecified. Scenario: Dispatch `_session` seeds `## Plan\n` and `feature\n`; unspecified defaults during mechanical migration can drift from the 148-call dispatch contract before `test_foundation` catches it
- **Proposed resolution**: Pin defaults in `session.py` to `## Plan\n` and `feature\n`, add optional `content=` to both seed helpers, and assert the literals in `test_foundation.py`



### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/tests/support/session.py
- **Concern**: Design export quoting for spaced paths is unspecified. Scenario: Plan edge case requires paths with spaces to remain valid; production `write_design_env_main` emits `export KEY=shlex.quote(value)`, but the helper spec only says "production-style" without quoting rules
- **Proposed resolution**: Make `write_design_source_env` use the same `export` + `shlex.quote` emission as `session_env._export_line`, and cover a spaced `REPO_ROOT` in `test_foundation.py` ### 1. [architecture] `python/tests/state/test_bootstrap.py`: Bootstrap tmpdir layout differs from dispatch `impl/` convention Many bootstrap tests bind `implement_tmpdir=str(tmp_path)` and place `plan.txt` and `session-env.sh` at the `tmp_path` root. `make_implement_tmpdir` always creates and seeds `tmp_path/impl`. Replacing inline setup with `make_implement_tmpdir` without retargeting `implement_tmpdir` leaves artifacts in `impl/` while bootstrap reads the parent. **Suggested revision:** In the `test_bootstrap.py` migration section, require directory alignment: call `seed_plan`, `seed_feature_description`, and `write_session_env` on the same directory used as `implement_tmpdir`, or set `implement_tmpdir` to the path returned by `make_implement_tmpdir`. Reserve `make_implement_tmpdir` for dispatch-style tests. ### 2. [correctness] `python/tests/support/session.py`: `write_session_env` allowed-key policy is undefined Migrated final-report fixtures use `MODE` and other reader keys outside `WRITE_ENV_KEYS`. If "reject invalid keys" is read as writer allowlist enforcement, `_write_minimal_state` refactors and ordinary overrides break. **Suggested revision:** State that implement `write_session_env` accepts any `_KEY_RE`-valid override key (with newline or NUL value rejection only). Keep design helper restricted to `WRITE_DESIGN_ENV_KEYS`. For minimal fixtures, omit every implement baseline key before writing sparse `REPO`+`MODE` overrides, or retain raw writes. ### 3. [correctness] `python/tests/support/session.py`: Default seed bytes are unspecified Dispatch `_session` uses `## Plan\n` and `feature\n`. Unpinned defaults risk silent drift across the large dispatch migration before foundation tests land. **Suggested revision:** Pin those literals in `session.py`, add optional `content=` to `seed_plan` and `seed_feature_description`, and assert them in `test_foundation.py`. ### 4. [correctness] `python/tests/support/session.py`: Design export quoting for spaced paths is unspecified The plan edge case requires spaced paths to work. Production design writer uses `shlex.quote` in export lines; the helper spec does not. **Suggested revision:** Emit `export KEY=shlex.quote(value)` like `session_env._export_line`, and add a spaced-path case to `test_foundation.py`.



### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/tests/support/session.py
- **Concern**: write_session_env allowlist is undefined while the implement baseline includes CURSOR_PRESENT. Scenario: The plan requires rejecting invalid keys and seeds CURSOR_PRESENT=false to match _session, but CURSOR_PRESENT is not in session_env.WRITE_ENV_KEYS. An allowlist of WRITE_ENV_KEYS alone rejects the baseline or forces dropping CURSOR_PRESENT and changing dispatch/bootstrap coverage.
- **Proposed resolution**: Define an explicit implement allowlist (at minimum WRITE_ENV_KEYS plus fixture-only keys such as CURSOR_PRESENT used by migrated tests) and document which keys are production-writer vs fixture-only.



### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/tests/report/test_final_report.py
- **Concern**: [SCOPE-REDUCTION] Keep _write_minimal_state as a raw sparse fixture instead of migrating it through write_session_env. Scenario: The plan both says to refactor _write_minimal_state via the shared writer and to retain deliberately incomplete session files. The helper baseline adds REPO_ROOT, plugin-root, and tool keys that minimal final-report tests currently omit; that can change report inputs beyond REPO=o/r.
- **Proposed resolution**: Exclude _write_minimal_state from shared-writer migration; keep its two-line raw session-env.sh. Use write_session_env only for ordinary plan-coverage setups that need the canonical baseline.



### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/tests/support/session.py
- **Concern**: seed_plan and seed_feature_description default bytes are unspecified. Scenario: make_implement_tmpdir must preserve _session dispatch seeds, but the plan does not pin default plan.txt and feature-description.txt content. Divergent defaults can pass migration while changing dispatch inputs.
- **Proposed resolution**: Pin defaults to the current _session bytes: plan.txt is "## Plan\n" and feature-description.txt is "feature\n"; assert them in test_foundation.py.



### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/tests/support/session.py
- **Concern**: make_design_tmpdir does not pin a default SESSION_ID. Scenario: The design baseline requires SESSION_ID, yet make_design_tmpdir gives no default. Migrated design-consumer tests can get inconsistent SESSION_ID values and flaky assertions.
- **Proposed resolution**: Pin one deterministic default (for example "test-session-1") and allow overrides; assert it in test_foundation.py.



### FINDING_9:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/tests/support/session.py
- **Concern**: write_design_source_env production wire shape is underspecified. Scenario: Production-style is ambiguous versus the lighter export lines in test_design_lifecycle._write_session_env. Missing shebang, generator comment, or shlex.quote exports can pass helper tests while diverging from write_design_env_main output that production-writer tests must match.
- **Proposed resolution**: Require the same wire shape as write_design_env_main: shebang, generator comment line, and export KEY=shlex.quote(value) rows in stable key order.



### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/tests/report/test_final_report.py:21-23
- **Concern**: Refactor _write_minimal_state through write_session_env conflicts with MODE and sparse session contract. Scenario: Plan requires refactoring _write_minimal_state to write_session_env with per-test overrides, but that helper rejects invalid keys and targets production session-env keys only. MODE=N/A is not in WRITE_ENV_KEYS or the implement baseline. A default-merging writer also injects REPO_ROOT, LARCH_CLAUDE_PLUGIN_ROOT, and tool keys that the minimal fixture deliberately omits. Either path changes inputs to write_final_report and coverage resolution versus today's two-key file.
- **Proposed resolution**: Keep _write_minimal_state as a raw two-line session-env write, or add an explicit carve-out: omit every implement baseline key and allow only non-writer test keys such as MODE via a documented sparse-fixture path. Do not route _write_minimal_state through the canonical default baseline.



### FINDING_11:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/tests/support/session.py
- **Concern**: seed_plan and seed_feature_description default bytes are unspecified. Scenario: _session seeds plan.txt as ## Plan\n and feature-description.txt as feature\n, while ordinary bootstrap setups still use plan\n (for example python/tests/state/test_bootstrap.py:1038). make_implement_tmpdir will pick one default for mechanical migration. Wrong or unstated defaults break dispatch parity or bootstrap coder tests.
- **Proposed resolution**: Pin defaults to ## Plan\n and feature\n for make_implement_tmpdir to match dispatch _session, and state that bootstrap sites with other bytes must call seed_plan or seed_feature_description with explicit content after tmpdir creation.



### FINDING_12:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/tests/report/test_final_report.py
- **Concern**: _write_minimal_state migration must omit the full implement baseline. Scenario: Plan requires refactoring _write_minimal_state through write_session_env, but that helper seeds implement baseline keys; merging defaults injects REPO_ROOT LARCH_CLAUDE_PLUGIN_ROOT and tool flags into fixtures that intentionally contain only REPO=o/r and MODE=N/A
- **Proposed resolution**: Require _write_minimal_state (and similar sparse fixtures) to pass omit= for every implement baseline key or keep them as raw session-env writes exempt from the shared writer refactor



### FINDING_13:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/tests/support/session.py
- **Concern**: write_session_env must allow additive overrides outside the implement baseline. Scenario: Plan text limits overrides to replacing baseline entries in place; migrated final-report fixtures need REPO and MODE, which are not in the implement baseline, and reject-invalid-keys can be read as WRITE_ENV_KEYS-only
- **Proposed resolution**: Document that overrides may add any safe KEY=value pair not in the baseline (including REPO MODE WORKFLOW_PATH LARCH_RUN_ID) and that invalid-key rejection targets malformed names or unsafe values, not production-writer allowlist exclusivity



