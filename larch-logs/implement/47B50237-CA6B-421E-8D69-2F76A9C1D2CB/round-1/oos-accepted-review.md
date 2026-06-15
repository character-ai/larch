### OOS_1: [OUT_OF_SCOPE] correctness: python/agents.py:3908
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Cursor review workspace still uses Path.cwd() Plugin-root CWD yields wrong --workspace for Cursor review slots Apply a parallel resolver for Cursor or pass explicit workspace from caller
- **Suggested revision**: Address the concern above.


### OOS_2: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - **correctness** `python/agents.py:4268-4269` — `launch-codex-implement` still passes `Path.cwd()` to `codex exec -C`, not `_resolve_review_codex_workdir`. **Why out of scope:** pre-existing; plan non-goal to leave implement launch paths unchanged.
- **Suggested revision**: Address the concern above.


