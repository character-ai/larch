## Proposed Design Outline

### Goals
- Extract the `/design` Step 0b deterministic spine into two phase-driver scripts, removing ~65–100 inline SKILL.md lines.
- Keep observable behavior identical; fold in only low-risk cleanups (one env-refresh path, idempotent-on-replay rename/run-params).
- Match the rank-1 phase-driver convention so the spine becomes a thin orchestrator → driver → gate flow.

### Non-goals
- Move the clarify / already-planned `AskUserQuestion` gates or the `/larch:issue` call into a script.
- Touch the rank-1 Step 3 driver (#3244) or other umbrella #3133 siblings; change the public flag contract or `run-params.json` v3 schema.
- Write new driver test harnesses (existing harnesses get minimal updates only).

### Approach sketch
- `design-route.sh` (pre-gate): resume-detect → title-eligibility → reentry-guard → one `ROUTE=` verdict + parsed resume KVs.
- `design-init-runparams.sh` (post-gate): tier-resolve → `[DESIGNING]` rename → env-refresh → `write-run-params.sh` → router-flag merge.
- Both source `lib-phase-driver.sh`, write a result `.env`, emit `emit_kv` stdout, exit 0/1/2 (rank-1 pattern).
- SKILL.md Step 0b becomes: fetch issue → `design-route` → orchestrator handles clarify / already-planned / cancel gates → on proceed/resume → `design-init-runparams`.

### Surfaces in scope
- `skills/design/SKILL.md` (Step 0b region only)
- `skills/design/scripts/design-route.sh` + `.md` (new)
- `skills/design/scripts/design-init-runparams.sh` + `.md` (new)
- `scripts/test-design-structure.sh`, `scripts/test-step0b-router-flag-recovery.sh` (existing-harness anchor updates)

### Open questions
- Resume fidelity: how faithfully `ROUTE=resume@<STEP>` must encode the `STEP=0c` clarify-resume special case vs. leaving fine routing in the orchestrator. (Decide in plan; leans toward driver emits `ROUTE=` + KVs, orchestrator owns the jump.)
