### FINDING_13: panel [code-review/accepted]

## correctness: scripts/larch-log-batches.md:50-51

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Doc claims each append writes one record; implementation appends all lines from the record file. Two-line valid NDJSON file appends two records in one call without contradiction in code. Rewrite to match append semantics or enforce single-line at validation.
- **Suggested revision**: Address the concern above.

### FINDING_21: panel [code-review/accepted]

## security: scripts/larch-log-batches.md:68-69

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Doc recommends --arg body but omits explicit safe shell quoting for the value word. Orchestrator uses --arg body $BODY unquoted; markdown with spaces or metacharacters splits/expands in the shell before jq, corrupting argv or enabling unintended expansions. Document --arg body "$BODY" or --rawfile/--argfile from a file; warn against unquoted expansion.
- **Suggested revision**: Address the concern above.

