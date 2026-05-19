### [rejected] FINDING_12

### FINDING_12: correctness: scripts/lib-external-launcher-common.sh:119-147;scripts/launch-review.sh:522-524;scripts/launch-review.sh:926-928
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] external_is_transient_infra_failure and call sites diverge from the plan: fourth parameter and emptiness check target OUTPUT file, not SIDECAR; no /dev/null sidecar guard from Part A. A reviewer using the written plan as the acceptance contract records a missing/wrong implementation; runtime classification also differs from the plan’s 0-byte sidecar rule whenever that rule would disagree with OUTPUT emptiness. Reconcile: implement the plan’s sidecar-based helper and SIDECAR arguments, or update the plan/issue to the output-file design and adjust tests/docs accordingly.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 NEUTRAL=1

### [rejected] FINDING_16

### FINDING_16: risk-integration: scripts/launch-review.sh:471-534
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Codex sidecar fallback /dev/null leaves auth detection blind while transient retries still run on allowlisted exits with empty output. Host cannot create OUTPUT.sidecar; Codex exits 5/7 with empty output; stderr auth hints are discarded. Launcher now sleeps/backoffs and retries up to MAX_TRANSIENT_RETRIES without ever being able to classify auth, increasing latency vs pre-change single-shot failure. Skip transient retries when SIDECAR is /dev/null or tee stderr to a readable diagnostics file for classification.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 NEUTRAL=1

### [rejected] FINDING_18

### FINDING_18: risk-integration: scripts/test-launch-review.sh (SL-transient cases) vs scripts/lib-external-launcher-common.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No launch-review integration test for codex exit 5 or cursor exit 4 despite allowlist. Regression only on launcher wiring for those exit codes might pass CI until caught elsewhere. Add optional SL-transient cases for exit 5 and 4 analogous to 7 and 8.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 NEUTRAL=1

### [rejected] FINDING_3

### FINDING_3: architecture: scripts/launch-review.sh:478-534,scripts/launch-review.sh:899-947
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] TRANSIENT_ATTEMPT is global across the auth loop without reset. Unusual interleaving of failures might exhaust transient retries early and deny later infra blips within the same outer loop. Document the global budget or reset TRANSIENT_ATTEMPT when AUTH_ATTEMPT increments if product wants per-wave infra retries.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 NEUTRAL=1

### [rejected] FINDING_4

### FINDING_4: code-quality: scripts/launch-review.sh:310-325
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicated cursor auth predicate across transient and auth-retry branches. Slight maintenance cost if one site is edited without the other. Factor a one-line helper or assign _cursor_auth_seen once per iteration.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 NEUTRAL=1

### [rejected] FINDING_5

### FINDING_5: code-quality: scripts/lib-external-launcher-common.sh:387-415;scripts/launch-review.sh:522-524,310-312
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Shipped transient detection uses empty/absent OUTPUT file instead of plan-specified empty sidecar plus /dev/null guard. Plan-vs-code drift may confuse reviewers re-implementing from the issue body only. Document in PR/issue that output-file heuristic replaced sidecar heuristic per run-external-agent sidecar noise.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 NEUTRAL=1

