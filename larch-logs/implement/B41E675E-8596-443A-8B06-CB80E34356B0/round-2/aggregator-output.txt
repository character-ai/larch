### FINDING_1: Missing unset CLAUDE_PLUGIN_ROOT regression for lint-fix-loop
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `scripts/test-lint-fix-loop.sh` does not cover the production path when `CLAUDE_PLUGIN_ROOT` is unset. A bad plugin-root fallback could fail to source telemetry helpers or omit `codex_lint_fix` ledger output without a targeted harness failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: Missing unset CLAUDE_PLUGIN_ROOT regression for negotiation
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `scripts/test-run-negotiation-round.sh` does not cover the Codex negotiation path when `CLAUDE_PLUGIN_ROOT` is unset. A bad plugin-root fallback could fail helper sourcing or omit `codex_negotiation` ledger output without a targeted harness failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_3: Missing round_artifact_included unit exclusions
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Unit-level `round_artifact_included` tests do not directly pin exclusion of `codex.events.jsonl` and `foo.events.jsonl`; only `coder-codex.events.jsonl` is covered directly. A targeted allowlist or glob regression could fail less clearly or slip past fast unit coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_4: Duplicated Codex telemetry invocation blocks
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Codex telemetry invocation logic is duplicated across `lint-fix-loop.sh`, `run-negotiation-round.sh`, and `review-and-fix.sh`, increasing drift risk for future argv, sidecar, or telemetry-order changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: Duplicated synthetic Codex stub fixture logic
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Synthetic JSONL and `--output-last-message` stub logic is duplicated across three harnesses, so fixture shape changes require coordinated edits and are easy to miss.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: Python timeout helper in get-issue-state test
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-get-issue-state.sh` uses a Python subprocess timeout helper instead of the plan-specified simple timeout approach, adding complexity and a `python3` dependency.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: Fragile awk/eval extraction of round_artifact_included
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `assert_round_artifact_included` extracts a nested function from `larch-log.sh` with `awk` and `eval`; formatting changes could break the test opaquely or exercise the wrong body.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_8: Inconsistent get-issue-state error emission style
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/get-issue-state.sh` uses inconsistent error-emission style between arity and flag-looking guards, creating maintainability noise without a claimed behavioral bug.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_9: Published wrapper logs used as telemetry parse sidecars
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Telemetry parse diagnostics are appended to publishable wrapper logs instead of dedicated `.sidecar` files in wrapped sites such as lint-fix-loop and review-and-fix. Malformed JSONL could leak prompt-bearing fragments through redacted run logs, and the implementation diverges from the planned sidecar/wrapper separation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_10: Wrapper progress moved to stderr without documented contract
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `run-external-agent.sh` now emits wrapper progress/diagnostics to stderr, but the behavior is outside the declared plan scope and lacks documentation or harness coverage. Callers that capture stdout may mis-parse if the contract changes again.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_11: Unexplained negotiation lock delay increase
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `LARCH_EXTERNAL_SERIAL_LOCK_DELAY` increased from 1 to 5 on the negotiation success path, adding several seconds to lint runs without an inline rationale or linked flake explanation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_12: Missing ledger diagnostic on empty or unparseable Codex events
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `external_launcher_record_usage_from_events` returns success without writing a ledger row when events JSONL is missing, empty, or unparseable. A timeout or early kill could still incur API usage while downstream token ledgers show no Codex row.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] get-issue-state harness docs omit new cases
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `scripts/get-issue-state.md` does not document new test cases `(h)` through `(k)`, making timeout and infinite-loop regression coverage less discoverable for contributors.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] Empty --issue value not rejected as missing value
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `scripts/get-issue-state.sh` treats `--issue ''` as a numeric validation error instead of a value-required error. The reviewer marked this as pre-existing and optional.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] Negotiation events basename assumes .txt output suffix
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `scripts/run-negotiation-round.sh` derives the events path with an `OUTPUT_FILE%.txt` suffix assumption. Non-`.txt` outputs get unexpected event basenames; reviewer marked this as pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
