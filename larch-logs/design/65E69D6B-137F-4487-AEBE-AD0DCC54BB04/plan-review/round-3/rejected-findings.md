### [Plan Review] FINDING_2

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/review/scripts/aggregate-findings.sh planned in plan.txt:194-199
- **Concern**: Plan adds shared aggregator prompt and validation logic where a local skip is enough for SIMPLE scope. Scenario: More shared LLM merge logic increases maintenance risk and can create new marker-matching failure modes while trying to protect the privileged marker
- **Proposed resolution**: For plan mode, when any input finding has a leading [SCOPE-REDUCTION] marker, skip aggregation and pass the deduped findings directly to tally; leave aggregate-findings.sh unchanged except tests/docs if needed


### [Plan Review] FINDING_16

### FINDING_16:
- **Reviewer(s)**: Cursor-dyn-marker-lifecycle
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:155-176
- **Concern**: `write_step3_result_env` is not listed in the `plan-review-loop.sh` edit bullets even though Key decision line 40 requires `SCOPE_ANCHOR_FILE` in both `emit_loop_kvs` and `write_step3_result_env`. Scenario: Pause/resume and `run-step3-review.sh` prefer `.step3-plan-review-result.env` over stdout; if implementers only add `emit_kv SCOPE_ANCHOR_FILE` to loop stdout, `SCOPE_ANCHOR_FILE` can be absent from the inner env and MainAgent re-tally / SKILL.md `--scope-anchor-file` threading fails silently
- **Proposed resolution**: Add an explicit bullet to persist `SCOPE_ANCHOR_FILE` inside `write_step3_result_env`, extend `_terminal_exit` to emit it on stdout, and keep `run-step3-review.sh` allowlists in sync (as the plan already proposes)


