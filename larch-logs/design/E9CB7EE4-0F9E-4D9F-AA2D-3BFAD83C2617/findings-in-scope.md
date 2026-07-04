### FINDING_1: Trailing difficulty scan can miss a valid stranded trailer
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements
- **Severity**: blocking
- **Concern**: `_adjacent_invalid_difficulty` / walk-start handling can skip a valid `difficulty:` line that has been stranded above the final trailer block, so `plan_difficulty()` returns `""` even though the document still contains a real difficulty tier.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Only return True for present-but-invalid difficulty lines (e.g. difficulty: EASY): when a walked line starts with difficulty:, return True only if it does not fullmatch _PLAN_DIFFICULTY_RE; valid stranded tiers must not trigger adjacent-invalid fail-closed
  - From Cursor-Innovation: Specify inclusive start: when `span is None`, begin at `len(lines) - 1`; when `span` exists, begin at `span[0]` and walk backward, skipping blanks, `_PLAN_TRAILER_LINE_RE` matches, and legacy `^confidence: .+$` lines before testing `line.startswith("difficulty:")`.
  - From Cursor-Requirements: Pin walk-start to `len(lines) - 1` after trimming trailing blanks, or document that the first examined index is walk-start - 1; add/adjust the no-span invalid-trailer unit test to assert the last physical line is checked before any whole-document fallback.

### FINDING_2: Regression fixture doesn't mirror the auto-compose/post-splice shape
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The Step 5c regression fixture only exercises an in-Plan embedded `difficulty:` line, not the live auto-composed document where provenance is spliced before the trailing `diff_lines:` block, so the test can pass while the real publish path still fails.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Build the fixture from plan.txt via _auto_compose_plan_md (or byte-match its output), include .step3-review-result.env so _splice_plan_provenance runs, and leave design-difficulty-rating.raw.json absent; assert publish succeeds on that post-compose/post-splice shape

### FINDING_3: Fake validate must bootstrap production trailing semantics
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The publish regression's fake `plan validate` branch can still be satisfied by substring or duplicated-regex logic unless it imports the production `trailing_plan_difficulty()` implementation with a real `python/` path bootstrap, and that harness should remain test-local instead of tightening the shared fake CLI globally.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In the fake validate branch, bootstrap sys.path to the workspace python package root (test-supplied env var) before importing difficulty.trailing_plan_difficulty(plan_text), or delegate plan validate to the real cli.py for this test only; keep rejecting mid-document-only tiers after rewrite
  - From Cursor-Innovation: In the new test, pass an env var with the real repo `python/` parent (or invoke production `plan validate` via subprocess). In the fake CLI `plan validate` branch, import `larch.calibration.difficulty` from that path and fail when `LARCH_REQUIRE_PLAN_DIFFICULTY=1` and `not difficulty.trailing_plan_difficulty(plan_text)`.
  - From Cursor-Pragmatic: Extend `_write_difficulty_recording_cli` (or add a sibling writer used only by the new regression): in the `plan validate` branch, bootstrap repo `python/` on `sys.path` via test-set `PYTHONPATH` (same pattern as `test_design_lifecycle.py`), `from larch.calibration import difficulty`, read `--plan-file`, and fail when `not difficulty.trailing_plan_difficulty(plan_text)` while `LARCH_REQUIRE_PLAN_DIFFICULTY=1`. Remove the substring gate at line 245.
  - From Cursor-Pragmatic: Name the harness explicitly: reuse or extend `_write_difficulty_recording_cli` with `FAKE_CLI_REQUIRE_DIFFICULTY=1` for the new stranded-shape regression; keep `_write_fake_cli` unchanged for unrelated publish tests.
  - From Cursor-Requirements: In the new test only, extend the fake validate branch to import production difficulty (sys.path insert to the real plugin python tree via an env var such as LARCH_REAL_PLUGIN_ROOT, or subprocess-delegate to the real python/cli.py plan validate with the same env), and fail when trailing_plan_difficulty(plan_text) is empty under LARCH_REQUIRE_PLAN_DIFFICULTY=1.
