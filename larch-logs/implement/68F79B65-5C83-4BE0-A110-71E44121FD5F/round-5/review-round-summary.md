# Review Round 5

- Mode: `diff`
- 11 accepted, 11 rejected (8 exonerated)

## Accepted Findings

### FINDING_1: correctness: skills/design/scripts/tally-plan-review.sh:237
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] --voter uses tool-canonical positions (Claude→v1) not VOTER_N slot index. Codex waterfall emits two --voter Claude:... args; second assign_voter hits duplicate voter position 1 and tally aborts; no findings-classification.tsv on degraded panels. Assign by slot index 1/2/3 from dispatch; use SLOT only for vN_tool (extend argv or pass position explicitly).
- **Suggested revision**: Address the concern above.


### FINDING_14: security: skills/design/scripts/tally-plan-review.sh:317-320
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] sanitize_tsv_cell does not neutralize spreadsheet formula prefixes in free-text finding_reviewers cells Analyst opens published findings-classification.tsv in Excel; a reviewer label like =HYPERLINK("https://evil.example") in finding_reviewers may execute or prompt as a formula Prefix/escape cells starting with = + - @ before TSV write; add harness fixture
- **Suggested revision**: Address the concern above.


### FINDING_15: architecture: skills/design/scripts/tally-plan-review.sh:220-238
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] --voter maps Claude/Codex/Cursor labels to fixed v1/v2/v3 columns, so two Claude voters (slot 1 + slot 2 waterfall) collide on position 1. Codex unavailable with Claude slot-1 OK and Claude slot-2 fallback: loop emits two --voter Claude:... args; tally exits duplicate voter position 1 and forensic TSV is missing. Pass canonical slot index from plan-review-loop (e.g. --voter 2:Claude:path) and assign_voter by index; keep vN_tool from runtime tool label.
- **Suggested revision**: Address the concern above.


### FINDING_16: correctness: skills/design/scripts/test-findings-classification.sh:1-386
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Acceptance case 18 / test-tally case 11 (v2_tool=Claude waterfall) are not implemented; doc claims waterfall coverage. CI passes while production waterfall dual-Claude tally failure (finding 1) has no regression guard. Add harness: slot-2 Claude fallback with slot-1 populated; assert v2_tool=Claude and v2 rating columns populated.
- **Suggested revision**: Address the concern above.


### FINDING_17: risk-integration: skills/design/scripts/tally-plan-review.sh:103-288
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Tally abort paths skip write_findings_classification, so a prior round TSV can remain on disk. Re-run after transient voter read error leaves stale findings-classification.tsv that publish may stage. On abort after out path known: truncate to header-only, unlink target, or write explicit degraded rows.
- **Suggested revision**: Address the concern above.


### FINDING_2: code-quality: skills/design/scripts/test-findings-classification.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Missing plan case 18; harness asserts duplicate Claude --voter must fail. Waterfall regression never runs; duplicate-Claude test codifies the bug as intended behavior. Add waterfall fixture expecting v2_tool=Claude with two Claude paths; fix tally first.
- **Suggested revision**: Address the concern above.


### FINDING_20: correctness: skills/design/scripts/tally-plan-review.sh:237
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] --voter uses tool-name canonical map instead of dispatch slot index Waterfall emits --voter Claude for slots 1 and 2; second Claude collides on v1 and tally errors, so v2_tool never records Claude substitution Map --voter by VOTER_N slot index (1/2/3); keep vN_tool from declared SLOT
- **Suggested revision**: Address the concern above.


### FINDING_21: correctness: skills/design/scripts/test-findings-classification.md:22-23
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Harness doc claims waterfall v2_tool=Claude case but no test implements it Acceptance criterion 18 and forensic analytics for substituted judges lack regression lock Add three-voter fixture with Claude in slot 2; assert v2_tool and v2 ratings
- **Suggested revision**: Address the concern above.


### FINDING_7: correctness: skills/design/scripts/tally-plan-review.sh:237
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] --voter uses canonical_position_for_slot(tool) instead of panel slot index 1/2/3. Codex unavailable; slot 2 Claude fallback; loop emits two --voter Claude:...; tally exits duplicate voter position 1; no findings-classification.tsv. Pass explicit slot index from plan-review-loop; assign_voter uses index for vN columns and SLOT label for vN_tool.
- **Suggested revision**: Address the concern above.


### FINDING_8: risk-integration: skills/design/scripts/test-findings-classification.sh (missing case 18)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Plan-required waterfall harness case 18 (v2_tool=Claude with populated v2 ratings) is absent. When Codex falls back to Claude while VOTER_1 is also Claude, tally maps both --voter Claude args to position 1 and errors or mis-attributes slot 2; analytics cannot record substitution in v2. Add case 18 and change explicit --voter placement to preserve slot index (not tool-name→v1/v2/v3 only).
- **Suggested revision**: Address the concern above.


### FINDING_9: risk-integration: scripts/test-design-log-publish.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Plan publish regression list includes rejecting unexpected files under plan-review/; harness has no round-1/unexpected.txt fixture. A future allowlist widening could stage arbitrary plan-review files without CI failure. Add round-1/findings-classification.tsv plus round-1/unexpected.txt; assert PUBLISH_OK=false.
- **Suggested revision**: Address the concern above.


