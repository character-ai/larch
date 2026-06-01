### FINDING_13: risk-integration: scripts/test-ship-pr.sh:2155,2212
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Stale 600s timeout comments on cases that use recovery waterfall Maintainers may edit the wrong code path when fixing timeout regressions Reword comments to recovery-waterfall / 1800s to match current stubs
- **Suggested revision**: Address the concern above.


### FINDING_24: correctness: scripts/test-implement-step2-routing.sh:47
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] The assert_not_contains guard forbids Codex → Cursor → Claude in SKILL.md but the assertion label says old waterfall order. A maintainer retitling routing may think the forbidden string is the retired order and weaken or remove the guard while syncing docs. Rename the label to state that SKILL.md must not duplicate the script-side waterfall arrow order (e.g. script-side waterfall order not duplicated in SKILL.md).
- **Suggested revision**: Address the concern above.


### FINDING_3: code-quality: docs/installation-and-setup.md:119-147
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Intro still claims API-key-only recipes above new subscription dual-auth content. Readers may think subscription aliases contradict the section header. Reword the intro to cover both API-key and subscription setup for Claude.
- **Suggested revision**: Address the concern above.


### FINDING_4: code-quality: scripts/launch-cursor-ci.md:191-192
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] launch-codex-ci.md not synced on first-fixer / tier-order prose. Maintainers reading only the Codex launcher doc miss rotated-first-tier bail semantics. Mirror launch-cursor-ci.md first-tier language in launch-codex-ci.md per Edit In Sync.
- **Suggested revision**: Address the concern above.


