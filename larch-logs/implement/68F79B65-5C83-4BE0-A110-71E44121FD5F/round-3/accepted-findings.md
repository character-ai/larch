### FINDING_1: code-quality: skills/design/scripts/plan-review-loop.sh:100-102
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] write_empty_review_artifacts duplicates the 21-column TSV header literal instead of calling emit_findings_classification_header despite sourcing lib-findings-classification.sh Schema changes require editing multiple copies (loop, lib, tests) and headers can drift silently Call emit_findings_classification_header > "$_fc_out" and drop the duplicated printf line
- **Suggested revision**: Address the concern above.


### FINDING_11: risk-integration: skills/design/scripts/test-findings-classification.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Plan harness case 15 (voter-sourced cell tab/newline sanitization via tr) is not implemented; only ballot finding_reviewers tab normalization is tested. A voter file containing embedded tab or newline inside a rating or tool field could corrupt TSV columns or concatenate tokens; CI would still pass. Add a fixture with tab/newline inside voter-sourced fields and assert TSV cells use single-space replacement and 21-field rows remain valid.
- **Suggested revision**: Address the concern above.


### FINDING_16: correctness: skills/design/SKILL.md:758
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Step 3 instructs re-run with sole --voter MainAgent but tally never processes those votes for acceptance. After main-agent writes YES votes to voter-main-agent.txt and re-runs per SKILL, tally exits early with main-agent-vote-required again and accepted-plan-findings.md stays empty; legacy --voter-files still accepts. Add MainAgent adjudication tally mode with eligible_count=1 and empty vN columns, or keep legacy --voter-files in SKILL until implemented; harness accepted-plan-findings after re-run.
- **Suggested revision**: Address the concern above.


### FINDING_17: risk-integration: skills/design/scripts/tally-plan-review.sh:347-354
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Sole-MainAgent TSV rows always get voting_result=rejected via classify_result(0,0,0,0). Forensic TSV shows rejected for all findings while voter-main-agent.txt may contain YES; analytics misread 0-judge rounds as panel rejection. Use distinct voting_result for 0-judge rows or derive from MainAgent votes when sole voter; document in tally-plan-review.md.
- **Suggested revision**: Address the concern above.


### FINDING_18: architecture: skills/design/scripts/plan-review-loop.sh:100-102
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] write_empty_review_artifacts duplicates TSV header literal instead of emit_findings_classification_header. Future column change updates lib helper and tally but leaves zero-findings/panel-failure headers wrong in published logs. Call emit_findings_classification_header for all header-only TSV writes.
- **Suggested revision**: Address the concern above.


### FINDING_19: correctness: skills/design/scripts/tally-plan-review.sh:132-177
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] --voter slot assignment uses basename/tool heuristics not argv order. Direct --voter Cursor then Claude invocations mis-order v1/v3 relative to dispatch order documentation. Assign vN by --voter enumeration index in --voter mode; reserve heuristics for --voter-files only.
- **Suggested revision**: Address the concern above.


### FINDING_21: correctness: docs/run-logs.md:440-443
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] run-logs claims v1/v2/v3 follow --voter argv order while tally uses canonical slot/path heuristics Analytics or operators reading run-logs will misinterpret middle-slot-empty TSVs (e.g. expect Cursor in v2 when only Claude+Cursor ran) Align run-logs slot semantics with tally-plan-review.md; remove argv-order claim
- **Suggested revision**: Address the concern above.


### FINDING_22: correctness: scripts/test-render-voter-prompt.sh:1746-1807
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Missing plan-required check that sentinel directives exclude rating prose Axis instructions could leak into Verify silently / Do NOT modify blocks without failing CI Grep rendered output: sentinel paragraphs must not contain CORRECTNESS=/SEVERITY=/QUALITY=/UNCERTAIN=
- **Suggested revision**: Address the concern above.


### FINDING_23: correctness: skills/design/scripts/plan-review-loop.sh:90-103
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] write_empty_review_artifacts inlines header instead of shared tally/header helper Header string can drift from tally/publish on future schema edits Use emit_findings_classification_header or tally with empty ballot
- **Suggested revision**: Address the concern above.


### FINDING_24: correctness: skills/design/scripts/test-tally-plan-review.sh:147-153
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Plan-listed tally TSV cases largely only in test-findings-classification; zero-voter path checks header only not rejected rows Zero-voter regression might ship header-only TSV without per-finding rejected rows Add rejected-row assertions or document test-findings-classification as sole authority
- **Suggested revision**: Address the concern above.


### FINDING_3: code-quality: skills/design/scripts/tally-plan-review.sh:132-197
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] --voter slot assignment uses position_for_voter heuristics not argv order Direct tally with non-canonical path order mis-assigns vN columns vs plan dispatch-order wording For --voter mode use explicit slot index; reserve heuristics for --voter-files only
- **Suggested revision**: Address the concern above.


### FINDING_4: code-quality: skills/design/scripts/test-findings-classification.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Plan case 18 waterfall (Claude in slot 2 on codex-vote-output path) not covered; slot-2-looking-path only tests basename rules Production waterfall identity from VOTER_N_TOOL could regress without a failing harness Add --voter Claude:.../codex-vote-output.txt fixture asserting v2_tool=Claude
- **Suggested revision**: Address the concern above.


### FINDING_6: correctness: skills/design/scripts/tally-plan-review.sh:267-354
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Sole --voter MainAgent skips vote tallying; accepted/rejected/oos stay empty despite valid voter-main-agent.txt. 0-judge panel; operator writes FINDING_1: YES to voter-main-agent.txt; re-run with --voter MainAgent:path; status stays main-agent-vote-required and no findings accepted (main used --voter-files with eligible_count=1). When MainAgent is sole voter use MAIN_AGENT_VOTER for artifact tally (eligible_count=1) while keeping TSV vN empty per plan if required; add harness for post-adjudication re-run.
- **Suggested revision**: Address the concern above.


### FINDING_7: correctness: skills/design/scripts/tally-plan-review.sh:132-197
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] --voter slot assignment uses basename/tool heuristics not argv dispatch order per plan. Custom --voter paths without slot markers can land in wrong vN columns or hit duplicate position errors despite canonical dispatch order from plan-review-loop. Assign v1/v2/v3 by --voter argument order; reserve position_for_voter for legacy --voter-files only.
- **Suggested revision**: Address the concern above.


### FINDING_8: correctness: skills/design/scripts/plan-review-loop.sh:90-102
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] write_empty_review_artifacts duplicates TSV header literal instead of emit_findings_classification_header. Future header schema change updates lib-findings-classification.sh but zero-findings/panel-failed paths emit a different header line. Call emit_findings_classification_header or delegate empty-ballot tally to tally-plan-review.sh.
- **Suggested revision**: Address the concern above.


### FINDING_9: correctness: skills/design/scripts/tally-plan-review.sh:79-81
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Argv contract errors exit 2; plan specifies exit 1. Callers grepping for exit 1 on mutex/invalid slot miss failures. Align exit code with plan and test-tally-plan-review.sh or update contract docs.
- **Suggested revision**: Address the concern above.


