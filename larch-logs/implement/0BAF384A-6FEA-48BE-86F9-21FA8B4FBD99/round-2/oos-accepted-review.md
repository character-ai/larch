### OOS_1: [OUT_OF_SCOPE] GraphQL error output may leak raw gh stdout
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `ERROR=` lines in `python/issue_block.py` include raw `gh` stdout without `redact_outbound`, which may expose auth or token-bearing errors.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### OOS_2: [OUT_OF_SCOPE] Cached-version pruning lacks cache-root validation
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `prune_cached_versions` uses `plugin_root.parent` without validating the cache-root shape, so a mis-set `CLAUDE_PLUGIN_ROOT` may delete version-shaped sibling directories.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


