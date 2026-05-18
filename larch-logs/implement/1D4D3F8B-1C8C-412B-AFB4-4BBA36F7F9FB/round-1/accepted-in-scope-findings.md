### FINDING_11: code-quality: scripts/launch-claude-review.md:180-183
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Doc can be read as voter never receiving diff context; only subprocess context-files are skipped. Misleading for readers who use --agent-file. Clarify subprocess context-files only; note --agent-file render path until code gates it.
- **Suggested revision**: Address the concern above.


### FINDING_12: correctness: scripts/launch-claude-review.sh:73-83
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] --agent-file render_args ignore ROLE so diff/plan can still be embedded via render-specialist-prompt while voter role skips only subprocess context-files. launch-claude-review.sh --agent-file agents/code-reviewer.md --mode diff --role voter --diff-file huge.patch still feeds huge.patch into render-specialist-prompt.sh which inlines diff instructions in the rendered prompt reintroducing large prompt and cap risk. Gate render_args on ROLE eq reviewer or reject --agent-file with --role voter.
- **Suggested revision**: Address the concern above.


### FINDING_14: risk-integration: scripts/launch-claude-review.sh:73-83
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] --role voter does not gate context flags passed to render-specialist-prompt.sh on the --agent-file path. A future or alternate voter launch that uses --agent-file with --role voter could still feed diff/plan/scope into render-specialist-prompt.sh while only --context-files forwarding is suppressed, diverging from the ballot-only voter contract and leaving the path untested. Gate render_args the same way as append_context_file for ROLE=voter, or explicitly document that agent-file voters are not supported and must use prompt-file.
- **Suggested revision**: Address the concern above.


### FINDING_9: architecture: scripts/launch-claude-review.sh:73-81
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] --role voter does not gate render_args for --agent-file; diff/plan/scope still passed to render-specialist-prompt.sh. A caller combining --agent-file, --role voter, and --diff-file still embeds the branch diff in the rendered prompt (render-specialist-prompt.sh), so large-diff / cap risk remains despite voter skipping --context-files. Gate render_args additions on ROLE=reviewer or document that voter is only valid with --prompt-file/--prompt.
- **Suggested revision**: Address the concern above.


