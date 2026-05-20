# Review Round 3

- Mode: `diff`
- Accepted findings: 3
- Rejected findings: 11
- Exonerated findings: 2
- Neutral findings: 0

## Accepted Findings

### FINDING_1: **correctness** — [`scripts/collect-agent-results.md:19`](scripts/collect-agent-results.md) — The updated NS-retry contract says that if publishing the validated retry body back to `<base>.txt` fails, the collector leaves `STATUS=NOT_SUBSTANTIVE`, but it does not say that the collector also deletes the `<base>-first-pass.txt` file that was created immediately before publish (`rm` of the first-pass sidecar on the publish-failure path in [`scripts/collect-agent-results.sh:165-167`](scripts/collect-agent-results.sh)). Operators reading only the doc may expect a first-pass sidecar to remain after a publish failure; the implementation and [`scripts/test-collect-agent-results.sh`](scripts/test-collect-agent-results.sh) (`C_NS_FP_PUBLISH_FAIL`) assume it is removed. **Suggested fix:** extend the publish-failure sentence to state that the first-pass sidecar is removed so the tree does not imply a successful publish.
- **Reviewer**: dyn-result-record-consistency-output.txt
- **Concern**: - **correctness** — [`scripts/collect-agent-results.md:19`](scripts/collect-agent-results.md) — The updated NS-retry contract says that if publishing the validated retry body back to `<base>.txt` fails, the collector leaves `STATUS=NOT_SUBSTANTIVE`, but it does not say that the collector also deletes the `<base>-first-pass.txt` file that was created immediately before publish (`rm` of the first-pass sidecar on the publish-failure path in [`scripts/collect-agent-results.sh:165-167`](scripts/collect-agent-results.sh)). Operators reading only the doc may expect a first-pass sidecar to remain after a publish failure; the implementation and [`scripts/test-collect-agent-results.sh`](scripts/test-collect-agent-results.sh) (`C_NS_FP_PUBLISH_FAIL`) assume it is removed. **Suggested fix:** extend the publish-failure sentence to state that the first-pass sidecar is removed so the tree does not imply a successful publish.
- **Suggested revision**: Address the concern above.


### FINDING_7: code-quality: scripts/collect-agent-results.md:24-25 vs scripts/collect-agent-results.sh:148-149
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Doc says stderr warning on first-pass copy failure; code uses larch_err. Operators or triage playbooks expect a warning-level signal but get error-channel severity. Align documentation with larch_err or change severity to match the documented contract.
- **Suggested revision**: Address the concern above.


### FINDING_9: code-quality: scripts/test-collect-agent-results.sh:353-377
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] C_NSR does not assert the original reviewer file contains the published retry body after success. A regression that publishes breadcrumbs but leaves stale prose on the canonical path could slip if only the retry artifact assertion passes. Mirror C_NS_FP_SUCCESS with a grep on OUT_NSR for RETRY_CONTENT.
- **Suggested revision**: Address the concern above.


