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


