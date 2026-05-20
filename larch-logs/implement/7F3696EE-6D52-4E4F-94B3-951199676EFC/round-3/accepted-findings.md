### FINDING_16: correctness: scripts/ship-pr.sh:1327-1334
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] plugin.json auto-resolve guard uses pattern '*/.claude-plugin/plugin.json' only, which misses the usual repo-relative path '.claude-plugin/plugin.json' from git's conflict listing. Rebase conflicts that only touch the real plugin manifest skip the intended 'git checkout --ours' fast path and still route through the vendor resolver (or mark the file unresolved), so the plan's deterministic handling for that file often never runs. Also match '.claude-plugin/plugin.json' at repo root (or use a prefix-agnostic test) and add a regression case in test-ship-pr.sh that conflicts only on that path.
- **Suggested revision**: Address the concern above.


