# Review Round 5

- Mode: `diff`
- Accepted findings: 4
- Rejected findings: 5
- Exonerated findings: 0
- Neutral findings: 0

## Accepted Findings

### FINDING_1: **Important** `correctness` [skills/review/scripts/review-core.sh:523](<OPERATOR_REPO_PATH>/skills/review/scripts/review-core.sh:523)  
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Important** `correctness` [skills/review/scripts/review-core.sh:523](<OPERATOR_REPO_PATH>/skills/review/scripts/review-core.sh:523)      The `main-agent-vote-required` path exits before calling `emit-tally.sh`, so 0-judge/degraded reviews do not get the new schema-2 `review-summary.json` with panel telemetry. Concrete scenario: when voter dispatch returns `TALLY_STATUS=main-agent-vote-required`, `review-core.sh` flushes the round log and exits, leaving `round-N/review-summary.json` missing or stale while stdout still reports `SCOUT_STATUS`/`DYNAMIC_SLOTS`. Call `emit-tally.sh` in this branch using the tally output files and pass `--scout-status`, `--dynamic-slots`, and `--static-slot-count` before `flush_round_log`. I could not run the shell harnesses because this sandbox is read-only and `mktemp` failed to create temp directories.
- **Suggested revision**: Address the concern above.


### FINDING_12: risk-integration: skills/review/scripts/review-core.sh:331-373
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] emit-tally runs without failure isolation on the panel-failed path under set -e If emit-tally or jq fails, review-core exits before emitting REVIEW_CORE_STATUS=panel-failed and before exit 2, so Step 5 may see a generic non-2 failure instead of a structured panel-failed stall Wrap emit in set +e with explicit RC handling, append-tool-failure on failure, or only copy_to_parent after successful emit
- **Suggested revision**: Address the concern above.


### FINDING_13: risk-integration: skills/review/scripts/review-core.sh:331-373;skills/review/scripts/review-core.sh:378-416
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] New emit-tally invocations in panel-failed and zero-findings paths run under set -e without guarding emit failure. emit-tally non-zero aborts before emit_kv and intended exit 2 (panel-failed) or success path for zero-findings; review-and-fix / Step 5 stall classification can misread the round. Wrap emit in set +e with explicit rc handling, or use || true and log while preserving REVIEW_CORE_STATUS and exit code contract.
- **Suggested revision**: Address the concern above.


### FINDING_8: correctness: scripts/ship-pr.sh (run_pr_create_phase after state_set_many PR_NUMBER/PR_URL)
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] write-final-report is fully swallowed (stdout/stderr discarded, || true) while log commit and push may still succeed A failed write-final-report leaves the committed run-log without an updated final-summary.md while the flow continues; remote tip can miss the artifact Stop swallowing errors: log failures to execution-issues or gate commit/push on write-final-report success
- **Suggested revision**: Address the concern above.


