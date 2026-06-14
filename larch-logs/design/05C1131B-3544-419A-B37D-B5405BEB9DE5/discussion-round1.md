## Decision 1: collect-agent-results.sh retry retargeting
- **Question**: Should collect-agent-results.sh's retry OUTER_LAUNCHER check be updated in this piece?
- **Resolution**: Yes — retarget collect-agent-results.sh in this piece so retries work immediately after launch-review.sh is retired.
- **Source**: user

## Decision 2: Prompt sidecar sentinel format
- **Question**: Should the Python port preserve the LARCH_PROMPT_SENTINEL=1 compact hash+render-args format for --agent-file launches?
- **Resolution**: Yes — preserve exactly. collect-agent-results.sh retries via `cli.py render specialist` replay depend on this format.
- **Source**: user

## Decision 3: Dirty-tree baseline
- **Question**: Should the Python launcher call snapshot-untracked.sh or `python3 cli.py dirty-tree checkpoint`?
- **Resolution**: Use `python3 cli.py dirty-tree checkpoint` — pure Python path, no bash dependency in the new launcher.
- **Source**: user
