### [Plan Review] FINDING_1

### FINDING_1: Metadata scan misses blank-separated trailers
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The contiguous metadata scan stops at the first non-trailer line above `diff_lines:` and does not allow the common blank line immediately before `diff_lines:`, so valid-looking `diff_added:` / `mechanical_churn:` trailers can be ignored and the script silently falls back to legacy `diff_lines` gating.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Specify upward scan may skip one empty line directly above `diff_lines:` before collecting trailers; add harness case (trailers, blank, `diff_lines:`); document in Step 2b / `check-plan-size.md` Edge cases


### [Plan Review] FINDING_6

### FINDING_6: Authoring and rewrite prompts lack strict trailer grammar constraints
- **Reviewer(s)**: Cursor-dyn-trailer-grammar-drift, Codex-dyn-trailer-grammar-drift
- **Severity**: latent
- **Concern**: Plan-authoring and rewrite surfaces only say trailers go above `diff_lines:` and omit the final contiguous metadata block, malformed trailer, and duplicate-key rules, so rewritten plans may be preserved in a form that `check-plan-size.sh` ignores or resolves unexpectedly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-trailer-grammar-drift, Codex-dyn-trailer-grammar-drift: Add a short cross-reference at each authoring/rewrite surface: optional size trailers must stay in the final contiguous metadata block defined by check-plan-size.md; malformed variants are ignored; duplicate keys use the last trailer in that block.


### [Plan Review] FINDING_7

### FINDING_7: Waterfall trailer-preservation spec is not implementable enough
- **Reviewer(s)**: Cursor-dyn-revision-trailer-spec, Codex-dyn-revision-trailer-spec
- **Severity**: important
- **Concern**: The waterfall revision plan says to preserve or recompute optional trailers but does not identify the exact `compose_prompt()` insertion point or require a deterministic post-apply validation, so a prompt-only change could still accept revisions that drop trailers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-revision-trailer-spec: Add to plan: extend compose_prompt() (lines 126-143), append one Hard rules printf after line 134 with concrete text (preserve diff_added/diff_deleted/mechanical_churn in final metadata block above diff_lines: unless intentionally recomputed; include example lines)
  - From Codex-dyn-revision-trailer-spec: Specify the minimal deterministic contract: edit compose_prompt's hard-rules text at lines 126-142 and add a post-apply check before success that, when the original plan had any optional size trailers, the revised final metadata block still contains preserved or recomputed optional trailers above final diff_lines; reject and restore otherwise. Do not add a recomputation engine.


