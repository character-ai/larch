### FINDING_1: Fake validate must require the trailing difficulty block
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The regression's fake `plan validate` branch can still pass when `difficulty:` appears anywhere in `## Plan`, so the test does not force the trailing-metadata lookup that the bug depends on.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Mandate `FAKE_CLI_REQUIRE_DIFFICULTY=1`, and change the fake `plan validate` branch to fail when trailing metadata lacks a valid tier (e.g. mirror `difficulty.plan_difficulty(plan_text)` or scan `difficulty.trailing_plan_metadata_lines()`), not when the substring is absent anywhere.


### FINDING_2: Regression must leave the raw difficulty sidecar absent
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: The Step 5c regression can still bypass the missing-sidecar publish path if it writes or synthesizes `design-difficulty-rating.raw.json`, so a broken `_resolve_publish_difficulty_rating()` fallback would remain untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Explicitly require no `design-difficulty-rating.raw.json` in this test. Assert post-publish trailing metadata and `difficulty sync-labels` / `write-record --design-tier MODERATE` via `FAKE_CLI_CALL_LOG`, extending the fake CLI with those stubs if needed.
  - From Codex-Arch: Omit the sidecar from the regression fixture, or assert it is absent before publish so the test actually hits the missing-sidecar path
  - From Cursor-Innovation: Mandate that the new publish regression leaves `design-difficulty-rating.raw.json` absent. Assert trailing-block order and `difficulty` sync-labels/write-record calls only. Drop the sidecar simulation option from the test plan.
  - From Cursor-Pragmatic: Require the regression fixture to leave design-difficulty-rating.raw.json absent. Assert trailing-block order only after publish succeeds without any raw-rating file.
  - From Codex-Pragmatic: Leave the sidecar absent in this scenario and tighten the fake validator to require difficulty only in the final trailer block.
  - From Cursor-Requirements: State explicitly that the regression reproduces the drafter-subprocess gap: do not create design-difficulty-rating.raw.json. Keep the stranded composed-plan shape, step-3 provenance env, and final-trailer assertions (review_status, rounds_completed, difficulty: MODERATE, diff_lines). Optionally tighten the local fake validate helper to require trailing difficulty via difficulty.plan_difficulty(), not any difficulty: substring.
  - From Codex-Requirements: Leave `design-difficulty-rating.raw.json` absent in the regression and let `design publish` recover from the stranded plan text end to end; keep a separate sidecar-present smoke test only if needed.


### FINDING_3: Publish setup needs the step-3 completion sentinel
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: Without `.completed/step-3`, `publish_core` stops before the difficulty splice/validate sequence, so the regression never reaches the bug it is supposed to cover.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Create `.completed/step-3` alongside `.step3-review-result.env`, matching `test_publish_splices_provenance_above_diff_lines`.


### FINDING_4: Whole-document fallback must not mask an invalid trailer
- **Reviewer(s)**: Codex-Arch
- **Severity**: blocking
- **Concern**: A whole-document fallback can mask a malformed trailing `difficulty:` line and let publish succeed by rewriting around the defect instead of preserving it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Only fall back when the trailing metadata span has no difficulty line at all, or fail fast when a trailing difficulty line exists but is invalid


### FINDING_1: Trailing difficulty guard must reject malformed final trailers
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: The trailing-metadata difficulty scan only checks the line immediately above a detected trailer span, and the no-span path can fall through to whole-document fallback without validating a malformed final `difficulty:` line. That means an invalid terminal trailer can be masked by an earlier valid embedded tier, and the `span is None` case can also lead to incorrect indexing or skipping of the invalid trailer check when blanks or a `confidence:` line separate `difficulty:` from `diff_lines:`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: `After the trailing scan finds no valid tier, walk backward from the last diff_lines: through contiguous trailer-shaped lines and also scan any difficulty:-prefixed lines in that region; if any such line fails tier validation, return "" before calling the whole-document fallback. Add a unit test with difficulty: EASY, confidence: high, diff_lines: <N> plus an earlier valid embedded difficulty: MODERATE.`
  - From Codex-Arch: `When no trailing span exists, also inspect the last nonblank line for a difficulty: prefix and return "" before invoking the fallback.`
  - From Cursor-Innovation: `Walk backward from start skipping blank lines (or reuse the same backward scan _trailing_metadata_span uses) and return "" when the first non-blank line above the span starts with difficulty:.`
  - From Codex-Innovation: `Before invoking the fallback, strip trailing blanks and return "" when the final nonblank line starts with difficulty: but fails _PLAN_DIFFICULTY_RE.fullmatch; keep the adjacent-to-span check for the invalid-before-`diff_lines` case. Add a focused unit case for this shape.`
  - From Cursor-Pragmatic: `In step 2, guard if span is not None: before the invalid-adjacent difficulty: check; when span is None, skip straight to the fallback helper (or return "" if the helper also finds nothing). Add a unit case with mid-document difficulty: and no terminal trailer block to lock this branch.`
  - From Codex-Pragmatic: `Before whole-document fallback, inspect the last nonblank line when no trailing span exists and return "" if it starts with difficulty:. Add the focused unit case.`
  - From Codex-Requirements: `Before invoking the whole-document fallback, inspect the trailer-adjacent suffix across the legacy confidence: line and return "" if it contains a difficulty:-prefixed line that fails _PLAN_DIFFICULTY_RE; add the matching unit case.`


### FINDING_3:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/design/_plan_quality_commands.py:871-877; python/tests/design/test_design_publish.py:232-251
- **Concern**: [SCOPE-REDUCTION] Required difficulty validation can still use the widened whole-document fallback. Scenario: After `plan_difficulty()` starts returning a mid-document tier, `validate_plan_main` and a fake validate helper implemented with `plan_difficulty()` can accept a composed plan whose final trailer has only `diff_lines:`. That weakens `LARCH_REQUIRE_PLAN_DIFFICULTY=1` and lets the regression pass without proving a true trailing `difficulty:` line.
- **Proposed resolution**: Make the real required-validation branch and the fake publish-test helper compute required difficulty from `trailing_plan_metadata_lines()` directly; reserve the new fallback for publish recovery before rewrite.

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


