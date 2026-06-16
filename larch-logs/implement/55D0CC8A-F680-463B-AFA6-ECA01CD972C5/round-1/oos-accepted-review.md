### OOS_1: [OUT_OF_SCOPE] Stop hook does not unset stale `LARCH_TOKEN_SESSION_ID` when `session_id` is absent
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `skills/implement/scripts/hook-stop-fail-close.sh:55` exports `LARCH_TOKEN_SESSION_ID` when `session_id` is present but never unsets it when absent, unlike SessionStart. A stale operator-exported `LARCH_TOKEN_SESSION_ID` can bind the resolver on Stop events that omit `session_id`, skipping TTL fallback and causing fail-open when post-/review blocking should apply.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Mirror SessionStart: unset `LARCH_TOKEN_SESSION_ID` when SID is empty before calling the resolver.
  - From cursor-specialist-edge-cases-output.txt: Mirror SessionStart: `unset LARCH_TOKEN_SESSION_ID || true` when `SID` is empty, before spawning Python.


