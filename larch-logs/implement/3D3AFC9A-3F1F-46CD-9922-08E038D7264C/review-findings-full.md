### FINDING_17: panel [code-review/accepted]

## code-quality: scripts/test-harness-shards-coverage.sh:136-143

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Guard-shard tempfile is still populated but never read after the last-shard to guard-shard refactor. Extra disk I/O per run and confusing dual representation (globals vs unused guard-shard file) for future edits; no direct security impact. Remove out_guard_shard writes and the unused third argument, or consume the file in validate_makefile instead of parallel globals.
- **Suggested revision**: Address the concern above.

