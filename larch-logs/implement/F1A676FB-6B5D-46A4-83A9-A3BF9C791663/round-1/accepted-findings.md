### FINDING_1: **Nit** `risk-integration` `docs/linting.md:239` — The linting docs still say `make test-implement-step2-routing` pins the omitted-`--coder` `Codex → Cursor → Claude` waterfall, but this branch changes that contract to `Cursor → Codex → Claude`. Update the row to match `scripts/test-implement-step2-routing.md:5-7` and `skills/implement/SKILL.md:1072-1082`.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Nit** `risk-integration` `docs/linting.md:239` — The linting docs still say `make test-implement-step2-routing` pins the omitted-`--coder` `Codex → Cursor → Claude` waterfall, but this branch changes that contract to `Cursor → Codex → Claude`. Update the row to match `scripts/test-implement-step2-routing.md:5-7` and `skills/implement/SKILL.md:1072-1082`.
- **Suggested revision**: Address the concern above.


### FINDING_11: code-quality: skills/implement/scripts/test-step2-dispatch.sh:99-104
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Test 1b only matches STATUS=claude_fallback. A regression that dropped ORCHESTRATOR_EDIT_AUTHORITY=allowed while still printing the status token could slip past this assertion. Assert ORCHESTRATOR_EDIT_AUTHORITY=allowed like neighboring tests.
- **Suggested revision**: Address the concern above.


### FINDING_12: code-quality: skills/implement/scripts/test-step2-dispatch.sh:99-105
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Test 1b drops stderr and omits `ORCHESTRATOR_EDIT_AUTHORITY` assertion vs sibling tests. Weaker NEVER #10 pair pin and harder failure diagnosis. Assert `ORCHESTRATOR_EDIT_AUTHORITY=allowed` and avoid silencing stderr unless asserting it empty on success.
- **Suggested revision**: Address the concern above.


### FINDING_15: correctness: skills/implement/scripts/test-step2-dispatch.sh:99-105
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Test 1b only matches `STATUS=claude_fallback`; same outcome if default coder were accidentally `claude`. CI passes after reverting default to `claude` while product intent requires default `cursor`. Add a disambiguating assertion (positive cursor path) or document scope and add a dedicated default test.
- **Suggested revision**: Address the concern above.


### FINDING_19: risk-integration: skills/implement/scripts/test-step2-dispatch.sh:91-105
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Test 1b only checks claude_fallback stdout for omitted --coder in a non-git cwd; same envelope as default claude. Reverting default CODER to claude in step2-implement.sh:124-126 would still pass Test 1b while violating the intended primary implementer contract. Add a harness case that distinguishes omitted --coder cursor path from explicit --coder claude (e.g. minimal git repo plus --cursor-present true and stub launcher expectations or assert external-tool path markers).
- **Suggested revision**: Address the concern above.


