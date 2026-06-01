## Proposed Design Outline

### Goals
- Extract E1: add `clear-stall` (stall-recovery.md steps 7.1-7.7) and `seed-terminal-state` (steps 8.1-8.3) subcommands to `stall-recovery-report.sh`.
- Extract E2: add a new standalone Step-18b wrapper that renders the token report, runs `write-final-report.sh`, snapshot-compares `summary-final.md`, and emits `EMIT_BODY=true|false`.
- Full cutover: rewrite the orchestrator prose so it delegates to both helpers.

### Non-goals
- No changes to `ship-pr.sh` (E1=18a, E2=18b are disjoint from it).
- Keep prompt-side: in-memory `STALL_TRACKING` clear (step 7.6), the verbatim `summary-final.md` emit, and `.step17-printed` / `.step17-emitted` sentinels (NEVER #20). The wrapper only DECIDES `EMIT_BODY`.
- Do not move step-8 bug-comment generation, dry-run eval, or issue-number load (only the 8.1-8.3 durable write moves).

### Approach sketch
- E1: both subcommands reuse existing `atomic_write_text` / `kv_get` / `validate_ship_pr_state`; `clear-stall` does temp-write -> reread+assert false -> `mv -f` -> reread+assert false and emits a `CLEARED=true|false` KV; `seed-terminal-state` rewrites-or-seeds the canonical Step-8 key shape with `STALL_TRACKING=true` then reconfirms.
- E2: new `skills/implement/scripts/` wrapper owns the token-report render + report run + snapshot/`cmp`, emitting `EMIT_BODY`; orchestrator does the verbatim emit + sentinel only on `EMIT_BODY=true`.
- Rewrite `stall-recovery.md` steps 7-8 and `SKILL.md` Step 18b `_wfr_` block to call the helpers.

### Surfaces in scope
- `skills/implement/scripts/stall-recovery-report.sh` (+ `.md`, `test-stall-recovery-report.sh`).
- New E2 wrapper `.sh` (+ sibling `.md` + offline harness).
- `skills/implement/references/stall-recovery.md`; `skills/implement/SKILL.md` Step 18b.

### Open questions
- None.
