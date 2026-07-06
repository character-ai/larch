## Proposed Design Outline

### Goals
- Stop the spurious `<task-notification>` feedback loop within 2-3 turns instead of 5+.
- Make repeated spurious notification turns invisible (deny the classification Read after N empty reads so the model makes zero tool calls).
- Fix the circuit breaker so it fires on notification turns regardless of whether `<task-notification>` triggers `UserPromptSubmit` hooks.
- Reinforce the "zero prose, zero tool calls on silent yield" contract in docs.

### Non-goals
- Do not change platform behavior for firing `<task-notification>` events.
- Do not break legitimate completion detection (marker-release path stays intact).
- Do not modify `/design` orchestrator step logic in SKILL.md beyond the silent-yield contract note.
- Do not touch Python code or the `python/` tree (all changes are Bash hooks + Markdown docs).

### Approach sketch
- **Fix 1**: Lower `LARCH_NO_PROGRESS_GUARD_THRESHOLD` default 5 → 3 in `hook-no-progress-guard.sh`.
- **Fix 2**: Add a per-`tasks/<id>.output` empty-read counter in `hook-bg-poll-guard.sh`; deny further Reads of the same file after 2 empty reads; reset counter when content changes or the marker goes away.
- **Fix 3**: In the Stop handler of `hook-no-progress-guard.sh`, when the counter reaches threshold, emit `{"decision":"block","reason":"..."}` directly (one-shot: reset counter after emitting to avoid re-entry loops) so the circuit breaker fires immediately even if `<task-notification>` does not trigger `UserPromptSubmit`.
- **Fix 4**: Update `skills/shared/design-background-wait.md` to explicitly prohibit prose output and tool calls on silent-yield turns; add a matching note to `SKILL.md` Step 3 notification boundary.

### Surfaces in scope
- `scripts/hook-no-progress-guard.sh` + `scripts/hook-no-progress-guard.md`
- `scripts/hook-bg-poll-guard.sh` + `scripts/hook-bg-poll-guard.md`
- `skills/shared/design-background-wait.md`

### Open questions
- Confirm that the Stop-hook block one-shot sentinel (`no-progress-block-emitted`) correctly resets so later genuine silent-yield turns are not permanently blocked after the first block fires.
