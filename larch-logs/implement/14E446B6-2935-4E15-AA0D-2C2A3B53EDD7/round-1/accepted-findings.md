### FINDING_1: **Important** correctness — `scripts/compose-review-findings.sh:180`  
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** correctness — `scripts/compose-review-findings.sh:180`      `code-review-oos` only recognizes headings shaped as `### OOS_N: ...`, but production `oos.md` entries are written as `### FINDING_N: [OUT_OF_SCOPE] ...` by `skills/review/scripts/collect-findings.sh:392-399` and then preserved by `skills/review/scripts/tally-code-votes.sh:354-355`. Concrete failing scenario: a round with OOS findings produces `round-1/oos.md`, but `compose-review-findings.sh` emits zero `outcome="out_of_scope"` records, so Gap 3 remains unfixed for real runs. Update the parser and regression fixture to cover the actual `FINDING_N: [OUT_OF_SCOPE]` shape, while still mapping emitted JSONL ids to `OOS_C...` if that is the desired schema.
- **Suggested revision**: Address the concern above.


### FINDING_10: correctness: scripts/compose-review-findings.sh:180-196
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] code-review-oos lacks inner-### handling; shared flush drops trailing body An oos.md finding with a mid-body ### subsection (e.g. ### Notes) truncates the emitted prose_body and drops following lines until the next OOS header, corrupting miner JSONL silently. Mirror code-review-rejected inner-heading logic for code-review-oos when pending_id is set.
- **Suggested revision**: Address the concern above.


### FINDING_11: correctness: scripts/compose-review-findings.sh:74-81
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] extract_reviewer_from_body only handles singular bold Reviewer at column 1 Finding body uses only - **Reviewers**: ... or plain Reviewer: lines; JSONL reviewer becomes panel while lib-vote-tally extracts real labels in the same PR Align patterns with reviewer_for_block or share extraction helper
- **Suggested revision**: Address the concern above.


### FINDING_14: correctness: scripts/compose-review-findings.sh:74-81
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] extract_reviewer_from_body only matches singular bold - **Reviewer**: lines, unlike reviewer_for_block which also accepts Reviewers and plain Reviewer:. JSONL reviewer falls back to panel for bodies that only use plural or unbolded attribution, diverging from tally extraction. Align extraction with reviewer_for_block patterns or share one helper.
- **Suggested revision**: Address the concern above.


### FINDING_18: risk-integration: scripts/compose-review-findings.sh:74-81
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] extract_reviewer_from_body only matches singular bold - **Reviewer**: at column 1 Body uses - **Reviewers**: or plain Reviewer: (allowed elsewhere in lib-vote-tally); reviewer becomes panel while tally attributes a real slot — inconsistent cross-pipeline semantics. Align extraction with reviewer_for_block rules or document and enforce a single canonical line shape upstream.
- **Suggested revision**: Address the concern above.


### FINDING_19: risk-integration: scripts/compose-review-findings.sh:74-81
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] extract_reviewer_from_body only handles singular - **Reviewer**: Bodies using - **Reviewers**: or plain Reviewer: (now supported by reviewer_for_block) still yield reviewer="panel" in JSONL. Reuse the same anchored patterns as reviewer_for_block or add compose tests for plural/plain lines.
- **Suggested revision**: Address the concern above.


### FINDING_2: **Important** security — `SECURITY.md:36`  
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Important** security — `SECURITY.md:36`      The updated trust-model text says explicit `--coder=cursor` runs Cursor but then documents the command/posture as ``codex exec --full-auto`, `approval: never`, `sandbox: workspace-write``. Concrete breakage path: an operator using `SECURITY.md` to choose an implementer can read that Cursor has Codex’s workspace-write sandbox posture, even though the same paragraph later says Cursor runs with `--trust` and broader filesystem access. Replace that parenthetical with the actual Cursor launcher posture, and describe the Codex fallback separately.
- **Suggested revision**: Address the concern above.


### FINDING_7: code-quality: scripts/compose-review-findings.sh:74-81
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] extract_reviewer_from_body only matches singular bold - **Reviewer**: while lib-vote-tally reviewer_for_block accepts Reviewers and plain Reviewer:/Reviewers: in the same PR. Finding bodies using - **Reviewers:** or plain Reviewer: lines get reviewer=panel in review-findings-full.jsonl even though tally-side extraction recognizes them, splitting attribution across subsystems. Align awk patterns with reviewer_for_block, add a compose harness case for plural/plain lines, or call a single shared extractor (e.g. reviewer_for_block via process substitution).
- **Suggested revision**: Address the concern above.


