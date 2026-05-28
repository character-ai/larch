# assess-plan-round.sh

Step 3.6 orchestrator: HARD gate, round ≥ 2, dispatch + tally, KV contract for SKILL.md (`ASSESSOR_*` keys).

- Reads `workflow_path` from `run-params.json` with a `jq` fast-path and a text fallback so the HARD gate still works when `jq` is unavailable.
- Captures dispatcher stdout KVs in a dedicated file and keeps incidental stderr/breadcrumb noise in the quiet log; control flow must never parse KVs from the quiet log.
- Any dispatch or breadcrumb-monitor failure degrades open by synthesizing the default verdict artifacts instead of tallying partial assessor files.
