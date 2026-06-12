# Review Round 1

- Mode: `diff`
- 18 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Step 6 lint-fix handoff falls into recovery instead of returning ledger-ready exit 3
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-risk-integration-output.txt, dyn-architecture-output.txt
- **Severity**: important
- **Concern**: `scripts/ship-pr.sh` still routes `main-agent-required` from ship-pr-internal lint-fix through `run_recovery_waterfall` or stall handling. The documented Step 6 carve-out does not return before recovery, does not reliably clear stall tracking, does not set `BAIL_REASON=ship-pr-internal-lint-fix`, and does not hand ledger-ready evidence to the orchestrator.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-risk-integration-output.txt: Implement the documented handoff branch in `run_checks_phase` (and the Python checks equivalent): set `BAIL_REASON=ship-pr-internal-lint-fix`, emit ledger-ready data, return exit **3** with `STALL_TRACKING=false`, and add regression tests for the Step 6 carve-out.
  - From dyn-architecture-output.txt: On `main-agent-required` from ship-pr-internal lint-fix, set `BAIL_REASON=ship-pr-internal-lint-fix`, clear stall tracking, emit ledger-ready KV (or forward `LINT_FIX_LEDGER_*`), and exit 3 before `run_recovery_waterfall`; add a regression test in the ship-pr harness.


### FINDING_10: Tier B sensitive validation checks corpus lines but misses extracted values and shapes
- **Reviewer(s)**: codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Tier B bounded-prose validation relies too much on exact corpus lines or operator supplements. It may miss sensitive `KEY=value` values, URLs, absolute paths, or paraphrased client facts that were not present verbatim in the checked corpus.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_11: Tier A loses raw bail reasons before rendering
- **Reviewer(s)**: codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Tier A rendering uses sanitized or enum-checked bail reasons from classification instead of preserving raw evidence until final secret redaction. Dev-clone reports can show `redacted` instead of useful dispatcher bail tokens.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_12: Tier B bail-token allowlist is incomplete and grammar is inconsistent
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt, dyn-risk-integration-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `safe_bail_reason_value` omits several valid needs-user tokens such as `fix-attempts-exhausted` and `ship-pr-internal-lint-fix`. It also appears to allow bare `ci-local-unfixable` despite the required compound suffix grammar. Valid operator handoff bails can render as `redacted`, while malformed compound tokens may render as safe.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.
  - From dyn-risk-integration-output.txt: Extend `safe_bail_reason_value` (and any lint/TSV parity source) with the full `needs_user_bail_reason` set; add `test-stall-recovery-report.sh` fixtures that compose Tier B reports with each token and assert verbatim rendering.
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_13: Bash `SHIP_PR_LEDGER_*` parse contract is undocumented and untested
- **Reviewer(s)**: codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-risk-integration-output.txt
- **Severity**: important
- **Concern**: Bash ship-pr can emit `SHIP_PR_LEDGER_*` fields, but the orchestrator contract documents only Python `ledger_*`, `LINT_FIX_LEDGER_*`, and `STEP5_REVIEW_LEDGER_*` surfaces. Bash-path handoffs may recover successfully without any prompt-side `record-escalation` call, causing Step 18a.5 to skip the required escalation-success report.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.
  - From dyn-risk-integration-output.txt: Either rename bash output to the pinned `ledger_*` JSON keys on a documented stdout channel, or document and test `SHIP_PR_LEDGER_*` parsing in `SKILL.md`, `ship-pr-exit-matrix.md`, and a `test-step-8-ship.sh` / ship-pr harness case.


### FINDING_16: Ledger KV regression tests are missing for lint-fix and Step 5 review harnesses
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Harness updates for `LINT_FIX_LEDGER_*` and `STEP5_REVIEW_LEDGER_*` are incomplete or absent. Field-name drift, stdout parsing regressions, missing ledger rows, MAV KV issues, or duplicate records can ship undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_17: compose-report reads caller-supplied artifact paths without tmpdir confinement
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `compose-report` reads several caller-supplied files without verifying they are regular, non-symlink files under `IMPLEMENT_TMPDIR`. A bad call could include arbitrary readable files in Tier A issue input or Tier B output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_18: `test-ci-decide.sh` is not wired into Makefile or harness shards
- **Reviewer(s)**: cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The new `test-ci-decide.sh` harness is orphaned from Makefile and test-harness shard targets. CI and relevant checks can pass without running bail-token parity tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_19: Stall-recovery report test matrix is too thin
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-risk-integration-output.txt
- **Severity**: important
- **Concern**: `test-stall-recovery-report.sh` does not cover enough of the plan matrix. Missing coverage includes Tier A filing, terminal-failure compose, normalize-outcome precedence, Step 18a.5 skip logic, escalation evidence edge cases, fallback or tagged Tool Failure evidence, and bail-token union rendering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-risk-integration-output.txt: Add targeted fixtures that feed each bail token through `classify` + `compose-report` (Tier B) and assert non-`redacted` rendering for allowlisted tokens and `redacted` for unsanitized compound suffixes.


### FINDING_2: Python lint-fix ledger metadata is dropped before ship JSON
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-architecture-output.txt
- **Severity**: important
- **Concern**: `FixOutcome` carries lint-fix ledger fields, but Python loses them while converting through `LoopResult`, `StepResult`, and ship JSON. The default Python ship path can return `NEEDS_USER_INPUT` / `main-agent-required` with no populated `ledger_ready` payload.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From dyn-architecture-output.txt: Introduce a single ledger-handoff carrier (nested struct on `LoopResult` / `StepResult`, or explicit propagation from `FixOutcome`) and map ship-pr-internal lint-fix to `needs_user_reason=ship-pr-internal-lint-fix` with populated `ledger_*` in `_step_result_to_ship`; add an integration test from `run_checks_phase` through `_step_result_to_ship`.


### FINDING_22: Bash ship-pr emits ledger-ready data for too few exit 3 handoffs
- **Reviewer(s)**: dyn-risk-integration-output.txt
- **Severity**: important
- **Concern**: `emit_ship_pr_ledger_ready` appears to run only on the `ci-wait` `ACTION=bail` branch. Other exit 3 handoffs such as `first-fixer-non-health` or `ci-local-unfixable:*` may not emit ledger-ready data, despite docs saying bash ship-pr does.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-risk-integration-output.txt: Call `emit_ship_pr_ledger_ready` (or equivalent) immediately before every exit **3** that hands work to Main Claude, using the same phase and `BAIL_FAILURE_DETAIL_LOG` already written to state.


### FINDING_23: Bail-token lint does not check all runtime emitters
- **Reviewer(s)**: dyn-risk-integration-output.txt
- **Severity**: important
- **Concern**: `cmd_lint` compares only TSV, code allowlist rows, and doc tables. It does not verify the expanded bail-token union against `ci-decide.sh`, `needs_user_bail_reason`, or Python `NEEDS_USER_REASON_TOKENS`, so drift can pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-risk-integration-output.txt: Add a lint sub-check (or extend `scripts/test-ci-decide.sh`) that asserts every token from those emitters is accepted by `safe_bail_reason_value`, with compound `ci-local-unfixable:` grammar tests as specified in the plan.


### FINDING_24: Python lint-fix ledger phase mapping diverges from bash
- **Reviewer(s)**: dyn-architecture-output.txt
- **Severity**: important
- **Concern**: Python maps non-step3/step5/step6 ledger sites to `ci-merge`, while bash distinguishes `ship-pr-ci-initial` from CI merge paths. Default Python ship-driver ledger rows can record the wrong phase.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-architecture-output.txt: Mirror the bash `case` table in a shared helper (or explicit site→phase map) and add parity tests for `ship-pr-ci-initial`, `ship-pr-ci-merge`, and `ship-pr-ci-per-job`.


### FINDING_25: Python ship ledger phase is hardcoded to ci-merge
- **Reviewer(s)**: dyn-architecture-output.txt
- **Severity**: important
- **Concern**: `_step_result_to_ship` hardcodes `ledger_phase="ci-merge"` for every ledger-ready handoff. Handoffs during `ci-initial` can be mis-tagged in the default Python driver.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-architecture-output.txt: Thread the active ship phase into `_step_result_to_ship` (from state or caller context) and set `ledger_phase` from that, with parity tests for `ci-initial` and `ci-merge`.


### FINDING_3: Python CI decide emits prose bail reasons instead of machine tokens
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-risk-integration-output.txt
- **Severity**: important
- **Concern**: `python/ci_monitor.py` still emits old prose bail reasons while bash `ci-decide.sh` emits machine tokens. Python-driven reports can render redacted Tier B bail reasons and drift from the bash token contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From dyn-risk-integration-output.txt: Update `python/ci_monitor.py:decide()` to emit the same tokens as `scripts/ci-decide.sh`, add parity tests in `python/test_ci_monitor.py`, and run one cross-driver assertion that both paths produce identical bail tokens for the same counters.


### FINDING_4: Escalation-success report requires classification even when success only has ledger evidence
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `compose-report` requires `stall-recovery-classification.env` for `escalation-success` reports. Successful runs with escalation ledger evidence may never classify, so Step 18a.5 can fail before filing the required report.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_5: Tier A failure-detail log path is not persisted for rendering
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `classify` validates or receives a failure-detail log, but does not persist `FAILURE_DETAIL_LOG` into `classification.env`. Tier A compose then tries to read a missing value, so terminal reports omit validated failure-detail logs. One reviewer also noted Tier A may read `BRANCH` instead of `BRANCH_NAME`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_6: `ship-pr-internal-lint-fix` token is allowlisted but not emitted on the intended path
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The `ship-pr-internal-lint-fix` bail token exists in allowlists and docs, but no runtime producer assigns it for the Step 6 handoff. Reports and ledger triggers cannot distinguish that path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


