### FINDING_10: risk-integration: scripts/relevant-checks.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] relevant-checks does not map lib-external-launcher-common.sh or run-external-agent.sh changes to their harness targets. After a resolver-only edit, running only relevant-checks can pass while test-lib-external-launcher-common.sh and test-run-external-agent.sh fail on make test-harnesses-8/6. Add relevant-checks cases for lib-external-launcher-common.sh, run-external-agent.sh, and paired test-* harnesses, or require full make lint in PR checklist for this surface.
- **Suggested revision**: Address the concern above.


### FINDING_11: risk-integration: scripts/test-lib-external-launcher-common.sh:497-499
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No test pins non-numeric/empty env coercing to resolver default 30. Documented edge case (garbage env) can regress without failing harnesses that only test unset env, explicit 0, and positive override. Add assert_resolver_timeout cases for env abc and/or empty string expecting 30.
- **Suggested revision**: Address the concern above.


### FINDING_2: code-quality: scripts/lib-external-launcher-common.md:7
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] "optional" contradicts default-on gate wording Readers infer gate is off unless configured Rename to "pre-launch health gate" or "enabled by default; opt out with 0"
- **Suggested revision**: Address the concern above.


### FINDING_21: architecture: scripts/lib-external-launcher-common.sh:40-78
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Non-numeric env values now fall through to the 30s default instead of disabling the gate. Operator sets LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT=30s or leaves a typo; gate runs and may fast-fail launches that previously skipped the probe. Document typo→on behavior; add resolver test pinning garbage env → 30.
- **Suggested revision**: Address the concern above.


### FINDING_3: code-quality: scripts/run-external-agent.md:120-122
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Test harness section omits LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT=0 guidance for offline stubs New harnesses may hit real check-reviewers.sh and flake under default-on Document export LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT=0 unless testing the gate
- **Suggested revision**: Address the concern above.


