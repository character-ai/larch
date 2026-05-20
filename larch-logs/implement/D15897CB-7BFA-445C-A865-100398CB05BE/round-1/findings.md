### FINDING_1: **risk-integration** `skills/implement/scripts/generate-code-flow-diagram.sh:40-41` — Step 7a’s runtime token/timing marks still emit `Step 7a — code flow diagram`, so a run will show `7a: diagrams` in the breadcrumb but keep attributing the same step window to the old partial name in token/timing reports. That preserves the operator-facing inconsistency this rename is meant to remove, and `scripts/test-implement-structure.sh:202-203` currently pins the stale label. **Suggested fix:** Rename both ledger marks to `Step 7a — diagrams`, then update `scripts/test-implement-structure.sh:202-203` and `skills/implement/scripts/generate-code-flow-diagram.md:6` to match.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: - **risk-integration** `skills/implement/scripts/generate-code-flow-diagram.sh:40-41` — Step 7a’s runtime token/timing marks still emit `Step 7a — code flow diagram`, so a run will show `7a: diagrams` in the breadcrumb but keep attributing the same step window to the old partial name in token/timing reports. That preserves the operator-facing inconsistency this rename is meant to remove, and `scripts/test-implement-structure.sh:202-203` currently pins the stale label. **Suggested fix:** Rename both ledger marks to `Step 7a — diagrams`, then update `scripts/test-implement-structure.sh:202-203` and `skills/implement/scripts/generate-code-flow-diagram.md:6` to match.
- **Suggested revision**: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] architecture: larch-logs/implement (historical runs)
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Old transcripts and reports still show legacy 7a code flow strings. None for current skill behavior; noise only if someone mistakes archives for live contracts. None required; exclude larch-logs when verifying string migration.
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] architecture: larch-logs/implement historical runs
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Old transcripts and reports still show legacy 7a code flow strings. No impact on current skill behavior; confusion only if archives are treated as live contracts. Exclude larch-logs when verifying string migration.
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] architecture: skills/implement/SKILL.md:10,1330,1629
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Overview prose still says code flow diagram in lifecycle summaries. Pre-existing broader wording vs step 7a rename scope. Optional doc-only alignment later.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] architecture: skills/implement/scripts/generate-code-flow-diagram.sh:40-41
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Token/timing ledger marks still say Step 7a — code flow diagram. Pre-existing; may feel inconsistent with diagrams breadcrumb. Optional rename of ledger strings in a separate change.
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] code-quality: CHANGELOG.md
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] CHANGELOG not updated in diff for operator-visible breadcrumb rename. Consumers relying only on CHANGELOG may miss the rename unless noted elsewhere. Add a release note when cutting the release if convention expects it.
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] code-quality: CHANGELOG.md (unchanged in diff)
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] No changelog bullet for operator visible breadcrumb rename. Consumers relying only on CHANGELOG may miss the rename unless noted elsewhere. Add a note when cutting the release if project convention expects it.
- **Suggested revision**: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] code-quality: feature_description (external prompt)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Prompt line 16 bullet implies 7a.r TSV rename to diagrams. Misleading requirement text only; implementation matches the in-repo plan. None for this PR; align future issue text with TSV vs macro short-name distinction.
- **Suggested revision**: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] code-quality: larch-logs/implement/**/session-transcript.jsonl
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] various Historical transcripts retain old breadcrumbs None for this PR No change
- **Suggested revision**: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] code-quality: skills/implement/SKILL.md:10,1330
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Summary prose still says code flow diagram Pre existing copy Align later if desired
- **Suggested revision**: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] code-quality: skills/implement/scripts/generate-code-flow-diagram.sh:40-41
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Ledger marks unchanged Step 7a code flow diagram Telemetry label narrower than new breadcrumb name Optional rename for parity not required for this PR
- **Suggested revision**: Address the concern above.

### FINDING_12: architecture: skills/implement/SKILL.md:1535
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Step 7a anchor comment still says Code Flow Diagram while breadcrumbs/registry say diagrams. Maintainers or tooling that treat anchor text as the canonical step label may assume the step is only code-flow. Rename anchor and test harness grep in a follow-up if single vocabulary is required.
- **Suggested revision**: Address the concern above.

### FINDING_13: code-quality: larch-logs/implement/D15897CB-7BFA-445C-A865-100398CB05BE/plan-goals-test.md:18-28
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Flushed plan file embeds old 7a: code flow literals. Verification grep for zero 7a: code flow hits fails even after a clean rename of sources. Exclude larch-logs from grep or redact before/after examples in flushed artifacts.
- **Suggested revision**: Address the concern above.

### FINDING_14: code-quality: larch-logs/implement/D15897CB-7BFA-445C-A865-100398CB05BE/plan-goals-test.md:18-28
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] New flushed plan embeds literal 7a code flow strings from the pre change plan Repo wide grep for verification still matches committed plan text Exclude larch logs from grep or accept archival literals
- **Suggested revision**: Address the concern above.

### FINDING_15: code-quality: skills/implement/SKILL.md:1629
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Post-7a.r Step 8 guardrail prose still says only code flow diagram while step breadcrumbs use diagrams Operators following strict vocabulary see mixed labels in adjacent lines Reword to Step 7a or diagrams step scope
- **Suggested revision**: Address the concern above.

### FINDING_16: correctness: larch-logs/implement/D15897CB-7BFA-445C-A865-100398CB05BE/plan-goals-test.md:18-28
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Committed plan-goals excerpt repeats literal 7a: code flow strings used as before examples Test plan in the same run asks for repo grep with zero matches; whole-repo grep still hits this log file Scope grep to non-log paths or document excluding larch-logs from that acceptance check
- **Suggested revision**: Address the concern above.

### FINDING_17: risk-integration: larch-logs/implement/D15897CB-7BFA-445C-A865-100398CB05BE/plan-goals-test.md
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Archived plan suggests grep for 7a code flow with zero matches but larch-logs retains that substring. Authors following the archived verification literally get endless false positives. Scope future greps to skill script dirs or exclude larch-logs from verification.
- **Suggested revision**: Address the concern above.

### FINDING_18: risk-integration: larch-logs/implement/D15897CB-7BFA-445C-A865-100398CB05BE/plan-goals-test.md:18-28
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] New flushed plan artifact embeds old 7a breadcrumb literals in narrative. A strict repo-root rg for 7a: code flow no longer yields zero after merge, which can falsely suggest incomplete migration. Scope verification to skills/scripts/docs or document that larch-logs may retain historical literals.
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: skills/implement/SKILL.md:1629
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Post-7a.r handoff prose still says the code flow diagram is not the end of the run while the step is branded diagrams. Operators see diagrams in the step banner then read singular code flow diagram at the handoff, nudging the old mental model at a critical transition before Step 8. Reword to neutral step or diagrams wording that matches the broadened step scope.
- **Suggested revision**: Address the concern above.

### FINDING_20: risk-integration: skills/implement/scripts/generate-code-flow-diagram.md:6 and scripts/test-implement-structure.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Token timing marks stay Step 7a code flow diagram while breadcrumbs use diagrams. Joining or grepping telemetry by expected step label diverges from live breadcrumbs more than before the rename. Optional follow-up align timing mark strings and structure-test pins with diagrams vocabulary.
- **Suggested revision**: Address the concern above.

### FINDING_21: risk-integration: skills/implement/scripts/generate-code-flow-diagram.sh:40-41
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Timing/token marks still label Step 7a as code flow diagram while breadcrumbs use diagrams. Operators correlating timing-report.json or ledger output with new 7a: diagrams lines may perceive a second distinct step. Optional follow-up to rename marks and update test-implement-structure pin if confusion arises.
- **Suggested revision**: Address the concern above.

### FINDING_22: risk-integration: skills/implement/scripts/step-name-registry.tsv:374;skills/implement/SKILL.md:268-334
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Breadcrumb and rebase macro short-name strings changed from code flow to diagrams. External monitors keyed on old literals miss events or mis-classify runs after upgrade. Update external matchers or document the breaking string change.
- **Suggested revision**: Address the concern above.

