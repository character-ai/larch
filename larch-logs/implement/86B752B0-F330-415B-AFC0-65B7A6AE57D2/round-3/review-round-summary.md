# Review Round 3

- Mode: `diff`
- 12 accepted, 3 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Escalation-success reports render an unrecoverable failure class
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Escalation-success auto-seeding sets `FAILURE_CLASS=unrecoverable`, and Tier B projection prints it. A merged escalation-success report with ledger-only evidence can claim an unrecoverable failure despite the success report kind.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_10: Caller-selected report surface can bypass Tier B protections
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `compose-report` lets caller-selected `--surface` choose Tier A versus Tier B. Consumer or forked runs can request `issue-input` and receive Tier A output with client-bearing fields, bypassing Tier B allowlists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_11: Tier A appends failure detail logs without revalidating containment
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Tier A reads `FAILURE_DETAIL_LOG` from classification without revalidating containment. A tampered classification env can point at a readable local file, which then gets copied into public issue input after only secret redaction.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_12: Root-cause validation accepts header-only artifacts
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Root-cause validation can accept reports with verdict, confidence, and summary but no investigation prose or durable evidence citations. This can publish low-signal escalation reports.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_14: Bash and Python lint-fix ledger remapping diverge for ship-pr CI
- **Reviewer(s)**: dyn-python-bash-parity-output.txt
- **Severity**: important
- **Concern**: Bash `emit_lint_fix_ledger_ready` emits `LINT_FIX_LEDGER_SITE=$SITE` and `LINT_FIX_LEDGER_TRIGGER=main-agent-required`, while Python remaps `ship-pr-ci-initial` to `ship-pr-internal` and `ship-pr-internal-lint-fix`. The two default drivers can expose contradictory ledger-ready KVs from the same lint-fix surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-python-bash-parity-output.txt: Address the concern above.


### FINDING_18: Python 3.11 guard ship paths omit ledger keys
- **Reviewer(s)**: dyn-json-stdout-contract-output.txt
- **Severity**: important
- **Concern**: Python 3.11 guard paths emit minimal `STALLED` JSON without the eight new `ledger_*` keys. Normal ship results include those keys, so strict JSON consumers or orchestrator helpers can misread guard output or fail on missing fields.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-json-stdout-contract-output.txt: Address the concern above.


### FINDING_2: Classifier matched-pattern assignments are lost through command substitution
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `classify_from_evidence` runs inside command substitution, so `MATCHED_CLASSIFIER_PATTERN` assignments do not persist. Step 3 contract failures can emit `MATCHED_CLASSIFIER_PATTERN=no-match` instead of `step-contract`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_3: Tier B sensitive-token validation can leak client evidence text, paths, or short identifiers
- **Reviewer(s)**: codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Tier B sensitive corpus construction omits raw evidence text, repo-relative path shapes, and short tokens. Bounded prose can echo client plan text, issue text, branch names, repo-relative paths, or short repo tokens into consumer-facing output while passing validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_4: Tier B validates root-cause prose but does not render it
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Tier B validates bounded root-cause prose but renders only `summary=`, so consumer escalation reports omit the evidence-cited investigation details.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_5: Step 8 does not route new ship-pr handoff reasons to Main Claude repair
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Step 8 routing omits new ship-pr handoff reasons emitted by scripts. `ship-pr-internal-lint-fix` or `ci-local-unfixable` can exit 3 but fall to user-input or stall handling instead of Main Claude repair.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_6: Step 5 escalation recording is not fail-open
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `record-escalation` runs under `set -e` in `run-step5-review.sh`. If ledger validation fails on a coder-main-agent-required handoff, the wrapper can exit from the helper instead of preserving the original review status and repair handoff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_7: Forked dry-run success is inferred too broadly
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `forked-dry-run` is treated as unconditional success when not stalled. Fork CI can fail without `STALL_TRACKING`, yet Step 18a.5 can still file `escalation-success` if the ledger is nonempty.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


