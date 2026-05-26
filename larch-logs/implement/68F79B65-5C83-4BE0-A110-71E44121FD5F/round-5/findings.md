### FINDING_1: correctness: skills/design/scripts/tally-plan-review.sh:237
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] --voter uses tool-canonical positions (Claude→v1) not VOTER_N slot index. Codex waterfall emits two --voter Claude:... args; second assign_voter hits duplicate voter position 1 and tally aborts; no findings-classification.tsv on degraded panels. Assign by slot index 1/2/3 from dispatch; use SLOT only for vN_tool (extend argv or pass position explicitly).
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: skills/design/scripts/test-findings-classification.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Missing plan case 18; harness asserts duplicate Claude --voter must fail. Waterfall regression never runs; duplicate-Claude test codifies the bug as intended behavior. Add waterfall fixture expecting v2_tool=Claude with two Claude paths; fix tally first.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: skills/design/scripts/tally-plan-review.sh:116-248
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Three overlapping slot-placement helpers for legacy vs explicit --voter. Future slot-rule changes must be edited in multiple places; easy to re-break waterfall or middle-slot semantics. Collapse to one assign_voter_at_position after slot-index fix.
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: skills/design/scripts/tally-plan-review.sh:326-360
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Redundant vote_for_id and parser subprocesses per TSV cell. Large ballots multiply shell/awk work without functional benefit. Cache tally_votes_for_id outputs and reuse for TSV columns.
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: scripts/parse-judge-vote-and-rating.sh:83-87
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Four awk invocations to split one parser TSV line. Small per-call overhead; unnecessary complexity vs IFS read. Split the tab line once in Bash after awk.
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: skills/design/scripts/tally-plan-review.sh:79-81
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Contract violation exits use 2; plan says 1. Callers grepping exit 1 only may mis-handle mutex errors. Align exit code with plan or document 2 in tally-plan-review.md.
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

### FINDING_10: risk-integration: skills/design/scripts/test-findings-classification.sh:201-211
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Parser harness only tests quiet capture via LARCH_QUIET_DISABLE=1, not default larch_quiet_init FD 3 path used by tally. Awk/emit_kv boundary break under quiet mode would not fail CI. Add parser case capturing FD 3 with quiet enabled (no LARCH_QUIET_DISABLE).
- **Suggested revision**: Address the concern above.

### FINDING_11: risk-integration: skills/design/scripts/tally-plan-review.sh:345-347
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] MainAgent adjudication can accept findings in markdown while TSV voting_result stays rejected with empty vN columns. Downstream analytics treating TSV voting_result as authoritative would mis-score MainAgent rounds. Document in harness or add consumer-oriented assertion comment.
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: scripts/test-render-voter-prompt.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Harness checks axis enum templates but not lowercase literal examples in rendered prompt lines. Uppercase examples could reach judges and fail parse-rate until manual discovery. grep -Fq CORRECTNESS=true (and peers) on both grammar renders.
- **Suggested revision**: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] risk-integration: scripts/test-dispatch-plan-voters.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] No new assertions on VOTER_N_TOOL KVs for waterfall fallback. Slot/tool KV bugs might only surface in live dispatch, not stubbed loop tests. Optional PATH-stubbed dispatch integration test in a follow-up.
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

### FINDING_18: correctness: skills/design/scripts/tally-plan-review.sh:345-347
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] MainAgent TSV rows force voting_result=rejected while MainAgent vote_for_id can accept findings in markdown artifacts. Analytics on TSV voting_result undercount accepts when 0-judge MainAgent adjudication accepted items. Document contract or use distinct voting_result for MainAgent-only TSV rows.
- **Suggested revision**: Address the concern above.

### FINDING_19: correctness: scripts/parse-judge-vote-and-rating.sh:50-68
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Glued YES-CORRECTNESS= tokens parse vote via lib-vote-tally but not separate CORRECTNESS= axis. Judge omits space after YES; forensic row shows empty correctness and uncertain=true despite substantive vote. Document whitespace requirement in voter prompts or strip vote token before axis split in awk.
- **Suggested revision**: Address the concern above.

### FINDING_20: correctness: skills/design/scripts/tally-plan-review.sh:237
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] --voter uses tool-name canonical map instead of dispatch slot index Waterfall emits --voter Claude for slots 1 and 2; second Claude collides on v1 and tally errors, so v2_tool never records Claude substitution Map --voter by VOTER_N slot index (1/2/3); keep vN_tool from declared SLOT
- **Suggested revision**: Address the concern above.

### FINDING_21: correctness: skills/design/scripts/test-findings-classification.md:22-23
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Harness doc claims waterfall v2_tool=Claude case but no test implements it Acceptance criterion 18 and forensic analytics for substituted judges lack regression lock Add three-voter fixture with Claude in slot 2; assert v2_tool and v2 ratings
- **Suggested revision**: Address the concern above.

### FINDING_22: correctness: skills/design/scripts/test-tally-plan-review.sh:1-312
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Planned test-tally-plan-review extensions largely absent Plan-required mutex, deprecation stderr, sanitization, and explicit-out tests not in this harness Port missing cases from plan section or update acceptance to single harness
- **Suggested revision**: Address the concern above.

### FINDING_23: architecture: skills/design/scripts/plan-review-loop.sh:100-102
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Header-only TSV uses inline helper not tally invocation Diverges from plan preferred empty-ballot tally as header authority Invoke tally-plan-review.sh with empty ballot for header-only paths
- **Suggested revision**: Address the concern above.

### FINDING_24: [OUT_OF_SCOPE] risk-integration: scripts/dispatch-code-voters.sh:1246
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Unplanned verification-context change from diff-plan to code May change code-review voter prompts outside Lesson 2 scope Verify intent; split to separate PR if unrelated
- **Suggested revision**: Address the concern above.

### FINDING_25: [OUT_OF_SCOPE] correctness: skills/design/scripts/tally-plan-review.sh:79-81
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Argv validation exits 2 not plan-specified exit 1 Only matters if callers distinguish exit codes Normalize to exit 1 or document exit 2 as normative
- **Suggested revision**: Address the concern above.

