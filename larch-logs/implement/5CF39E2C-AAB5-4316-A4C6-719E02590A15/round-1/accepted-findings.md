### FINDING_1: code-quality: skills/design/scripts/test-assess-plan-round.sh:293-307
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] advance_step3_cursor hand-parses plan-review-round-cursor.txt instead of snapshot-plan-round.sh read-cursor If parse_cursor_file semantics change (malformed file, leading zeros, stderr warnings) the harness can still pass while Step 3 entry and assess-plan-round.sh diverge Implement advance via read-cursor + write-cursor matching skills/design/SKILL.md:1026-1039
- **Suggested revision**: Address the concern above.


### FINDING_12: risk-integration: scripts/test-design-structure.sh:840-849
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Plan acceptance requires six Step 3.6 skip-breadcrumb literals byte-for-byte in SKILL.md and approval-gates.md but structure tests only pin passive-summary and partial Step 3.5 bypass text. An edit rephrases skip breadcrumbs in one file only; make lint and test-design-structure.sh pass while acceptance fails. Add paired contains pins (or a cross-file equality check) for all six ⏩ 3.6 skip breadcrumb literals in both files.
- **Suggested revision**: Address the concern above.


### FINDING_13: correctness: skills/design/SKILL.md:955,1128
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Cap routing prose now goes Step 3b → Step 4 → Gate C while the pinned cap warning still says returning to Gate C. test-design-structure.sh:86 Pinned breadcrumb text can contradict normative routing without any test failure, confusing operators on cap-reached runs. Update breadcrumb and pin together for routing-consistent wording, or add an assertion linking cap prose to the warning text.
- **Suggested revision**: Address the concern above.


### FINDING_14: risk-integration: skills/design/scripts/test-assess-plan-round.sh:293-307
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Two-entry cursor helper reads plan-review-round-cursor.txt directly instead of snapshot-plan-round.sh read-cursor/write-cursor used in SKILL.md Step 3 entry. Future read-cursor validation or format changes break production while the integration case still passes. Reimplement advance_step3_cursor using read-cursor and write-cursor like SKILL.md:1026-1038.
- **Suggested revision**: Address the concern above.


### FINDING_15: risk-integration: scripts/test-design-structure.sh:846-849
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Step 3.5 bypass pins differ between SKILL.md and approval-gates.md and omit skipped-cap-reached from the approval pin. Drift in bypass status lists between files passes CI while Step 3.5 entry exceptions diverge. Pin the identical full Gate-B-bypass status list in both files including skipped-cap-reached if normative.
- **Suggested revision**: Address the concern above.


### FINDING_2: code-quality: scripts/test-design-structure.sh:843-849
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Six Step 3.6 skip breadcrumbs are not structurally pinned across SKILL.md and approval-gates.md An edit to one skip breadcrumb in SKILL.md can desync approval-gates.md:92 without failing CI until manual review Add contains pins for each ⏩ 3.6 skip literal (or pin the consolidated approval-gates sentence plus SKILL mirrors)
- **Suggested revision**: Address the concern above.


### FINDING_22: correctness: skills/design/SKILL.md:955
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Cap-hit breadcrumb still says returning to Gate C while routing is Step 3b → Step 4 → Gate C Operator or log triage assumes Gate C is immediate and may skip Step 3b/4 or mis-order recovery Clarify the live printf/normative cap sentence in the same change as routing (or update pin at scripts/test-design-structure.sh:86)
- **Suggested revision**: Address the concern above.


### FINDING_23: risk-integration: scripts/test-design-structure.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] No structural pins for the six Step 3.6 skip-breadcrumb literals across SKILL.md and approval-gates.md Future edit drops or typos a skip breadcrumb in one file while CI stays green Add paired contains pins for all six ⏩ 3.6 skip literals in test-design-structure.sh
- **Suggested revision**: Address the concern above.


### FINDING_24: correctness: skills/design/scripts/test-assess-plan-round.sh:293-307
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] advance_step3_cursor reads cursor file directly instead of read-cursor Harness passes while production mishandles malformed cursor files Use snapshot-plan-round.sh read-cursor in the helper and assert ROUND_CURSOR output
- **Suggested revision**: Address the concern above.


### FINDING_27: code-quality: scripts/test-design-structure.sh:846
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Step 3.5 bypass pin only checks cap-reached prefix panel-failed or tally-error could be removed from blockquote without CI failure Pin full Gate-B-bypass list or each bypass status token
- **Suggested revision**: Address the concern above.


### FINDING_29: correctness: scripts/test-design-structure.sh:846
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] SKILL.md Step 3.5 Gate-B-bypass structural pin only matches a prefix, not the full short-circuit set required by the plan. An agent can remove panel-failed, tally-error, or other bypass statuses from skills/design/SKILL.md:1134 while scripts/test-design-structure.sh still passes; Step 3.5/3.6 bypass prose regresses without CI failure. Add a contains pin for the full Gate-B-bypass enumeration in SKILL.md (mirror approval-gates.md:849), including panel-failed and skipped-cap-reached if normative.
- **Suggested revision**: Address the concern above.


### FINDING_4: code-quality: skills/design/SKILL.md:1115
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] plan-size-trigger|plan-validator-defects prose says before Gate B/3b while also skipping Gate B Operators may think Gate B still runs before the 2b.5 handler completes Say run Step 2b.5 then short-circuit to Step 3b; skip Gate B and Step 3.6
- **Suggested revision**: Address the concern above.


### FINDING_7: correctness: skills/design/scripts/test-assess-plan-round.sh:293-307
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Cursor helper reads plan-review-round-cursor.txt directly instead of read-cursor If read-cursor normalization diverges from raw file parsing, harness could pass while Step 3 entry mis-advances cursor Call snapshot-plan-round.sh read-cursor and parse ROUND_CURSOR= like SKILL.md does
- **Suggested revision**: Address the concern above.


### FINDING_8: correctness: scripts/test-design-structure.sh:846
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Step 3.5 bypass pin only checks cap-reached prefix Removing panel-failed or tally-error from SKILL.md:1134 blockquote would not fail structure test Pin the full Gate-B-bypass short-circuit list string from SKILL.md:1134
- **Suggested revision**: Address the concern above.


