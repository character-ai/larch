### FINDING_1: Metadata scan misses blank-separated trailers
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The contiguous metadata scan stops at the first non-trailer line above `diff_lines:` and does not allow the common blank line immediately before `diff_lines:`, so valid-looking `diff_added:` / `mechanical_churn:` trailers can be ignored and the script silently falls back to legacy `diff_lines` gating.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Specify upward scan may skip one empty line directly above `diff_lines:` before collecting trailers; add harness case (trailers, blank, `diff_lines:`); document in Step 2b / `check-plan-size.md` Edge cases

### FINDING_2: Optional trailers still count toward PLAN_LINES
- **Reviewer(s)**: Codex-Arch, Cursor-Edge, Codex-Edge, Cursor-Innovation, Codex-Innovation
- **Severity**: important
- **Concern**: Optional metadata trailers remain included in the `PLAN_LINES` body count, so a plan under the 800-line body limit can hard-trigger solely because `diff_added`, `diff_deleted`, or `mechanical_churn` lines were added above `diff_lines:`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Subtract the final optional metadata-block line count when computing PLAN_LINES, or compute plan_body_lines after parsing the block; add a boundary test with 800 body lines plus optional trailers
  - From Cursor-Edge, Codex-Edge: After parsing the final metadata block, exclude those optional trailer lines from PLAN_LINES or explicitly revise the contract/tests to state that metadata counts toward the 800-line body gate
  - From Cursor-Innovation: Keeping plan_lines as trailer_nr-1 means each diff_added/diff_deleted/mechanical_churn line consumes plan-body budget; a ~798-line plan plus three trailers can trip plan_lines>800 while the same body without trailers would not Document in check-plan-size.md/flags.md that metadata lines count toward PLAN_LINES, or subtract the parsed metadata block from plan_lines after trailer scan (small change after line 90, not a lines-1-90 rewrite)
  - From Codex-Innovation: Compute PLAN_LINES as physical lines before the final metadata block when optional trailers are present, while preserving legacy behavior when absent

### FINDING_3: Discussion rewrites can drop optional trailers
- **Reviewer(s)**: Cursor-Edge, Codex-Edge, Codex-Innovation, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: The post-plan Gate A discussion revision path can rewrite `plan.txt`, rerun `EMIT_PLAN` and Step 2b.5, and drop `diff_added`, `diff_deleted`, or `mechanical_churn`, causing mechanical or deletion-heavy plans to regress to legacy `diff_lines` hard-gating.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge, Codex-Edge: Update discussion-rounds.md plan-revision authority to preserve or recompute optional plan-size trailers above final diff_lines, matching Gate B/waterfall guidance
  - From Codex-Innovation: Extend the same preserve-or-recompute rule to the post-plan discussion revision path, keeping optional trailers directly above final diff_lines
  - From Codex-Pragmatic: Add skills/design/references/discussion-rounds.md to the UPDATED list and revise its plan revision authority text to preserve or recompute diff_added, diff_deleted, and mechanical_churn in the final metadata block above diff_lines when it rewrites plan.txt.
  - From Cursor-Requirements: Add a minimal UPDATED entry for skills/design/references/discussion-rounds.md requiring any post-plan direct plan.txt revision to preserve or recompute diff_added diff_deleted and mechanical_churn in the final metadata block above diff_lines before re-running ACTION=EMIT_PLAN

### FINDING_4: Missing regression test for additions-keyed hard diff
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The harness lacks a case where `diff_added` is present and below the additions threshold while `diff_lines` exceeds the legacy threshold, so an implementation could still incorrectly hard-trigger on total churn.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add one case with diff_added under 2000 and diff_lines above 1500 asserting HARD_TRIGGER_FIRED=false TRIGGER_REASONS empty and DIFF_ADDED set.

### FINDING_5: Optional trailer grammar contract is underspecified
- **Reviewer(s)**: Cursor-dyn-trailer-grammar-drift, Codex-dyn-trailer-grammar-drift
- **Severity**: important
- **Concern**: The authoritative machine-contract docs do not spell out the exact accepted trailer regexes, `mechanical_churn: false` handling, block-stop behavior, malformed-as-absent behavior, or duplicate-key resolution, leaving room for implementation and prompt drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-trailer-grammar-drift, Codex-dyn-trailer-grammar-drift: Make check-plan-size.md spell out the three accepted full-line regexes, that upward scanning stops at the first line above diff_lines that is not one of those trailer regexes, and that duplicate keys use the last match inside that contiguous block.

### FINDING_6: Authoring and rewrite prompts lack strict trailer grammar constraints
- **Reviewer(s)**: Cursor-dyn-trailer-grammar-drift, Codex-dyn-trailer-grammar-drift
- **Severity**: latent
- **Concern**: Plan-authoring and rewrite surfaces only say trailers go above `diff_lines:` and omit the final contiguous metadata block, malformed trailer, and duplicate-key rules, so rewritten plans may be preserved in a form that `check-plan-size.sh` ignores or resolves unexpectedly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-trailer-grammar-drift, Codex-dyn-trailer-grammar-drift: Add a short cross-reference at each authoring/rewrite surface: optional size trailers must stay in the final contiguous metadata block defined by check-plan-size.md; malformed variants are ignored; duplicate keys use the last trailer in that block.

### FINDING_7: Waterfall trailer-preservation spec is not implementable enough
- **Reviewer(s)**: Cursor-dyn-revision-trailer-spec, Codex-dyn-revision-trailer-spec
- **Severity**: important
- **Concern**: The waterfall revision plan says to preserve or recompute optional trailers but does not identify the exact `compose_prompt()` insertion point or require a deterministic post-apply validation, so a prompt-only change could still accept revisions that drop trailers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-revision-trailer-spec: Add to plan: extend compose_prompt() (lines 126-143), append one Hard rules printf after line 134 with concrete text (preserve diff_added/diff_deleted/mechanical_churn in final metadata block above diff_lines: unless intentionally recomputed; include example lines)
  - From Codex-dyn-revision-trailer-spec: Specify the minimal deterministic contract: edit compose_prompt's hard-rules text at lines 126-142 and add a post-apply check before success that, when the original plan had any optional size trailers, the revised final metadata block still contains preserved or recomputed optional trailers above final diff_lines; reject and restore otherwise. Do not add a recomputation engine.

### FINDING_8: Waterfall preservation path needs an automated harness case
- **Reviewer(s)**: Codex-dyn-revision-trailer-spec
- **Severity**: important
- **Concern**: The testing strategy only allows a spot-check for revision preservation and does not require a focused `revise-plan-with-waterfall` regression test, so trailer-dropping behavior could survive relevant checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-revision-trailer-spec: Require one focused automated case in scripts/test-revise-plan-with-waterfall.sh: start with a plan containing diff_added, diff_deleted, mechanical_churn, and diff_lines; have one candidate drop the optional trailers and verify it is rejected or falls through; have the winning candidate preserve them above final diff_lines.
