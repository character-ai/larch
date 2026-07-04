# Review Round 1

- Mode: `diff`
- 2 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: correctness: Makefile:37-37
- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: [important] The new bg-wait writer-parity lint is only wired into local make lint, not the automated lint-only path used by CI and scoped pre-commit. If run-step-checks.sh drops CLONE_PATH= again, make lint-only in CI and python/cli.py checks run-relevant still pass, so the regression ships until a developer runs the local aggregate manually. Register the parity lint in the pre-commit/CI path that backs make lint-only, or otherwise invoke it from CI, as is done for lint-bg-wait-coverage.
- **Suggested revision**: Address the concern above.


### FINDING_4: risk-integration: Makefile:37-38
- **Reviewer**: codex-specialist-edge-cases-output.txt
- **Concern**: [important] The new bg-wait writer parity lint only runs in local make lint and never in the repo's automated lint-only path. CI and ordinary pre-commit still skip the new check, so a future omitted CLONE_PATH stamp can merge without the regression guard ever executing. Add a pre-commit hook entry for lint-bg-wait-writer-parity (mirroring lint-bg-wait-coverage) or change CI to run make lint instead of make lint-only.
- **Suggested revision**: Address the concern above.


