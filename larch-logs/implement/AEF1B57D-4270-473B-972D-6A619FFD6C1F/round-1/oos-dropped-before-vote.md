### OOS_1: [OUT_OF_SCOPE] Design skill still has unqualified runtime citations
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: latent
- **Concern**: `skills/design/SKILL.md` still has a follow/load citation that lacks the new runtime qualifier, so the widened classifier can miss it unless a separate audit covers it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Add an only-when/on qualifier matching runtime conditions or track via a separate audit follow-up.

### OOS_2: [OUT_OF_SCOPE] Research skill still has untracked runtime citations
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: latent
- **Concern**: `skills/research/SKILL.md` still contains mandatory orchestrator-never and unqualified run-id-flag references that remain outside the current baseline union.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Extend prose qualifiers and real-scan assertions to research in a follow-up PR.

### OOS_3: [OUT_OF_SCOPE] Conditional-reference regex is punctuation-sensitive
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-closure-classifier
- **Severity**: important
- **Concern**: `CONDITIONAL_REFERENCE_RE` is still punctuation-sensitive: it misses split-sentence conditional prose, treats comma-separated qualifiers as untracked, and relies on commas to keep some explicit exclusions from being classified at all.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Document the constraint for skill authors or adjust the regex if comma-separated qualifiers are needed.
  - From cursor-specialist-edge-cases: Document authoring constraint or widen lookahead to allow comma before only <qualifier>
  - From dyn-dyn-closure-classifier: Narrow the guard to sentence boundaries that actually terminate the operand (for example `(?![.]\s)` only), or run a second pass for `Load it only for` after an earlier `…foo.md` on the same line; add a regression test using the line 281 wording.
  - From dyn-dyn-closure-classifier: A small explicit exclusion set would be more robust than punctuation-sensitive regex behavior.

### OOS_4: [OUT_OF_SCOPE] Ratchet misses runtime refs that evade all classifier arms
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-closure-classifier
- **Severity**: latent
- **Concern**: The ratchet still only protects files that already land in the eager/conditional baselines, so runtime references that fail every classifier arm can reappear without a lint failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Extend classifier/ratchet to other skills or add a watchlist when audit confirms gaps
  - From cursor-specialist-testing: Track follow-up classifier work only if a later audit confirms additional runtime closure gaps.

### OOS_5: [OUT_OF_SCOPE] `_clean_raw_path` punctuation trim changed without a test
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: `_clean_raw_path` now trims punctuation asymmetrically, changing path resolution behavior globally without a dedicated regression test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add a small `_clean_raw_path` or path-extraction fixture if ticked paths with leading punctuation ever appear in ratcheted prompts.
