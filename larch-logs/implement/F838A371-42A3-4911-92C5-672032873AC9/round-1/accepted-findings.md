### FINDING_10: correctness: skills/implement/SKILL.md:1219
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Step 2.3 Q/A redispatch prose still says the launcher derives auto-mode from session artifacts after LARCH_AUTO_MODE and --auto-mode plumbing were removed. Orchestrator or maintainer follows stale Step 2.3 text and assumes session-env still carries an auto-mode signal for redispatch, causing confusion when reconciling argv with run-step2-dispatch.sh behavior. Update the sentence to omit auto-mode and match the actual keys forwarded to step2-implement.sh.
- **Suggested revision**: Address the concern above.


### FINDING_11: risk-integration: scripts/test-implement-structure.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No CI structure test pins that /implement no longer advertises or documents --auto (issue #2497 acceptance is only enforced by prose edits). A future PR could reintroduce --auto in skills/implement/SKILL.md without failing make lint until a human notices. Add a grep-based assertion in scripts/test-implement-structure.sh (or equivalent harness) for the removed flag surfaces.
- **Suggested revision**: Address the concern above.


### FINDING_12: code-quality: skills/fix-issue/scripts/test-fix-issue-bail-detection.md:21
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Contract doc still claims a paired literal assertion with scripts/test-implement-structure.sh after the [--auto if auto_mode] harness row was deleted. Maintainers rely on the doc for cross-file update discipline and chase a nonexistent dual-repo pin. Rewrite or delete the outdated pairing sentence.
- **Suggested revision**: Address the concern above.


### FINDING_13: risk-integration: scripts/test-design-structure.sh:179-181
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Check 6 now uses only one substring pin for Step 3.5 routing, weaker than the prior dual grep that also constrained auto_mode-specific Step 3b forwarding. A partial regression in skills/design/SKILL.md could still contain proceed to Step 3.5 while reintroducing forbidden Step 3a/3b routing text. Add a complementary structural assertion (negative token or second required phrase) so routing invariants stay fail-closed.
- **Suggested revision**: Address the concern above.


### FINDING_6: correctness: skills/implement/SKILL.md:1219
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Step 2.3 Q/A redispatch prose still says launcher derives auto-mode from session artifacts after LARCH_AUTO_MODE removal. Implementer searches for removed session-env key during needs_qa resume debugging. Rewrite clause to only name keys and forwarding that still exist post-change.
- **Suggested revision**: Address the concern above.


### FINDING_7: correctness: skills/design/SKILL.md:368
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Standalone subagent replay claims it matches inline standalone output after dropping conditional architecture-diagram replay. Maintainer mis-equates subagent vs inline user-visible sections around diagrams. Tighten or remove the equivalence sentence to match what the replay block still prints.
- **Suggested revision**: Address the concern above.


### FINDING_8: correctness: scripts/test-design-structure.sh:179-181
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Check 6 lost the second grep pin for Step 3.5 forward motion toward Step 3b; only Step 3 substring is asserted. Future Step 3.5→3b regression can ship while Check 6 still passes. Add a structural pin for Step 3.5→3b that does not rely on removed auto_mode literals.
- **Suggested revision**: Address the concern above.


