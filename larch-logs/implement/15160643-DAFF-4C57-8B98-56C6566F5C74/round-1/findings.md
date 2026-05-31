### FINDING_1: [OUT_OF_SCOPE] Collector retry stderr-sink coverage is static instead of behavioral
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-meta-contract-output.txt, dyn-launcher-parity-output.txt
- **Severity**: important
- **Concern**: Retry forwarding for `--stderr-sink` is mainly asserted with source greps rather than runtime argv checks across outer-launcher and CMD_JSON retry paths. Regressions could leave string literals in place while dropping actual forwarding, failing to prove forward and omit behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-meta-contract-output.txt: Address the concern above.
  - From dyn-launcher-parity-output.txt: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] Launch-review stderr-sink threading tests do not prove lane argv
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-meta-contract-output.txt, dyn-launcher-parity-output.txt
- **Severity**: important
- **Concern**: `launch-review.sh` coverage relies on weak or source-only checks for `--stderr-sink` threading. Codex greps are not lane-scoped enough, and cursor primarily checks meta recording, so regressions in actual `run-external-agent.sh` argv forwarding could pass tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-meta-contract-output.txt: Address the concern above.
  - From dyn-launcher-parity-output.txt: Address the concern above.

### FINDING_3: Duplicate STDERR_SINK meta writes can hide divergence
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `STDERR_SINK=` can be written by both base `.meta` handling and outer meta append paths, creating duplicate keys where last-wins parsing may hide inconsistencies.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] Invalid stderr-sink exit-code contract is inconsistent
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The plan reportedly expected exit 2 for invalid `--stderr-sink`, while implementation/tests pin exit 1. Docs, plan, and launcher behavior may disagree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] Collector duplicates meta parsing logic
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `collect-agent-results.sh` has duplicated `.meta` parsing blocks for function and inline paths, increasing maintenance risk when adding fields such as `STDERR_SINK`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] Non-review launchers do not round-trip future stderr sinks
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `launch-cursor-implement.sh` and `launch-cursor-ci.sh` append outer meta without accepting or passing a stderr sink, so future adoption of `--stderr-sink` in those lanes would drop the field on retry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_7: CMD_JSON stderr-sink traversal guard is not tested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The CMD_JSON retry path lacks a test proving malicious `STDERR_SINK` values containing `..` are rejected by collector retry metadata validation rather than deferred to `run-external-agent.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_8: Documentation field list omits STDERR_SINK
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `scripts/collect-agent-results.md` documents the parser/writer field list without `STDERR_SINK`, even though the field is now parsed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] Shared globals may race across concurrent empty-output retries
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Multi-reviewer empty-output retry appears to use shared globals across background subshells, which could send the wrong stderr sink or related argv to a child if loop state changes before exec.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] Initial stderr-sink validation allows broader paths than retry validation
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Initial `--stderr-sink` handling allows absolute paths and `..` under `validate_meta_scalar_path`, while collector retry rejects `..`; first-pass stderr selection could read or write unintended paths before retry fail-closed behavior applies.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] Outer retry suppresses launcher stderr
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Outer-launcher retry runs with stderr redirected away, reducing operator visibility into retried launcher failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] Launch-review risk flag does not round-trip into outer meta
- **Reviewer(s)**: dyn-meta-contract-output.txt
- **Severity**: latent
- **Concern**: `launch-review.sh` accepts `--risk` but does not appear to assign or pass it into outer meta append calls, so collector retries effectively use default or hand-edited risk values.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-meta-contract-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] Timeout rejection messages differ by lane
- **Reviewer(s)**: dyn-launcher-parity-output.txt
- **Severity**: latent
- **Concern**: Codex and cursor launcher timeout validation messages remain inconsistent, though this is pre-existing and unrelated to stderr-sink wiring.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-launcher-parity-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] NOT_SUBSTANTIVE retries do not forward STDERR_SINK
- **Reviewer(s)**: dyn-launcher-parity-output.txt
- **Severity**: latent
- **Concern**: NOT_SUBSTANTIVE outer-launcher retry paths still do not parse or forward `STDERR_SINK`; only empty-output retry paths were extended.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-launcher-parity-output.txt: Address the concern above.
