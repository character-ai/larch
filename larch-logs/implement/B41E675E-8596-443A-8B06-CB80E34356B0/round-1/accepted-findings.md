### FINDING_1: Missing CLAUDE_PLUGIN_ROOT-unset fallback regressions
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The Item B harnesses do not exercise production behavior when `CLAUDE_PLUGIN_ROOT` is unset, so a broken `PLUGIN_ROOT` / `SCRIPT_DIR` fallback or failed `lib-codex-launcher-common.sh` source could regress without CI catching missing Codex telemetry or token-ledger rows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_10: run-external-agent progress can pollute events JSONL
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Wrapped Codex sites redirect `run-external-agent` progress stdout into `*.events.jsonl` alongside Codex JSONL, so long runs can interleave non-JSON diagnostics into files expected to be strict JSONL.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_2: Missing direct round_artifact_included probes
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `scripts/test-larch-log.sh` only covers `write-round` behavior, not direct `round_artifact_included` return codes required by acceptance #3, so an allowlist typo for `scout-archetype-yield.tsv` or `*.events.jsonl` could be masked by integration staging behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_3: Breadcrumb assertions no longer fail when breadcrumbs disappear
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Review-and-fix breadcrumb tests were weakened after the FD 3 harness change, so expected user-visible breadcrumbs can disappear on compose-fail, all-fail, and dispatch paths without failing the relevant lint shards.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_4: Summary-derivation warning breadcrumb is no longer asserted
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The compose-fail path no longer asserts the summary-derivation warning breadcrumb, reducing coverage for the operator-visible signal emitted when `compose-review-findings` fails during summary derivation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_6: Telemetry sidecar path is not the stderr sink
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `lint-fix-loop.sh` and `review-and-fix.sh` pass a `codex.sidecar` path to telemetry helpers while Codex stderr goes to `wrapper.log`, leaving diagnostics and future stderr-based classification pointed at the wrong file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_8: Negotiation test does not pin sidecar stream separation
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-run-negotiation-round.sh` does not assert that the sidecar is free of `token_usage` JSONL event bleed, so a redirect regression could violate the stream-split contract while CI still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


