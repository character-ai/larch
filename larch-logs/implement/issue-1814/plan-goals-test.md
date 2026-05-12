## Goal
Strengthen post-/design and post-/review anti-halt directives in `skills/implement/SKILL.md` to explicitly say "do NOT end the turn (neither silently nor after text output)" — mirroring the fix from 9d639da that patched the same gap at Step 8.

## Implementation Plan

Files to modify:
- `skills/implement/SKILL.md`: lines 818 and 1282 — add "do NOT end the turn (neither silently nor after text output), and" before "do NOT write a summary"
- `scripts/test-implement-anti-halt.sh`: two new `check_contains` assertions pinning the new phrases

Approach: surgical phrase insertion at both boundaries; no structural changes.

## Test plan
Run `bash scripts/test-implement-anti-halt.sh` and `/relevant-checks` (pre-commit + agent-lint).
