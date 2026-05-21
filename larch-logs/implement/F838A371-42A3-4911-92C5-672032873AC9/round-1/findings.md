### FINDING_1: risk-integration: README.md:70-82,169
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] README skill table and /imaq row still document [--auto] and /implement --merge --auto --quick. Operators copy-paste flags from README into Claude Code; /implement or /design rejects unknown --auto or chains wrong vs shipped skills. Align README rows and /imaq equivalent with current SKILL.md argument-hints and alias forwarding.
- **Suggested revision**: Address the concern above.

### FINDING_2: risk-integration: docs/skills.md:31-92
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Canonical SKILL files drop --auto but docs/skills.md still documents [--auto] and wrong /imaq, /alias delegation. Operator copies documented argv; model or CLI rejects --auto or assumes non-interactive suppression still exists. Refresh docs/skills.md rows and prose to match current skills/*/SKILL.md argument-hint and delegation.
- **Suggested revision**: Address the concern above.

### FINDING_3: risk-integration: README.md:69-82
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] README skill matrix still lists [--auto] for /design, /fix-issue, /implement after branch removes those flags from SKILL.md. Same user confusion as stale docs/skills.md but sourced from README landing table. Update HTML table cells to remove [--auto] and align with corrected docs/skills.md.
- **Suggested revision**: Address the concern above.

### FINDING_4: risk-integration: README.md:169
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Aliases table still claims /imaq equals /implement --merge --auto --quick; imaq SKILL.md is --merge --quick only. Operator scripts argv assuming --auto is always present in /imaq expansion. Change row to /implement --merge --quick to match skills/imaq/SKILL.md.
- **Suggested revision**: Address the concern above.

### FINDING_5: risk-integration: docs/workflow-lifecycle.md:40-70
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Workflow bullets and mermaid edges still show --auto forwarders (/imaq, /alias, /create-skill, /compress-skill). Derived automation or mental model encodes wrong argv for wrapper skills. Update bullets and mermaid labels to current forwarder argv without --auto.
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

### FINDING_9: [OUT_OF_SCOPE] code-quality: scripts/check-mid-run-dirty-tree.md:24
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Doc still mentions --auto carve-out though skills no longer expose --auto. File not modified in branch diff; adjacent stale doc only. Update carve-out prose when touching dirty-tree docs for a future change.
- **Suggested revision**: Address the concern above.

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

### FINDING_14: [OUT_OF_SCOPE] risk-integration: docs/workflow-lifecycle.md:40-70
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Topology docs and mermaid still document --auto forwarding for /imaq, /alias, and /create-skill after skills removed --auto. Readers or external automation authors following canonical docs may pass unknown flags or misunderstand delegation edges; fails at invocation rather than a silent security bypass. Update docs/skills.md and docs/workflow-lifecycle.md (and any dependent diagrams) to match current SKILL.md forwarding in a separate doc-sync pass.
- **Suggested revision**: Address the concern above.

### FINDING_15: correctness: README.md:70-82,169
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] README skill table and /imaq alias row still document [--auto] and /implement --merge --auto --quick after skills drop --auto. Operators copy flags from README or trust the /imaq equivalence and pass --auto or expect autonomous checkpoint suppression; invocations can fail as unknown flags or misrepresent /imaq behavior versus skills/imaq/SKILL.md. Align README table rows and the /imaq line with current SKILL.md argument-hint and forwarding (e.g. /imaq -> /implement --merge --quick).
- **Suggested revision**: Address the concern above.

### FINDING_16: correctness: docs/skills.md:31,73-77,81,91
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] docs/skills.md still documents /implement --quick --auto for /alias and [--auto] on /design /fix-issue /implement plus --auto behavior text. Same as README: documentation-driven runs or operator expectations diverge from shipped skills, producing wrong invocations or confusion about which flags exist. Refresh argument lists, delegation bullets, and /design prose to remove --auto and match the linked SKILL.md files.
- **Suggested revision**: Address the concern above.

### FINDING_17: correctness: docs/workflow-lifecycle.md:40-70,132-157
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Delegation topology mermaid labels, narrative bullets, standalone /design bullet, /imaq equivalence, and flags table still reference --auto and old /imaq expansion. Canonical workflow map instructs forwarders and operators to use removed flags and wrong /imaq argv relative to updated alias skills. Update mermaid edge labels, prose, equivalences, and the flags table to the post-removal forwarding graph and remove the stale --auto row.
- **Suggested revision**: Address the concern above.

### FINDING_18: correctness: scripts/check-mid-run-dirty-tree.md:24
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Contract still names a --auto carve-out though --auto is no longer a supported skill flag. Readers infer a live --auto interaction with dirty-tree recovery that the runtime no longer exposes; mild onboarding or audit confusion. Rewrite the carve-out bullet without referencing --auto while preserving the recovery requirement.
- **Suggested revision**: Address the concern above.

