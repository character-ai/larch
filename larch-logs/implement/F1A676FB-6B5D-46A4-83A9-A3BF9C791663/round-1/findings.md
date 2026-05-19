### FINDING_1: **Nit** `risk-integration` `docs/linting.md:239` — The linting docs still say `make test-implement-step2-routing` pins the omitted-`--coder` `Codex → Cursor → Claude` waterfall, but this branch changes that contract to `Cursor → Codex → Claude`. Update the row to match `scripts/test-implement-step2-routing.md:5-7` and `skills/implement/SKILL.md:1072-1082`.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Nit** `risk-integration` `docs/linting.md:239` — The linting docs still say `make test-implement-step2-routing` pins the omitted-`--coder` `Codex → Cursor → Claude` waterfall, but this branch changes that contract to `Cursor → Codex → Claude`. Update the row to match `scripts/test-implement-step2-routing.md:5-7` and `skills/implement/SKILL.md:1072-1082`.
- **Suggested revision**: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] code-quality: skills/implement/SKILL.md:1223
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Duplicate wording unavailable or unavailable in a Step 2 print bullet. Confusing operator messaging; not introduced by this branch. Fix wording in a separate edit.
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] code-quality: skills/implement/SKILL.md:1223
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicate "unavailable" phrasing in Step 2 print bullet. File not changed by this branch diff; cosmetic only. Optional prose fix in a separate edit.
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] code-quality: skills/implement/SKILL.md:1223
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Duplicated unavailable wording in Step 2.4 bullet. Minor readability only; pre-existing adjacent to touched section. Optional prose cleanup in a follow-up edit.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] code-quality: skills/implement/SKILL.md:~135
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Duplicate unavailable wording in Cursor fallback status bullet Unchanged by this branch; cosmetic only only Fix wording in a separate edit if desired
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] risk-integration: SECURITY.md:46
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Omitted --coder routing prose still documents Codex first then Cursor. Operators and auditors relying on SECURITY.md misunderstand when Cursor may implement without an explicit flag after merge. Rewrite the sentence to Cursor to Codex to Claude and align coder_fallback wording with SKILL.md.
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] risk-integration: SECURITY.md:46-47
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Still documents Codex to Cursor waterfall for omitted --coder. Operators relying on SECURITY.md for routing trust model get stale order and fallback narrative. Update SECURITY.md when merging or in a immediate follow-up PR.
- **Suggested revision**: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] risk-integration: docs/linting.md:238
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Lint matrix row still names Codex to Cursor to Claude for test-implement-step2-routing. Contributors read stale harness description vs actual pins. Update the table cell to Cursor to Codex to Claude to match scripts/test-implement-step2-routing.md.
- **Suggested revision**: Address the concern above.

### FINDING_9: code-quality: docs/linting.md:239
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] `make test-implement-step2-routing` row still names `Codex → Cursor → Claude` waterfall. Linting matrix contradicts updated SKILL and routing harness after merge. Update cell text to `Cursor → Codex → Claude`.
- **Suggested revision**: Address the concern above.

### FINDING_10: code-quality: docs/run-logs.md:71
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] `coder_fallback=true` described as when routing "fell past Codex." Wording implies Codex-first waterfall in run-log contract prose. Use vendor-neutral wording aligned with both-external-down / Claude fallback semantics.
- **Suggested revision**: Address the concern above.

### FINDING_11: code-quality: skills/implement/scripts/test-step2-dispatch.sh:99-104
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Test 1b only matches STATUS=claude_fallback. A regression that dropped ORCHESTRATOR_EDIT_AUTHORITY=allowed while still printing the status token could slip past this assertion. Assert ORCHESTRATOR_EDIT_AUTHORITY=allowed like neighboring tests.
- **Suggested revision**: Address the concern above.

### FINDING_12: code-quality: skills/implement/scripts/test-step2-dispatch.sh:99-105
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Test 1b drops stderr and omits `ORCHESTRATOR_EDIT_AUTHORITY` assertion vs sibling tests. Weaker NEVER #10 pair pin and harder failure diagnosis. Assert `ORCHESTRATOR_EDIT_AUTHORITY=allowed` and avoid silencing stderr unless asserting it empty on success.
- **Suggested revision**: Address the concern above.

### FINDING_13: correctness: docs/linting.md:239
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] make test-implement-step2-routing matrix row still names Codex to Cursor to Claude waterfall for omitted --coder Documentation contradicts updated harness and SKILL; readers get wrong mental model of default routing Update the table cell to Cursor to Codex to Claude to match scripts/test-implement-step2-routing.md and SKILL
- **Suggested revision**: Address the concern above.

### FINDING_14: correctness: docs/run-logs.md:71
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] manifest.json blurb still says coder_fallback=true when routing fell past Codex Ambiguous or misleading description of the flag after cursor-first waterfall Rephrase to match SKILL (e.g. both external implementers unavailable) or quote the exact manifest contract from scripts/larch-log.md
- **Suggested revision**: Address the concern above.

### FINDING_15: correctness: skills/implement/scripts/test-step2-dispatch.sh:99-105
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Test 1b only matches `STATUS=claude_fallback`; same outcome if default coder were accidentally `claude`. CI passes after reverting default to `claude` while product intent requires default `cursor`. Add a disambiguating assertion (positive cursor path) or document scope and add a dedicated default test.
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: SECURITY.md:46
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Omitted-coder routing paragraph still documents Codex-first waterfall and ties coder_fallback=true to Cursor-without-explicit-flag when Codex is unavailable Operators and reviewers relying on SECURITY.md mis-predict default external implementer order and when the manifest records coder_fallback=true, diverging from authoritative skills/implement/SKILL.md after this branch Rewrite the paragraph to match SKILL: Cursor then Codex then Claude; clarify coder_fallback=true only on both-external-down Claude path (or equivalent accurate wording)
- **Suggested revision**: Address the concern above.

### FINDING_17: risk-integration: SECURITY.md:46
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Omitted-`--coder` paragraph still documents Codex-first waterfall, implicit-Cursor-via-Codex-absence, and bundles `coder_fallback=true` into that narrative. Operators misread default implementer order, when Cursor runs without `--coder=cursor`, and when manifests record `coder_fallback=true`. Rewrite to match SKILL: `Cursor → Codex → Claude`, correct implicit-selection cases, and state `coder_fallback=true` only for both-externals-down (Claude) routing.
- **Suggested revision**: Address the concern above.

### FINDING_18: risk-integration: skills/implement/scripts/step2-implement.sh:123-199
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Omitted --coder now defaults to cursor; cursor-present gate runs before git-tree checks. Invocation with no --coder and no --cursor-present from a non-git cwd used to fail closed (exit 2) on the codex default; it now exits 0 with STATUS=claude_fallback and ORCHESTRATOR_EDIT_AUTHORITY=allowed, authorizing main-agent edits where automation previously aborted. Pass explicit --coder when git context matters; document behavior; consider orchestrator fail-closed if needed.
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: skills/implement/scripts/test-step2-dispatch.sh:91-105
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Test 1b only checks claude_fallback stdout for omitted --coder in a non-git cwd; same envelope as default claude. Reverting default CODER to claude in step2-implement.sh:124-126 would still pass Test 1b while violating the intended primary implementer contract. Add a harness case that distinguishes omitted --coder cursor path from explicit --coder claude (e.g. minimal git repo plus --cursor-present true and stub launcher expectations or assert external-tool path markers).
- **Suggested revision**: Address the concern above.

