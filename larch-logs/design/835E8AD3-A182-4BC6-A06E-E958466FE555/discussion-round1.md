## Decision 1: Version-floor check vs. signal detection
- **Question**: Add a hand-maintained `codex --version` floor check next to the model pins, or rely purely on detecting the gate signal at runtime?
- **Resolution**: Signal detection only. No version constant. Detect `Model metadata for <model> not found` and `requires a newer version of Codex` in probe + launch stderr and map to an upgrade message. No `codex --version` floor is added (the correct floor is only knowable after a failure; a constant would need a manual bump each model rotation).
- **Source**: user

## Decision 2: Step 0 probe model
- **Question**: The probe currently exercises only `codex_role="default"` (gpt-5.6-sol). Should it also exercise luna/terra, or change model?
- **Resolution**: Switch the Step 0 codex probe to exercise **gpt-5.6-luna only** (highest-volume review model, cheapest/mini pricing). Do NOT probe sol or terra. Cross-role (sol/terra) gating is caught reactively at launch via the new signal detection, not at Step 0. Accepted trade-off: a luna-only probe will not mark codex unavailable up front when only sol/terra is gated (as in the reported incident).
- **Source**: user

## Decision 3: Actionable messaging surfaces (in scope)
- **Question**: Where must the actionable "upgrade Codex CLI" message surface?
- **Resolution**: Two surfaces. (1) The Step 2 launch drift warning (`/implement`) when a launch hits the gate signal. (2) `/larch:status` (and the shared degraded-tools explanation) when the probe hits the gate signal. Message form: "codex CLI too old for <model>; run `npm install -g @openai/codex@latest`".
- **Source**: issue #7072 proposed fix, confirmed in scope

## Decision 4: Hard constraints / non-goals (codebase-derived)
- **Question**: What must not break, and what is out of scope?
- **Resolution**: Preserve the `KEY=value` stdout grammars of `agent check-reviewers`, `agent degraded-tools-gate`, and `status check` (downstream parsers). Preserve the exit-99 launcher sentinel behavior in `collect_results.py` / `dispatch_step2.py`; the fix adds the actionable server message alongside it, it does not replace the sentinel. Do NOT change the 60s probe cache TTL (out of scope; not flagged by the issue). Do NOT add per-model version floors or probe-all-roles. Smallest change: signal detection helper + probe-model switch + two message surfaces.
- **Source**: codebase (`python/larch/agents/_auth.py`, `python/larch/agents/collect_results.py`, `python/larch/implement/dispatch_step2.py`)
