# Review Round 2

- Mode: `diff`
- Accepted findings: 7
- Rejected findings: 2
- Exonerated findings: 0
- Neutral findings: 0

## Accepted Findings

### FINDING_1: **Nit** `correctness` `docs/run-logs.md:234` says `--design-only` runs skip Step 18, but [skills/implement/SKILL.md](<OPERATOR_REPO_PATH>/skills/implement/SKILL.md:1010) routes design-only completion to Step 16 and Step 18, and Step 17/18 still run `write-final-report.sh`. This makes the final-summary docs contradict the workflow. Update the sentence to say design-only skips Step 8+ PR creation, while terminal cleanup still runs and may refresh the tracking summary with `PR: N/A`.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Nit** `correctness` `docs/run-logs.md:234` says `--design-only` runs skip Step 18, but [skills/implement/SKILL.md](<OPERATOR_REPO_PATH>/skills/implement/SKILL.md:1010) routes design-only completion to Step 16 and Step 18, and Step 17/18 still run `write-final-report.sh`. This makes the final-summary docs contradict the workflow. Update the sentence to say design-only skips Step 8+ PR creation, while terminal cleanup still runs and may refresh the tracking summary with `PR: N/A`. Validation note: I attempted `make test-ship-pr` and `bash skills/implement/scripts/test-write-final-report.sh`, but the read-only sandbox blocked temp/cache creation under `/tmp` and `/var/folders`, so I could not verify the harnesses here.
- **Suggested revision**: Address the concern above.


### FINDING_10: risk-integration: scripts/test-ship-pr.sh:663-704
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] pr_create_final_summary_failure only exercises post-create write-final-report failure; pre-create failure is still fatal in ship-pr.sh but no longer covered by a dedicated scenario. A regression in the first write-final-report invocation could ship without failing test-ship-pr because the stub always succeeds before create-pr.sh. Add a harness scenario where the stub fails on the initial write-final-report call (without --comment-only) and assert exit_stall 9b / expected state.
- **Suggested revision**: Address the concern above.


### FINDING_4: code-quality: scripts/ship-pr.sh:999-1002
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Comments say post-create refresh is API-only. Someone tightening sandbox or auditing side effects may assume no filesystem writes under IMPLEMENT_TMPDIR and miss tmp summary rewrites. Clarify no extra git commit/push and that summary-final.md is still updated for the upsert.
- **Suggested revision**: Address the concern above.


### FINDING_5: code-quality: skills/implement/scripts/write-final-report.sh:1-3
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Shebang comment implies every run writes the run-log final-summary file. Maintainers skim the header and misconfigure or duplicate logic for comment-only mode. Update the header to mention optional skip of the tracked run-log copy.
- **Suggested revision**: Address the concern above.


### FINDING_7: risk-integration: scripts/ship-pr.sh:951-960
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Pre-create blocking write-final-report runs full upsert before create-pr; failure stalls with no PR. Transient or auth/API failure on placeholder larch:final-summary upsert exits 9b before PR creation; old flow had PR already when the same helper could fail after create-pr. Document trade-off or split file materialization from comment upsert for pre-create.
- **Suggested revision**: Address the concern above.


### FINDING_8: risk-integration: scripts/test-ship-pr.sh (pr_create harness section)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] No automated coverage for plan §1b first-phase write-final-report stall or §1c pre-PR larch-log commit best-effort continue. A refactor could remove exit_stall on the pre-create write or incorrectly stall when the pre-PR log commit fails; CI would stay green. Add stubbed scenarios: (1) write-final-report fails only without --comment-only and assert stall/exit code; (2) larch-log commit fails and assert create-pr still invoked and phase advances with Warnings recorded.
- **Suggested revision**: Address the concern above.


### FINDING_9: risk-integration: scripts/test-ship-pr.sh:663-701
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Misleading scenario name/comments for pr_create_final_summary_failure. Future readers assume the first (pre-PR) write failed, but only the post-create comment-only path is exercised. Rename make_repo slug and comments to reflect post-create comment refresh failure only.
- **Suggested revision**: Address the concern above.


