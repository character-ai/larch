## Decision 1: Absorption scope — initial vs resume
- **Question**: Does absorption of the degraded-tools gate and 1.r checkpoint apply to `--mode initial` only, or also to `--mode resume`?
- **Resolution**: Both. Absorption applies to both modes. On resume (`up_to_phase="plan"`), `_phase_coder` does not run, so the new absorption phase reads the prior coder from `bootstrap-routing.env` before running the gate and 1.r. Dirty-tree recovery still works (resume bootstrap runs gate + 1.r internally instead of the orchestrator calling them explicitly).
- **Source**: user

## Decision 2: step-0-degraded-gate.sh fate
- **Question**: Can `step-0-degraded-gate.sh` be retired, or must it stay for backward compat?
- **Resolution**: Retire it. Since both initial and resume absorb the gate, the standalone shell script is no longer called from SKILL.md. `test-implement-structure.sh` and `SKILL.md`'s wrapper list are updated accordingly.
- **Source**: user (via "Also absorb on resume" choice)

## Decision 3: PHANTOM_* KVs after 1.r absorption
- **Question**: Should PHANTOM_* KVs from the absorbed 1.r be added to ROUTING_KEYS and forwarded in the envelope?
- **Resolution**: No. PHANTOM_* KVs are advisory telemetry only (SKILL.md: "do not act on them"). They are emitted to bootstrap stdout but NOT added to ROUTING_KEYS. Consistent with existing treatment.
- **Source**: codebase (SKILL.md line 320)

## Decision 4: Orchestrator explanation for both-down AskUserQuestion
- **Question**: After absorption, how does the orchestrator get the per-tool explanation when DEGRADED_PROMPT_REQUIRED=true?
- **Resolution**: Add DEGRADED=true, BOTH_DOWN=true, CODEX_STATE, CURSOR_STATE to the routing envelope (new ROUTING_KEYS entries). Orchestrator regenerates the explanation from those KVs (same content as degraded_tools_result()). One-down notice and non-interactive degraded logging are handled inside the bootstrap.
- **Source**: codebase (agents.py degraded_tools_result logic)

## Decision 5: Forked-target rebase args
- **Question**: When forked_target=true, does 1.r need explicit --base-remote/--base-ref?
- **Resolution**: No. Defaults (upstream/main) are used, same as current SKILL.md call site that only passes --forked-target.
- **Source**: codebase (SKILL.md line 342, rebase-checkpoint-probe.sh defaults)
