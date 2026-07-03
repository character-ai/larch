### [rejected] FINDING_1

**Rejected subtype:** dismissed (0 YES)

### FINDING_1: Operator export warning is missing from the docs
- **Reviewer(s)**: dyn-dyn-hook-boundary
- **Severity**: important
- **Concern**: The exemption is keyed only on the hook environment, so accidental parent-shell export can give the orchestrator the same full bypass as a child. The docs should warn operators not to export it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-hook-boundary: "Document in `SECURITY.md` and `scripts/hook-bg-poll-guard.md` that operators must not export `LARCH_CLAUDE_SUBPROCESS_HOOK_EXEMPT` in the orchestrator environment; treat accidental export like `LARCH_BG_POLL_GUARD_DISABLE=1`. Optionally add a harness case that exports a junk value such as `true` or `yes` and asserts deny, to pin the exact-`1` contract beyond the existing `=0` case."


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

