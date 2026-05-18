### FINDING_1: [OUT_OF_SCOPE] architecture: scripts/launch-claude-subprocess.md
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Companion doc may still describe voters receiving forwarded diff context via dispatch-code-voters. Misleading operator mental model after voter context drop. File not in branch diff; align in a follow-up.
- **Suggested revision**: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] code-quality: docs/linting.md
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Makefile/linting doc table omits new --role harness coverage. Pre-existing vs updated harness contract in scripts/test-launch-claude-review.md. Update docs/linting.md in a follow-up if you want the table to match the harness.
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] risk-integration: docs/linting.md:202
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] linting doc row for test-launch-claude-review omits new --role scenarios. Readers underestimate local harness coverage. File not in branch diff; update docs/linting.md in a follow-up.
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] risk-integration: scripts/dispatch-with-waterfall.sh:167-169
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Waterfall Claude fallback never passes --role voter; not changed in this diff. Hypothetical non-dispatch-code-voters caller passing diff plus voter prompts could still bundle diff on Phase 3. Consider forwarding role in a follow-up if that caller appears; not required for this diff s mitigated caller.
- **Suggested revision**: Address the concern above.

### FINDING_5: architecture: implementation plan vs scripts/test-launch-claude-review.sh
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Plan referenced test-launch-review.sh but harness is test-launch-claude-review.sh. Future implementers may look for a non-existent harness name. Align plan template or add explicit harness name.
- **Suggested revision**: Address the concern above.

### FINDING_6: architecture: implementation_plan:Files to modify
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] New harness contract doc scripts/test-launch-claude-review.md not listed in the plan file set Minor plan vs diff surface mismatch only; no runtime gap. Add the path to the plan file list if parity is required.
- **Suggested revision**: Address the concern above.

### FINDING_7: architecture: implementation_plan:Testing bullet vs scripts/test-launch-review.sh
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Plan verification names test-launch-review.sh but --role is on launch-claude-review.sh A strict plan-to-file audit could mark the requirement unmet because test-launch-review.sh was not edited, even though make test-launch-claude-review is the correct gate. Rename the plan bullet to scripts/test-launch-claude-review.sh or note the Makefile target explicitly.
- **Suggested revision**: Address the concern above.

### FINDING_8: architecture: scripts/launch-claude-review.md:13
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Doc says reviewer sees full diff inline but prompt-file path uses context-files attachment. Misleading operational mental model for debugging context size. Rephrase to describe context-files attachment.
- **Suggested revision**: Address the concern above.

### FINDING_9: architecture: scripts/launch-claude-review.sh:73-81
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] --role voter does not gate render_args for --agent-file; diff/plan/scope still passed to render-specialist-prompt.sh. A caller combining --agent-file, --role voter, and --diff-file still embeds the branch diff in the rendered prompt (render-specialist-prompt.sh), so large-diff / cap risk remains despite voter skipping --context-files. Gate render_args additions on ROLE=reviewer or document that voter is only valid with --prompt-file/--prompt.
- **Suggested revision**: Address the concern above.

### FINDING_10: code-quality: scripts/dispatch-code-voters.sh:131-147
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] mode is always description after removing diff branch; variable is redundant. No functional bug; slight unnecessary state. Use --mode description literally or drop the variable.
- **Suggested revision**: Address the concern above.

### FINDING_11: code-quality: scripts/launch-claude-review.md:180-183
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Doc can be read as voter never receiving diff context; only subprocess context-files are skipped. Misleading for readers who use --agent-file. Clarify subprocess context-files only; note --agent-file render path until code gates it.
- **Suggested revision**: Address the concern above.

### FINDING_12: correctness: scripts/launch-claude-review.sh:73-83
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] --agent-file render_args ignore ROLE so diff/plan can still be embedded via render-specialist-prompt while voter role skips only subprocess context-files. launch-claude-review.sh --agent-file agents/code-reviewer.md --mode diff --role voter --diff-file huge.patch still feeds huge.patch into render-specialist-prompt.sh which inlines diff instructions in the rendered prompt reintroducing large prompt and cap risk. Gate render_args on ROLE eq reviewer or reject --agent-file with --role voter.
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: implementation_plan vs scripts/test-launch-review.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Plan asked to verify test-launch-review.sh for --role; diff only extends test-launch-claude-review.sh. Maintainers may search test-launch-review.sh for coverage and wrongly conclude --role is untested. Update the plan or add a one-line comment in test-launch-review.sh pointing to test-launch-claude-review.sh if cross-stack visibility matters.
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: scripts/launch-claude-review.sh:73-83
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] --role voter does not gate context flags passed to render-specialist-prompt.sh on the --agent-file path. A future or alternate voter launch that uses --agent-file with --role voter could still feed diff/plan/scope into render-specialist-prompt.sh while only --context-files forwarding is suppressed, diverging from the ballot-only voter contract and leaving the path untested. Gate render_args the same way as append_context_file for ROLE=voter, or explicitly document that agent-file voters are not supported and must use prompt-file.
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: scripts/test-launch-claude-review.sh:84-102
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] No harness for --agent-file combined with --role voter. If render_args is later gated incorrectly, regression may slip without a red test. Add a stubbed --agent-file + --role voter case once behavior is finalized.
- **Suggested revision**: Address the concern above.

