# skills/implement/scripts/hook-stop-fail-close.sh — contract

`hook-stop-fail-close.sh` is the plugin-shipped `Stop` hook that guards two post-skill halt boundaries inside an active `/implement` run.

**Post-/design boundary** (issue #1814): blocks session stop when the resolved `/implement` tmpdir has `design-export/manifest.env` (design ran) but neither `.boundary-gate-passed` nor `.run-cleaned-up` exists. Recovery: run `post-design-boundary.sh` against the active tmpdir and continue per its directive.

**Post-/review boundary** (issue #1862): blocks session stop when `review-round-summary.md` exists (review ran) but neither `.review-boundary-passed` nor `.run-cleaned-up` exists. `.review-boundary-passed` is written by the orchestrator at the start of Step 6 after all three required post-/review actions complete (Cross-Skill Health Propagation + Track Rejected Code Review Findings + Step 6 breadcrumb). Recovery: execute those three actions in order, then `touch "$IMPLEMENT_TMPDIR/.review-boundary-passed"`.

Both checks share the `.run-cleaned-up` sentinel as the terminal escape: once teardown writes it the hook allows all stops through. The `stop_hook_active` guard prevents a continuation-loop trap. The block envelope shape (top-level `{"decision":"block","reason":"..."}`) was verified against the Claude Code hooks reference. If `jq` is missing, the hook emits a static literal block envelope.

Edit in sync with `lib-resolve-implement-tmpdir.sh`, `post-design-boundary.sh`, `hooks/hooks.json`, `skills/implement/SKILL.md` Step 6, and `scripts/test-implement-anti-halt.sh`.
