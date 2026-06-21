### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/test-step3-orchestrator-fence.sh:54-179
- **Concern**: `apply_step3_handoff` still duplicates the pre-thin Bash handoff via `read-result-env.sh` and inline status mapping; the plan only retargets wrapper static pins. Scenario: Most `make test-step3-orchestrator-fence` behavioral cases call `apply_step3_handoff` directly, not `design-step3-review.sh`, so they never exercise `plan-review normalize-status` and can stay green while the duplicated helper drifts (it already omits `panel-init-failed` from the forward-map at lines 125-132)
- **Proposed resolution**: Replace `apply_step3_handoff` with a thin subprocess wrapper around `python3 "$REPO_ROOT/python/cli.py" plan-review normalize-status --design-tmpdir … --stdout-file … --loop-rc …`, keep `DISPLAY_ONLY` as a separate display filter, and update the header comment at lines 39-40



### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/plan_review.py:375
- **Concern**: In-process step3_record_report_evidence failure emits machine WARN= to stdout via logging_util.emit_kv. Scenario: Thinning replaces bash subprocess >/dev/null 2>&1 with a direct Python call; on failure emit_kv prints WARN= before the canonical envelope, breaking orchestrator KV parsing and hook-safe stdout contracts
- **Proposed resolution**: Wrap the in-process step3_record_report_evidence call with stdout suppression (devnull or capture); on nonzero rc emit only the existing markdown stderr warning, never machine WARN=



