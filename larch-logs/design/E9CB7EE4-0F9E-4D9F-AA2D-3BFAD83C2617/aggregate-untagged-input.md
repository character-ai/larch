### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/larch/calibration/difficulty.py
- **Concern**: _adjacent_invalid_difficulty treats every difficulty: prefix as invalid-adjacent and skips legacy confidence: lines during the backward walk. Scenario: After auto-compose, a plan.txt trailer is emitted after ## Acceptance as difficulty/confidence/diff_lines:. _splice_plan_provenance then inserts review_status/rounds_completed immediately before the final diff_lines:, leaving difficulty/confidence outside _trailing_metadata_span. The adjacent walk skips confidence:, hits valid difficulty: MODERATE, returns True, and plan_difficulty() returns "" — the reported Step 5c publish failure persists
- **Proposed resolution**: Only return True for present-but-invalid difficulty lines (e.g. difficulty: EASY): when a walked line starts with difficulty:, return True only if it does not fullmatch _PLAN_DIFFICULTY_RE; valid stranded tiers must not trigger adjacent-invalid fail-closed

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/design/test_design_publish.py
- **Concern**: Step 5c regression fixture does not match the auto-compose + splice trailer layout from the bug report. Scenario: The plan writes composed-plan.md with difficulty: inside ## Plan and a separate terminal diff_lines:. Production auto-compose (_auto_compose_plan_md) places plan.txt trailers after ## Acceptance, and publish splices provenance before the last diff_lines:. A regression using only the in-Plan embedding can pass while the confidence-separated stranded trailer from the live path still fails under the proposed adjacent-invalid logic
- **Proposed resolution**: Build the fixture from plan.txt via _auto_compose_plan_md (or byte-match its output), include .step3-review-result.env so _splice_plan_provenance runs, and leave design-difficulty-rating.raw.json absent; assert publish succeeds on that post-compose/post-splice shape

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/tests/design/test_design_publish.py
- **Concern**: The tightened fake plan validate cannot call production trailing_plan_difficulty without a python/ bootstrap. Scenario: Publish subprocesses call CLAUDE_PLUGIN_ROOT/python/cli.py, which in these tests is the embedded fake CLI under a minimal tmp plugin tree with no larch package. Replacing the substring difficulty: check with trailing_plan_difficulty() requires importing larch.calibration.difficulty from the workspace python tree; without an explicit sys.path/env bootstrap (or delegating plan validate to the real python/cli.py), the mandated regression cannot enforce production trailing semantics
- **Proposed resolution**: In the fake validate branch, bootstrap sys.path to the workspace python package root (test-supplied env var) before importing difficulty.trailing_plan_difficulty(plan_text), or delegate plan validate to the real cli.py for this test only; keep rejecting mid-document-only tiers after rewrite

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/tests/design/test_design_publish.py
- **Concern**: The Step 5c regression still does not spell out how the embedded fake `plan validate` branch reaches production `trailing_plan_difficulty()` semantics.. Scenario: The fake CLI under `plugin_root/python/cli.py` is a standalone heredoc script with no `larch` on `sys.path`. Implementers can satisfy “trailing semantics” with a substring check or duplicated regex, so publish can pass while production `validate_plan_main` would still reject the same composed text. Round 2 left this neutral; the plan names the helper but not the wiring.
- **Proposed resolution**: In the new test, pass an env var with the real repo `python/` parent (or invoke production `plan validate` via subprocess). In the fake CLI `plan validate` branch, import `larch.calibration.difficulty` from that path and fail when `LARCH_REQUIRE_PLAN_DIFFICULTY=1` and `not difficulty.trailing_plan_difficulty(plan_text)`.

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/calibration/difficulty.py
- **Concern**: `_adjacent_invalid_difficulty` walk-start is ambiguous when `_trailing_metadata_span` returns `None`.. Scenario: The plan sets walk-start to `len(lines)` with no rule for the first examined index. Code that starts at `lines[len(lines)]` is out of range; code that decrements first can skip the terminal invalid `difficulty:` line and fall through to whole-document fallback, masking malformed final trailers the plan’s unit tests expect to return `""`.
- **Proposed resolution**: Specify inclusive start: when `span is None`, begin at `len(lines) - 1`; when `span` exists, begin at `span[0]` and walk backward, skipping blanks, `_PLAN_TRAILER_LINE_RE` matches, and legacy `^confidence: .+$` lines before testing `line.startswith("difficulty:")`.

### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/design/test_design_publish.py:219-262
- **Concern**: Step 5c regression must call production trailing difficulty in the fake validate subprocess, not duplicate regex semantics. Scenario: The plan says the fake `plan validate` branch must enforce `trailing_plan_difficulty()` semantics, but `_write_difficulty_recording_cli` already gates on the substring `"difficulty:" not in plan_text` (line 245). A copied regex or substring check can pass when `## Plan` embeds `difficulty: MODERATE` while the true trailing block still has only `diff_lines:`, so publish succeeds without exercising the trailing-metadata contract the bug depends on.
- **Proposed resolution**: Extend `_write_difficulty_recording_cli` (or add a sibling writer used only by the new regression): in the `plan validate` branch, bootstrap repo `python/` on `sys.path` via test-set `PYTHONPATH` (same pattern as `test_design_lifecycle.py`), `from larch.calibration import difficulty`, read `--plan-file`, and fail when `not difficulty.trailing_plan_difficulty(plan_text)` while `LARCH_REQUIRE_PLAN_DIFFICULTY=1`. Remove the substring gate at line 245.

### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/tests/design/test_design_publish.py:24-42
- **Concern**: Strict trailing validate must stay test-local; do not tighten shared `_write_fake_cli`. Scenario: The plan says tighten the fake helper "in this test" but does not name the existing split between `_write_fake_cli` (always-ok validate) and `_write_difficulty_recording_cli` (optional difficulty gate). Changing `_write_fake_cli` globally would break many harness tests that publish plans with only `diff_lines:` and no trailing `difficulty:` (e.g. `test_publish_splices_provenance_above_diff_lines`, `test_publish_cross_consumer_repo_root`).
- **Proposed resolution**: Name the harness explicitly: reuse or extend `_write_difficulty_recording_cli` with `FAKE_CLI_REQUIRE_DIFFICULTY=1` for the new stranded-shape regression; keep `_write_fake_cli` unchanged for unrelated publish tests.

### FINDING_8:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/calibration/difficulty.py
- **Concern**: _adjacent_invalid_difficulty walk-start is ambiguous when no trailing span exists. Scenario: The plan sets walk-start to len(lines) when _trailing_metadata_span returns None and says to walk backward from that index. With N lines (indices 0..N-1), starting at len(lines) without first decrementing skips the final line or raises IndexError, so a document that ends with an invalid difficulty: line and no diff_lines: trailer can still reach _last_plan_difficulty_line and accept an earlier embedded tier.
- **Proposed resolution**: Pin walk-start to len(lines) - 1 after trimming trailing blanks, or document that the first examined index is walk-start - 1; add/adjust the no-span invalid-trailer unit test to assert the last physical line is checked before any whole-document fallback.

### FINDING_9:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/tests/design/test_design_publish.py
- **Concern**: Step 5c regression fake validate still lacks a production-semantics bootstrap. Scenario: The plan requires the test-local fake plan validate branch to enforce trailing_plan_difficulty() on the final composed text, but the embedded fake CLI under CLAUDE_PLUGIN_ROOT has no import path to larch.calibration.difficulty and today uses a difficulty: substring check in _write_difficulty_recording_cli. Re-implementing trailing rules inline or keeping the substring guard lets publish pass while production validate_plan_main still rejects the stranded shape.
- **Proposed resolution**: In the new test only, extend the fake validate branch to import production difficulty (sys.path insert to the real plugin python tree via an env var such as LARCH_REAL_PLUGIN_ROOT, or subprocess-delegate to the real python/cli.py plan validate with the same env), and fail when trailing_plan_difficulty(plan_text) is empty under LARCH_REQUIRE_PLAN_DIFFICULTY=1.
