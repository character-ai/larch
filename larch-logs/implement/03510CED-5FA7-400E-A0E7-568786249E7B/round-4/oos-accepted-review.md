### OOS_12: [OUT_OF_SCOPE] _resolve_conflicts lacks forbidden-path/submodule guard after fixer tier
- **Reviewer(s)**: dyn-conflict-loop-output.txt
- **Severity**: nit
- **Concern**: Pre-existing: `_resolve_conflicts` has no forbidden-path / submodule guard after a fixer tier, unlike the new CI agentic loop. Write-capable Codex/Cursor conflict tiers already had this exposure; Claude write-capability widens it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-conflict-loop-output.txt: Pre-existing: `_resolve_conflicts` has no forbidden-path / submodule guard after a fixer tier, unlike the new CI agentic loop. Write-capable Codex/Cursor conflict tiers already had this exposure; Claude write-capability widens it.


