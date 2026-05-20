### FINDING_1: **Important** `correctness` [skills/review/scripts/review-core.sh:523](<OPERATOR_REPO_PATH>/skills/review/scripts/review-core.sh:523)  
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Important** `correctness` [skills/review/scripts/review-core.sh:523](<OPERATOR_REPO_PATH>/skills/review/scripts/review-core.sh:523)      The `main-agent-vote-required` path exits before calling `emit-tally.sh`, so 0-judge/degraded reviews do not get the new schema-2 `review-summary.json` with panel telemetry. Concrete scenario: when voter dispatch returns `TALLY_STATUS=main-agent-vote-required`, `review-core.sh` flushes the round log and exits, leaving `round-N/review-summary.json` missing or stale while stdout still reports `SCOUT_STATUS`/`DYNAMIC_SLOTS`. Call `emit-tally.sh` in this branch using the tally output files and pass `--scout-status`, `--dynamic-slots`, and `--static-slot-count` before `flush_round_log`. I could not run the shell harnesses because this sandbox is read-only and `mktemp` failed to create temp directories.
- **Suggested revision**: Address the concern above.

### FINDING_2: **Important** `risk-integration` [skills/review/references/heavy-worker.md:65](<OPERATOR_REPO_PATH>/skills/review/references/heavy-worker.md:65)  
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `risk-integration` [skills/review/references/heavy-worker.md:65](<OPERATOR_REPO_PATH>/skills/review/references/heavy-worker.md:65)      The `/review --subagent` heavy-worker contract still tells the worker to write `review-summary.json` with `schema_version: 1` and no `panel` object. Concrete breakage: a subagent review can successfully return a schema-1 summary, so the committed run-log still lacks `panel.scout_status`, `panel.static_slot_count`, `panel.dynamic_slot_count`, and `panel.total_slot_count` despite the new inline `emit-tally.sh` schema. Update this runtime prompt contract to schema version 2 and include the new `panel` fields/defaults.
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] architecture: larch-logs/implement/5F7568AE-E8DA-4B76-8E08-E03C1DA604FC/
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Committed implement run-log snapshot from chore(larch-logs) flush. Not plan fidelity for the three fixes; excluded by review scope rules. No action required for plan fidelity.
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] correctness: skills/review-and-fix/scripts/review-and-fix.sh:625-698
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] write_rejected_findings_aggregate only discovers directories named round-<digits> Non-canonical round directory names would be skipped from aggregation Established naming contract; only relevant if future code creates zero-padded round dirs
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] correctness: skills/review/scripts/review-core.sh:523-540
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] main-agent-vote-required exit still skips emit-tally That round may not refresh review-summary.json with schema v2 panel fields Pre-existing path; consider a follow-up if consumers require JSON on every exit branch
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] security: skills/review-and-fix/scripts/review-and-fix.sh (write_rejected_findings_aggregate mktemp+mv)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] /tmp mktemp then mv into impl_tmpdir is symlink-TOCTOU sensitive for same-user attackers Same-user attacker could race the temp file to redirect mv behavior (classic /tmp issue) Hardening would be repo-wide tmpdir policy; not introduced solely by this diff
- **Suggested revision**: Address the concern above.

### FINDING_7: architecture: skills/implement/SKILL.md:1659-1709 (Pre-bump log flush prose)
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Implemented fix diverges from original Step 7a write-final-report plan in the issue text Operators following the old issue spec may still expect a Step 7a write; SKILL now documents ship-pr timing instead Align external issue/PR description with shipped Step 8+ / refresh-run-logs behavior
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: scripts/ship-pr.sh (run_pr_create_phase after state_set_many PR_NUMBER/PR_URL)
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] write-final-report is fully swallowed (stdout/stderr discarded, || true) while log commit and push may still succeed A failed write-final-report leaves the committed run-log without an updated final-summary.md while the flow continues; remote tip can miss the artifact Stop swallowing errors: log failures to execution-issues or gate commit/push on write-final-report success
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: skills/implement/SKILL.md:1659-812; scripts/ship-pr.sh:377-463; scripts/refresh-run-logs.sh:249-307
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Part B of the supplied plan and feature_description required write-final-report.sh in Step 7a before larch-log commit; diff forbids Step 7a and implements ship-pr/refresh-run-logs instead. A checklist review against the pasted Part B marks the requirement unmet or inverted even if the branch fixes final-summary commit timing another way. Implement the Step 7a ordering from the plan or update the plan and feature text to the ship-pr and refresh-run-logs architecture.
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: skills/implement/SKILL.md:1679;scripts/ship-pr.sh:970-1015
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Part B lifecycle contradicts written plan/feature: SKILL forbids Step 7a write-final-report; fix lives in ship-pr post-create instead. An operator or doc-driven automation expecting the Step 7a write-final-report call from the plan will not find it and may diverge from the implemented fix. Reconcile feature/plan with SKILL or change code to match the documented Step 7a placement.
- **Suggested revision**: Address the concern above.

### FINDING_11: risk-integration: skills/review/scripts/review-core.sh:273-283 skills/review/scripts/review-core.sh:403-416
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Non-integer DYNAMIC_SLOTS/STATIC_SLOT_COUNT from dispatch is not validated before emit-tally Dispatch bug or corrupted env emits DYNAMIC_SLOTS=abc → emit-tally exits 2 → set -e aborts review-core before status lines Validate or sanitize slot counts in review-core to match emit-tally digit rules
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: skills/review/scripts/review-core.sh:331-373
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] emit-tally runs without failure isolation on the panel-failed path under set -e If emit-tally or jq fails, review-core exits before emitting REVIEW_CORE_STATUS=panel-failed and before exit 2, so Step 5 may see a generic non-2 failure instead of a structured panel-failed stall Wrap emit in set +e with explicit RC handling, append-tool-failure on failure, or only copy_to_parent after successful emit
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: skills/review/scripts/review-core.sh:331-373;skills/review/scripts/review-core.sh:378-416
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] New emit-tally invocations in panel-failed and zero-findings paths run under set -e without guarding emit failure. emit-tally non-zero aborts before emit_kv and intended exit 2 (panel-failed) or success path for zero-findings; review-and-fix / Step 5 stall classification can misread the round. Wrap emit in set +e with explicit rc handling, or use || true and log while preserving REVIEW_CORE_STATUS and exit code contract.
- **Suggested revision**: Address the concern above.

### FINDING_14: security: skills/review/scripts/emit-tally.sh (new --scout-status branch in branch diff)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] SCOUT_STATUS is passed to jq without length or format validation unlike numeric slot flags A pathological scout_status string produces an arbitrarily large review-summary.json and can exhaust memory or break tools that parse the summary Validate or cap scout_status length (and optionally allowlist values) before jq emission
- **Suggested revision**: Address the concern above.

