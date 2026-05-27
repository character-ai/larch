### FINDING_1: Missing CLAUDE_PLUGIN_ROOT-unset fallback regressions
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The Item B harnesses do not exercise production behavior when `CLAUDE_PLUGIN_ROOT` is unset, so a broken `PLUGIN_ROOT` / `SCRIPT_DIR` fallback or failed `lib-codex-launcher-common.sh` source could regress without CI catching missing Codex telemetry or token-ledger rows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

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

### FINDING_5: Duplicated Codex telemetry block can drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Three scripts carry mirrored Codex telemetry logic, so future edits to JSON parsing, redirects, or bucket labels require coordinated manual changes and can drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: Telemetry sidecar path is not the stderr sink
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `lint-fix-loop.sh` and `review-and-fix.sh` pass a `codex.sidecar` path to telemetry helpers while Codex stderr goes to `wrapper.log`, leaving diagnostics and future stderr-based classification pointed at the wrong file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_7: Inconsistent invalid-value handling in get-issue-state
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `scripts/get-issue-state.sh` handles missing, flag-like, and empty `--issue` / `--repo` values with inconsistent error shapes and formatting, which makes caller parsing and review diffs less consistent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_8: Negotiation test does not pin sidecar stream separation
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-run-negotiation-round.sh` does not assert that the sidecar is free of `token_usage` JSONL event bleed, so a redirect regression could violate the stream-split contract while CI still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_9: Negotiation harness serial-lock delay adds unnecessary runtime
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The success-path serial lock delay in `scripts/test-run-negotiation-round.sh` increased from 1s to 5s, adding roughly four seconds to every shard invocation without an evident production rationale or documented flake fix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_10: run-external-agent progress can pollute events JSONL
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Wrapped Codex sites redirect `run-external-agent` progress stdout into `*.events.jsonl` alongside Codex JSONL, so long runs can interleave non-JSON diagnostics into files expected to be strict JSONL.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] Duplicate Codex failure exit paths
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/run-negotiation-round.sh` has redundant Codex failure exit handling through both an inner case and tail `EXIT_CODE`; this is pre-existing cleanup outside the reviewed feature scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] Symlink edge case in SCRIPT_DIR resolution
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/run-negotiation-round.sh` computes `SCRIPT_DIR` without `pwd -P` while `PLUGIN_ROOT` uses `pwd -P`, leaving a symlinked-script path edge case that was not introduced by this feature.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] Breadcrumb assertions weakened in quiet mode
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: The review-and-fix quiet-mode breadcrumb assertions can always pass when breadcrumbs are absent, creating possible CI blind spots for unrelated UX regressions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] Published model-text outputs remain broad
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `scripts/larch-log.sh:95` still publishes pre-existing `*-output.txt` negotiation and reviewer outputs with full model text; Item B does not widen that surface because only local `*.events.jsonl` siblings were added.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] coder-codex.wrapper.log remains allowlisted
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `scripts/larch-log.sh:89` still allowlists `coder-codex.wrapper.log`, whose Codex stderr may contain sensitive diagnostics; this PR improves stream separation but does not add stderr redaction beyond the existing publication pipeline.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] Launcher events JSONL has same progress-line risk
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Existing launcher sites already redirect `run-external-agent` stdout to `*.events.jsonl`, creating the same possible non-JSON progress-line interleaving risk outside this feature’s changed wrapped sites.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] Allowlist regression coverage uses integration only
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-larch-log.sh` relies on `write-round` integration rather than direct `round_artifact_included` probes; this is weaker than the acceptance wording if staging changes without touching the include helper.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
