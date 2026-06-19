### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/plan_review_round.py:70-83,152-163
- **Concern**: Skipped non-dict slot rows still crash manifest relabeling after dispatch. Scenario: With --skip-invalid-slots, a manifest containing one valid slot and one JSON array or scalar row can be accepted by the waterfall and launch reviewers, but execute_round later re-reads plan-review-slots.ndjson and calls row.get on the non-dict value, raising AttributeError before findings and voters complete.
- **Proposed resolution**: Add isinstance(row, dict) guards, or use logging_util.iter_jsonl_dicts, in _load_manifest_slots and _compose_findings_from_collector.




### FINDING_3:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/plan_review_round.py:70-82,144-162
- **Concern**: Plan drops non-dict slot rows in the waterfall but leaves downstream manifest readers assuming every JSON line is a dict. Scenario: A plan-review manifest with one JSON scalar row and one valid row can dispatch successfully with --skip-invalid-slots, then _load_manifest_slots or _compose_findings_from_collector calls row.get and aborts the round
- **Proposed resolution**: Extend the plan with a minimal non-dict guard in the plan_review_round manifest loops, or rewrite the panel manifest to valid rows before later stages read it




### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/agent_waterfall.py:639-655
- **Concern**: Invalid-slot sidecar write timing is unspecified relative to reviewer launches. Scenario: Plan requires raising ValidationError when the invalid-slot sidecar cannot be written, but does not pin that write to immediately after slot load and before the first _launch_slot call. An implementer can place the sidecar write after phase launches succeed; a late write failure then exits rc=2 while external reviewers are already running, recreating a partial panel-failed state the feature is meant to avoid
- **Proposed resolution**: State explicitly in agent_waterfall.py changes: parse and drop invalid rows first; if skip mode has drops and at least one valid row, write INVALID_SLOT_DROPS_FILE and emit INVALID_SLOT_DROP_COUNT/WARN before any phase1/2/3 launch; on sidecar write failure raise ValidationError before launching




### FINDING_5:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/plan_review_round.py:369-386; skills/design/scripts/design-step3-review.sh:552-610
- **Concern**: The planned DEGRADED_PANEL_WARNING is emitted only by panel-dispatch and is not propagated through the production /design Step 3 boundary. Scenario: A panel drops one invalid slot row and succeeds; the panel-dispatch test passes, but design-step3-review.sh only allowlists selected result keys and WARN, so the operator/result env do not record the degraded-panel warning the issue requires
- **Proposed resolution**: Thread the warning through an existing surfaced key such as WARN, or add DEGRADED_PANEL_WARNING to the round/result-env/wrapper propagation path; add one round-level coverage check rather than only panel-dispatch coverage




### FINDING_6:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/agent_waterfall.py:639-763
- **Concern**: Invalid-slot sidecar write timing is unspecified relative to reviewer launches. Scenario: The plan requires ValidationError when the invalid-slot sidecar cannot be written, but places sidecar emission in dispatch_waterfall without ordering it before _launch_slot. Following the existing DROPPED_SLOTS_FILE pattern would write the sidecar after launches; an OSError there would exit rc=2 after reviewers already started, and dispatch_panel would treat the round as panel-failed despite partial reviewer output.
- **Proposed resolution**: Pin the contract: after load with drops and before any _launch_slot call, write <paths-file>.invalid-slots (or fail closed with no launches and no paths file). Keep stdout KVs at successful completion; on post-load write failure do not launch reviewers.




