### FINDING_1: **Important** correctness — `scripts/compose-review-findings.sh:180`  
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** correctness — `scripts/compose-review-findings.sh:180`      `code-review-oos` only recognizes headings shaped as `### OOS_N: ...`, but production `oos.md` entries are written as `### FINDING_N: [OUT_OF_SCOPE] ...` by `skills/review/scripts/collect-findings.sh:392-399` and then preserved by `skills/review/scripts/tally-code-votes.sh:354-355`. Concrete failing scenario: a round with OOS findings produces `round-1/oos.md`, but `compose-review-findings.sh` emits zero `outcome="out_of_scope"` records, so Gap 3 remains unfixed for real runs. Update the parser and regression fixture to cover the actual `FINDING_N: [OUT_OF_SCOPE]` shape, while still mapping emitted JSONL ids to `OOS_C...` if that is the desired schema.
- **Suggested revision**: Address the concern above.

### FINDING_2: **Important** security — `SECURITY.md:36`  
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Important** security — `SECURITY.md:36`      The updated trust-model text says explicit `--coder=cursor` runs Cursor but then documents the command/posture as ``codex exec --full-auto`, `approval: never`, `sandbox: workspace-write``. Concrete breakage path: an operator using `SECURITY.md` to choose an implementer can read that Cursor has Codex’s workspace-write sandbox posture, even though the same paragraph later says Cursor runs with `--trust` and broader filesystem access. Replace that parenthetical with the actual Cursor launcher posture, and describe the Codex fallback separately.
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] architecture: branch diff vs feature_description
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Large unrelated changes bundled with compose schema fix Unrelated Step 2 / waterfall / log flush increases blast radius and confounds bisect if compose regressions appear. Split PRs or isolate chore/version/docs from functional compose changes.
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] code-quality: CHANGELOG.md / larch-logs/** (branch)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Large non-functional log and changelog volume alongside the feature. Human review cost only. No change required per repo policy on larch-logs; optional PR split for readability.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] correctness: scripts/compose-review-findings.sh:190-196
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Pre-existing inner-### weakness on accepted findings paths Accepted findings with inner ### still lose body content; unchanged by this feature branch. Future parity fix if accepted templates gain subheadings.
- **Suggested revision**: Address the concern above.

### FINDING_6: architecture: scripts/compose-review-findings.sh:169-171
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Exact string match on Code Review for header reviewer Irregular spacing in [Code Review] headers skips header reviewer; usually masked by body extraction but brittle. Normalize captured header text before comparison or use a structured parse.
- **Suggested revision**: Address the concern above.

### FINDING_7: code-quality: scripts/compose-review-findings.sh:74-81
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] extract_reviewer_from_body only matches singular bold - **Reviewer**: while lib-vote-tally reviewer_for_block accepts Reviewers and plain Reviewer:/Reviewers: in the same PR. Finding bodies using - **Reviewers:** or plain Reviewer: lines get reviewer=panel in review-findings-full.jsonl even though tally-side extraction recognizes them, splitting attribution across subsystems. Align awk patterns with reviewer_for_block, add a compose harness case for plural/plain lines, or call a single shared extractor (e.g. reviewer_for_block via process substitution).
- **Suggested revision**: Address the concern above.

### FINDING_8: code-quality: scripts/test-implement-step2-routing.sh (branch diff)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Unrelated waterfall-order assertion updates bundled with compose-review-findings schema work. Reviewers must read routing doc/test churn unrelated to JSONL schema gaps. Split PR/commits or isolate routing doc sync from the findings composer change unless required to fix CI on main.
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: scripts/compose-review-findings.sh:165-171
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Code Review header reviewer gated on exact string match Header uses extra spaces inside Code Review; header slot ignored until body or panel Normalize match or key off rejected vs non-rejected branch only
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: scripts/compose-review-findings.sh:180-196
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] code-review-oos lacks inner-### handling; shared flush drops trailing body An oos.md finding with a mid-body ### subsection (e.g. ### Notes) truncates the emitted prose_body and drops following lines until the next OOS header, corrupting miner JSONL silently. Mirror code-review-rejected inner-heading logic for code-review-oos when pending_id is set.
- **Suggested revision**: Address the concern above.

### FINDING_11: correctness: scripts/compose-review-findings.sh:74-81
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] extract_reviewer_from_body only handles singular bold Reviewer at column 1 Finding body uses only - **Reviewers**: ... or plain Reviewer: lines; JSONL reviewer becomes panel while lib-vote-tally extracts real labels in the same PR Align patterns with reviewer_for_block or share extraction helper
- **Suggested revision**: Address the concern above.

### FINDING_12: correctness: scripts/compose-review-findings.sh:74-81
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Reviewer line must start at column 1 with hyphen Indented - **Reviewer**: line in body; false panel fallback Allow leading whitespace in matcher like lib-vote-tally anchoring
- **Suggested revision**: Address the concern above.

### FINDING_13: correctness: scripts/compose-review-findings.sh:74-81
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Reviewer bullet must start at column 1 Indented/wrapped reviewer bullets are ignored; reviewer falls back to panel despite visible attribution. Allow leading whitespace before the bullet in the awk pattern.
- **Suggested revision**: Address the concern above.

### FINDING_14: correctness: scripts/compose-review-findings.sh:74-81
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] extract_reviewer_from_body only matches singular bold - **Reviewer**: lines, unlike reviewer_for_block which also accepts Reviewers and plain Reviewer:. JSONL reviewer falls back to panel for bodies that only use plural or unbolded attribution, diverging from tally extraction. Align extraction with reviewer_for_block patterns or share one helper.
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: branch diff vs implementation_plan three-file list
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Unrelated behavioral and doc changes bundled with compose JSONL schema fix Operators expect a scoped schema PR but also ship default coder waterfall lib-vote-tally version bumps and run logs; harder bisect and review Split PRs or expand plan to cover all intentional changes
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: scripts/compose-review-findings.sh:104
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] New round_num field on every JSONL record Strict downstream consumers of review-findings-full.jsonl may fail closed on unknown keys or missing migration. Document release impact or add an explicit schema_version field if external contracts exist.
- **Suggested revision**: Address the concern above.

### FINDING_17: risk-integration: scripts/compose-review-findings.sh:164-172
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] [rejected] headers no longer contribute a reviewer when body lacks - **Reviewer**:. Downstream that depended on the old mistaken header capture now sees panel. Document the semantics in consumer docs or add a transitional warning if any known caller relied on header-only tokens.
- **Suggested revision**: Address the concern above.

### FINDING_18: risk-integration: scripts/compose-review-findings.sh:74-81
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] extract_reviewer_from_body only matches singular bold - **Reviewer**: at column 1 Body uses - **Reviewers**: or plain Reviewer: (allowed elsewhere in lib-vote-tally); reviewer becomes panel while tally attributes a real slot — inconsistent cross-pipeline semantics. Align extraction with reviewer_for_block rules or document and enforce a single canonical line shape upstream.
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: scripts/compose-review-findings.sh:74-81
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] extract_reviewer_from_body only handles singular - **Reviewer**: Bodies using - **Reviewers**: or plain Reviewer: (now supported by reviewer_for_block) still yield reviewer="panel" in JSONL. Reuse the same anchored patterns as reviewer_for_block or add compose tests for plural/plain lines.
- **Suggested revision**: Address the concern above.

### FINDING_20: risk-integration: scripts/test-compose-review-findings.sh:174-197
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] OOS test asserts reviewer on one of three records only Weak coverage for per-row reviewer wiring once headings are fixed. Assert reviewer (or at least non-empty distinct values) for OOS_C1 and OOS_C3 as well, or jq-walk all OOS rows.
- **Suggested revision**: Address the concern above.

### FINDING_21: risk-integration: skills/implement/SKILL.md;skills/implement/scripts/step2-implement.sh;SECURITY.md
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Omitted --coder default waterfall now prefers Cursor over Codex when both are available. A deployment that assumed Codex-first external implementation without passing --coder=codex now routes implementation to Cursor, shifting trust/permissions assumptions. Document the posture change; require explicit --coder where policy must pin an implementer; align internal runbooks and consumer guidance.
- **Suggested revision**: Address the concern above.

