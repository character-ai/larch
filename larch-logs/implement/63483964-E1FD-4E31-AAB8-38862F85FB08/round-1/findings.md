### FINDING_1: `31956cc9` — Pin YES↔EXONERATE anchor phrase across voter prose and structural harness  
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: - `31956cc9` — Pin YES↔EXONERATE anchor phrase across voter prose and structural harness
- **Suggested revision**: Address the concern above.

### FINDING_2: `9f0915f0` — `chore(larch-logs): flush implement run 63483964-E1FD-4E31-AAB8-38862F85FB08`
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: - `9f0915f0` — `chore(larch-logs): flush implement run 63483964-E1FD-4E31-AAB8-38862F85FB08` **Diff summary (from precomputed diff):** Adds `FINDING_2678` in [`scripts/test-design-structure.sh`](scripts/test-design-structure.sh), updates the contract line in [`scripts/test-design-structure.md`](scripts/test-design-structure.md), appends the canonical sentence inside the two backtick-wrapped instruct strings in [`skills/design/references/plan-review.md`](skills/design/references/plan-review.md), adds a matching `printf` in [`skills/shared/scripts/render-voter-prompt.sh`](skills/shared/scripts/render-voter-prompt.sh), and adds the usual [`larch-logs/implement/...`](larch-logs/implement/63483964-E1FD-4E31-AAB8-38862F85FB08) run artifacts. That matches the attached implementation plan (renderer instead of editing `dispatch-plan-voters.sh` directly; `plan-review-quick.md` unchanged). ---
- **Suggested revision**: Address the concern above.

### FINDING_3: risk-integration: scripts/test-design-structure.sh:580-606
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] FINDING_2678 asserts phrase only in source files, not in rendered prompt files from make_prompt_file. Refactor stops calling render-voter-prompt.sh while leaving renderer source phrase in place; external voters lose anchor but structural test still passes. Add rendered-output grep in test-dispatch-plan-voters healthy block or assert dispatch still invokes renderer and emitted prompt contains the phrase.
- **Suggested revision**: Address the concern above.

### FINDING_4: correctness: scripts/test-design-structure.sh:581
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] CANONICAL_PHRASE uses substring without trailing period while prose uses a full sentence with punctuation. Minor drift in terminal punctuation could remain compatible with substring checks and slip past strict verbatim intent. Use one canonical string including punctuation or document substring-only contract in the check comment.
- **Suggested revision**: Address the concern above.

### FINDING_5: risk-integration: scripts/test-design-structure.sh:600-602
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] FINDING_2678 only greps render-voter-prompt.sh source, not rendered voter prompt files from dispatch-plan-voters.sh. A future change could stop emitting the new printf line in real prompt files while the literal still satisfies the source-level grep, weakening the pin the issue described for on-disk prompts. Add grep -Fq of the canonical phrase against healthy-mode codex/cursor prompt outputs in scripts/test-dispatch-plan-voters.sh (or run render-voter-prompt.sh in the harness and assert stdout).
- **Suggested revision**: Address the concern above.

### FINDING_6: risk-integration: scripts/test-design-structure.sh:580-608
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Plan acceptance text claims FINDING_2678 is listed in harness run output, but the script only prints the aggregate PASS line. Reviewers scanning CI logs cannot see which sub-check ran without reading the script or failing a sub-assertion. Adjust acceptance prose or emit an explicit line naming FINDING_2678 when that traceability is required.
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] code-quality: skills/design/references/plan-review-quick.md:21
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Quick-mode line punctuates after EXONERATE with an em dash, not the period used elsewhere; substring test still passes. Not introduced by this diff; only relevant if the project later wants byte-identical phrasing across all four surfaces. Leave as-is unless prose normalization is desired in a follow-up.
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: scripts/test-design-structure.sh:199-227
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Plan acceptance asked for FINDING_2678 to be listed in successful run stdout; implementation only comments and fail() strings reference that id. Anyone validating the PR against the written acceptance line by reading only successful CI logs or terminal capture will not see FINDING_2678 named, though the check did run. Add an explicit success echo for FINDING_2678 after the block, or revise the plan acceptance wording to match the file's existing silent-on-success pattern.
- **Suggested revision**: Address the concern above.

