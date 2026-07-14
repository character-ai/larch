### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/tests/support/design_wire.py:NEW
- **Concern**: result_env validation reimplements session env key/value guards (G-Fix-1). Scenario: session.py already enforces ^[A-Z_][A-Z0-9_]*$ keys and rejects newline CR NUL values; a parallel copy in design_wire risks divergent fixture contracts
- **Proposed resolution**: Extract shared KV validation in tests.support (or export helpers from session.py) and call it from result_env_lines / write_result_env

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/tests/design/test_plan_quality.py
- **Concern**: `plan_body` is NEW/UPDATED-only but the migration target includes valid `### MAY_UPDATE:` / `### REWRITTEN:` plans. Scenario: `test_compose_revise_prompt_preserves_optional_heading_type` and `_heading_count` use valid non-NEW/UPDATED headings. The Edge cases line defers extra heading kinds, while the migration bullet says to move normal heading fixtures to the shared builder, so implementers can either over-expand `plan_body` or migrate those tests and break prompt/heading assertions.
- **Proposed resolution**: In `test_plan_quality.py` migration notes, explicitly keep heading-type preservation and multi-kind heading-count fixtures inline. Limit `plan_body` to NEW/UPDATED unless a follow-up piece expands scope.

### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/tests/support/design_wire.py
- **Concern**: diff_lines_trailer should delegate to larch.design.plan_grammar.compose_trailer_lines. Scenario: Hand-rolled diff_lines: lines can accept values plan_grammar rejects (octal, bad difficulty casing, wrong ordering) and diverge from fixtures that already use compose_trailer_lines in design tests
- **Proposed resolution**: Make diff_lines_trailer a thin wrapper around compose_trailer_lines for the requested keys; join with a single trailing newline to match existing plan.txt fixtures

### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/tests/support/design_wire.py
- **Concern**: plan_body should validate each emitted ### NEW:/### UPDATED: line with plan_grammar.match_heading. Scenario: Builders that format paths with ad hoc spacing or backticks can produce plans tests treat as valid but plan command parsing and heading-count logic reject, weakening the migration
- **Proposed resolution**: After formatting headings, assert match_heading succeeds for every line (or raise ValueError); document that paths must use the colon form the grammar accepts

### FINDING_9:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/tests/support/design_wire.py
- **Concern**: Plan leaves write_result_env key-validation contract ambiguous relative to lifecycle migration. Scenario: Implementing write_result_env with PHASE_RESULT_ENV_ALLOW_KEYS (as production phase_driver_write_result_env does) rejects ROUTE=, INIT_STATUS=, and RUN_PARAMS_PATH= rows that test_design_lifecycle.py still intends to migrate, so setup fails or migration is abandoned mid-PR
- **Proposed resolution**: Specify validation uses shell-var-name checks only (reuse design_session._valid_var_name / tests.support.session _KEY_RE) and explicitly not PHASE_RESULT_ENV_ALLOW_KEYS; or add an allow_keys parameter with presets from design_step0_env (INIT_RESULT_KEYS, ROUTE_RESULT_KEYS) and document which preset each migrated file uses

### FINDING_10:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/tests/support/design_wire.py
- **Concern**: run_params_json is specified independently of existing schema-v3 seed_run_params. Scenario: A second copy of schema-v3 defaults or json.dumps formatting diverges from tests.support.session.seed_run_params, reintroducing the whitespace/key-order breakage the plan failure modes warn about and undermining the one-file wire-edit goal
- **Proposed resolution**: Implement run_params_json as a thin wrapper over the same shared payload builder seed_run_params uses (_RUN_PARAMS_SCHEMA_V3 merge plus json.dumps(indent=2, sort_keys=False) and trailing newline); do not duplicate the schema dict

### FINDING_13:
- **Reviewer(s)**: Cursor-dyn-Wire Fixture Boundary
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/tests/design/test_design_publish.py:897-915 python/tests/design/test_design_lifecycle.py:3071-3072 python/tests/support/design_wire.py (planned)
- **Concern**: plan_body as specified cannot build dominant ordinary plan fixtures. Scenario: Most migrated valid plans are section markdown (## Plan / ## Approach / ## Testing strategy) with optional difficulty trailers and no ### NEW:/### UPDATED: headings; the NEW module spec only lists firm file headings while UPDATED test_design_publish.py requires building ordinary composed-plan fixtures with plan_body
- **Proposed resolution**: Extend the plan_body contract with a body/sections parameter (or plan_markdown prefix) plus optional ordered trailer lines before diff_lines_trailer; keep only firm-heading ordering in the file-heading slice

### FINDING_14:
- **Reviewer(s)**: Cursor-dyn-Wire Fixture Boundary
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/tests/design/test_design_publish.py:2179-2187 python/tests/support/session.py:236-255
- **Concern**: Unqualified make_design_tmpdir migration can break publish capture source-env tests. Scenario: _run_publish_capture_case seeds source-env.sh as a minimal SESSION_ID=RUN1 stub that publish later augments (assert LARCH_CLAUDE_SOURCE_FILE= at line 2314); make_design_tmpdir always writes bash export source-env via write_design_source_env
- **Proposed resolution**: Name an explicit carve-out in test_design_publish.py migration: keep hand-written minimal/non-export source-env stubs inline; use make_design_tmpdir only on paths that do not assert publish-side source-env mutation semantics ## Findings ### 1. architecture — Duplicate `run_params_json` (major, in-scope) Piece 2 already exposes `seed_run_params` in `python/tests/support/session.py` with schema-v3 defaults, `indent=2`, and a trailing newline. The planned `run_params_json` in `design_wire.py` repeats the same contract. Two writers will drift on defaults, key order, and whitespace. **Suggested revision:** `run_params_json` should delegate to `session.seed_run_params` (or re-export it), not duplicate `_RUN_PARAMS_SCHEMA_V3`. ### 2. correctness — `plan_body` API too narrow for ordinary fixtures (major, in-scope) The planned `plan_body` only covers ordered `### NEW:` / `### UPDATED:` sections. Most ordinary fixtures in the migration set do not use firm headings at all. Examples: - `test_design_publish.py` builds full section plans with `difficulty:` trailers and no firm headings (`897-915`). - `test_design_lifecycle.py` repeatedly uses `## Plan\n\ndiff_lines: 1\n` (`3071` and similar). The plan’s `### UPDATED: python/tests/design/test_design_publish.py` line says to build ordinary plans with `plan_body`, but the NEW module spec cannot produce those shapes. **Suggested revision:** Extend `plan_body` with a freeform body/sections argument (and optional ordered grammar trailers before `diff_lines_trailer`), or split `plan_markdown` + `plan_file_headings`. Keep malformed and fidelity literals inline per the plan. ### 3. risk-integration — `make_design_tmpdir` carve-out for publish source-env stubs (minor, in-scope) `make_design_tmpdir` (`session.py:236-255`) always writes production-style `source-env.sh`. `test_design_publish.py:_run_publish_capture_case` (`2179-2187`) intentionally seeds a minimal `SESSION_ID=RUN1\n` stub that publish mutates; tests assert post-publish content at `2314`. Blind replacement with `make_design_tmpdir` can change source-env semantics on those paths. **Suggested revision:** Keep minimal/non-export `source-env.sh` stubs inline in publish capture tests; use `make_design_tmpdir` only where `source-env.sh` content is not part of the assertion surface. --- ## [OUT_OF_SCOPE] (tracked follow-ups, cap 3) 1. **architecture** — `python/test_support.py:35-58`: Re-exporting `design_wire` helpers from `test_support.py` for parity with session helpers. Nice for ergonomics; not required for correctness because `test_foundation.py` already imports `review_wire` from `tests.support` directly. 2. **code-quality** — `python/larch/design/plan_grammar.py:38-44`: A full `plan_trailers()` builder for `CANONICAL_TRAILER_ORDER` (`difficulty`, `diff_added`, `mechanical_churn`, etc.). Issue scope names only `diff_lines_trailer`; ordinary publish fixtures can keep `difficulty:` lines inline or composed until a later piece needs one-file trailer edits. 3. **security** — `python/larch/design/design_terminal.py:79-88`: Symlink refusal on `write_result_env`. Production writers refuse symlinks; a test-only helper need not mirror that unless a migrated test exercises symlink trust boundaries (those stay inline in `test_clarify.py` / lifecycle tests today). --- ## What the plan gets right - Malformed, legacy, and injection fixtures stay inline (aligned with `review_wire.py:3-5`). - `write_result_env` / `result_env_lines` should follow `larch_io.format_kvs` (`python/larch/io.py:452-461`): caller order preserved, `KEY=value\n`, terminal newline. - `test_foundation.py` expansion matches how Piece 1 tests `review_wire` (`test_foundation.py:41-101`). - `source-env.sh` is publish-excluded (`design_log_publish_flow.py:128-137`), so `make_design_tmpdir` is unlikely to break log-tree inclusion tests in `test_design_log_publish_flow.py`. - Negative result-env fixtures with embedded newlines correctly remain inline (`test_design_lifecycle.py:138-156` exercises production read filtering, not the shared writer).

### FINDING_15:
- **Reviewer(s)**: Codex-dyn-Wire Fixture Boundary
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/tests/design/test_plan_quality.py:35-37; python/tests/design/test_plan_quality.py:328-340
- **Concern**: Specify that plan_body supports valid one-kind heading sets, including UPDATED-only plans. Scenario: The planned migration covers normal heading fixtures, but existing valid fixtures contain no NEW section; a builder that always emits both sections cannot replace them without adding nonexistent headings
- **Proposed resolution**: Define optional ordered new and updated inputs that emit only supplied headings, and add an exact UPDATED-only builder assertion

### FINDING_16:
- **Reviewer(s)**: Codex-dyn-Wire Fixture Boundary
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/state/session_env.py:1552-1560; python/tests/support/session.py:201-213
- **Concern**: Specify byte-compatible run_params_json serialization. Scenario: The plan requires deterministic seeds but does not require the production schema-v3 key order and indent=2 JSON shape; a compact or reordered serializer would silently change migrated wire fixtures
- **Proposed resolution**: Require run_params_json to match the existing production/shared serializer, including key order, indentation, override placement, and one terminal newline, with an exact-string foundation test
