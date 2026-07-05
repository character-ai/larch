### [Plan Review] FINDING_1

### FINDING_1: Reviewer prompt regeneration can ship incomplete
- **Reviewer(s)**: Cursor-Arch, Codex-Pragmatic
- **Severity**: important
- **Concern**: The prompt-regeneration workflow can leave checked-in reviewer artifacts out of sync if the plan does not explicitly cover both the hand-maintained reviewer bodies and `agents/pre-rendered/.manifest` in the right order.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In Approach and Testing strategy, require this order: edit `reviewer-templates.md`, regenerate the four template-owned agents, manually sync the five hand-maintained `agents/reviewer-*.md` files, then run `python3 python/cli.py generate pre-rendered-reviewer-prompts` and `generate check`
  - From Codex-Pragmatic: Add `agents/pre-rendered/.manifest` to the `UPDATED` list and regenerate it with the pre-rendered bodies.


### [Plan Review] FINDING_3

### FINDING_3: Rejected-OOS audit should reuse TSV schema-gated voting helpers
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The rejected-OOS audit path risks trusting malformed `findings-classification.tsv` rows or bypassing the existing voting parser, which can misclassify rows unless schema support and footer fallback are preserved.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In `review_phase_detail.py`, load the sibling `findings-classification.tsv` once per round, build a `finding_id -> voting_result` map via the existing `voting` helpers when schema-supported, and fall back to `_vote_result` only when the TSV is absent or unusable
  - From Cursor-Pragmatic: Gate each per-round TSV with voting.classification_tsv_schema_supported(text, panel_kind="code-review") (same contract as rejected_analysis._join_run_findings); when unsupported or unreadable, treat the file as absent and use footer parsing per block


### [Plan Review] FINDING_4

### FINDING_4: Cap-1 rollup priority labels can collapse
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: When rebuilding label state from rolled-up design OOS data, duplicate issue URLs can overwrite earlier priority and drop the shared issue's high-risk label.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Aggregate priority per URL with OR semantics across all matching originals, or persist the rolled-up priority alongside the sentinel rows, and add a cap-1 label-only retry regression test.


### [Plan Review] FINDING_5

### FINDING_5: Neutral audit outcomes lack test coverage
- **Reviewer(s)**: Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: important
- **Concern**: The planned TSV-first audit tests do not cover neutral outcomes, so a regression could drop neutral OOS candidates when footers are absent or malformed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add a fixture where findings-classification.tsv has voting_result=neutral for OOS_N with no usable Vote tally footer and assert the candidate still appears in render_rejected_oos_audit_section output
  - From Codex-Pragmatic: Add a TSV-first neutral-row case, ideally with a missing or malformed footer, and assert the candidate still renders.

