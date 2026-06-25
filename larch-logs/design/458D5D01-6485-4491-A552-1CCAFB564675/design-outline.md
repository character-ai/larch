## Proposed Design Outline

### Goals
- Enumerate all remaining mechanical "background A returns → parse → launch background B" chains in `skills/implement/SKILL.md` (full sweep).
- Fold each mechanical chain into a single directive-emitting Python verb so the orchestrator takes one background turn instead of two.
- Keep the happy-path common case fast; preserve existing repair-loop and MAV-judgment prose for failure paths.

### Non-goals
- Folding chains that require main-agent judgment: MAV ballot reading/voting, coder-main-agent repair, conflict-resolution edits, rejected-findings tracking.
- Changing the Step 8+ ship driver (already clean: JSON handoff + `ship route-exit` emits `NEXT_ACTION`).
- Changing bootstrap result parsing (already clean: `BOOTSTRAP_NEXT` emitted by `bootstrap invoke`).
- Redesigning the #5274 checks-failure repair-loop macro or the #5271 commit-route interface.

### Approach sketch
- Enumerate the chains in SKILL.md by reading each background fence and its post-notification parse+branch block.
- For each mechanical pair (pass → deterministic next fence with no judgment), add a Python verb in `python/implement_dispatch.py` that runs both subprocesses sequentially and emits `NEXT_ACTION=continue|stall|checks-failed`.
- Primary targets: step-5 self-review (checks + commit-route), step-5 MAV aftermath (checks + step-5-resume --ready-to-commit), step-6→7 (checks + commit-route --site step7).
- Update SKILL.md to replace two-fence prose + two background fences with one-fence prose + single verb call.
- Update `scripts/test-implement-fence-shape.sh` `EXPECTED_OLD`/`EXPECTED_NEW` for any removed or added background fences.

### Surfaces in scope
- `python/implement_dispatch.py` — new verb functions.
- `python/cli.py` — verb registration table.
- `skills/implement/SKILL.md` — fence and prose updates for folded chains.
- `scripts/test-implement-fence-shape.sh` — fence-count regression harness.
- Sibling `.md` contracts for any new wrapper scripts.

### Open questions
- None.
