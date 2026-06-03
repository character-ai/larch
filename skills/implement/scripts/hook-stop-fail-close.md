# skills/implement/scripts/hook-stop-fail-close.sh — contract

`hook-stop-fail-close.sh` is the plugin-shipped `Stop` hook that guards post-skill halt boundaries inside an active `/implement` run (post-/review; the retired post-/design manifest gate is no longer enforced here — issue #2487).

**Post-/review boundary** (issue #1862): blocks session stop when `review-round-summary.md` exists (review ran) but neither `.review-boundary-passed` nor `.run-cleaned-up` exists. `.review-boundary-passed` is written by the orchestrator at the start of Step 6 after all three required post-/review actions complete (Cross-Skill Presence Propagation + Track Rejected Code Review Findings + Step 6 breadcrumb). Recovery: execute those three actions in order, then `touch "$IMPLEMENT_TMPDIR/.review-boundary-passed"`.

**Post-/release boundary — retired Phase 1 (#3364):** `/implement` no longer arms a release sentinel or runs a release precheck gate on the ship path; version bumps are operator- or `/release`-initiated via `.claude/skills/release/SKILL.md`. This hook no longer enforces a post-/release stop gate.

All checks share the `.run-cleaned-up` sentinel as the terminal escape: once teardown writes it the hook allows all stops through. The `stop_hook_active` guard prevents a continuation-loop trap. The block envelope shape (top-level `{"decision":"block","reason":"..."}`) was verified against the Claude Code hooks reference. If `jq` is missing, the hook emits a static literal block envelope.

Edit in sync with `lib-resolve-implement-tmpdir.sh`, `hooks/hooks.json`, `skills/implement/SKILL.md` Steps 6 and 8, and `scripts/test-implement-anti-halt.sh`.
