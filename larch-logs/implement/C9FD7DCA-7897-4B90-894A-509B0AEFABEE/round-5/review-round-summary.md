# Review Round 5

- Mode: `diff`
- 4 accepted, 11 rejected (3 neutral)

## Accepted Findings

### FINDING_13: Reviewer-prune filter harness lacks fail-open advisory cases
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test-reviewer-prune.sh` does not assert plan-required `PRUNE_FAIL_OPEN=true` advisory WARN behavior or absence of `PRUNE_STATUS`, so regressions in filter stdout could pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_17: Concise republish leaves stale per-round reviewer-prune ledgers
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `design-log-publish.sh` does not remove stale per-round `reviewer-prune-ledger.tsv` files on concise republish, allowing existing design logs to retain duplicate per-round ledgers despite the root-only ledger contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_3: Empty reviewer_signals results are misclassified as unavailable
- **Reviewer(s)**: codex-specialist-security-output.txt, codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `_audit_reviewer_signals_jq` treats valid zero-result `reviewer_signals` queries as unavailable, causing clean concise logs to emit skip instead of pass when no NS retries or trailing-content issues are present.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-security-output.txt, codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_4: Corpus smoke thresholds are looser than acceptance criteria
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test-fluff-analysis-corpus.sh` allows post-v49 latent and accepted-low-value acceptance regressions above the documented KPI thresholds to pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt: Address the concern above.


