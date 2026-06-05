### FINDING_1:
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/plan-review-loop.sh:1172-1184
- **Concern**: Pre-review Jaccard dedup can drop the [SCOPE-REDUCTION] tag before tally. Scenario: The plan protects tagged findings in the aggregator and tally, but plan-review-loop.sh dedup still merges FINDING blocks when Concern token overlap exceeds 0.6 and keeps only the first block body. An over-scope addition kept first absorbs a later [SCOPE-REDUCTION] finding on the same plan surface; the merged ballot loses the tag and the scope cut reverts to the normal 2-YES threshold
- **Proposed resolution**: In dedup (or its plan step), skip merging when either block contains an unfenced [SCOPE-REDUCTION], or always retain the tagged block when a merge pair disagrees on scope direction; add a test-plan-review-loop case with opposing tagged/untagged concerns on overlapping text

### FINDING_2:
- **Reviewer(s)**: Codex-Arch, Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:119-133
- **Concern**: Scope anchor uses brainstorm-merged feature context instead of the originating issue. Scenario: The plan says voters/reviewers/scout should anchor on the originating issue, but it passes FEATURE_FILE after brainstorm.md is merged into plan-review-feature-context.txt; brainstorm additions can become treated as required issue scope and defeat scope-reduction findings
- **Proposed resolution**: Preserve the original feature file path before the brainstorm merge and pass that original path to the new scope-anchor reviewer/scout/voter wiring; keep the merged file only for existing optional context paths if still needed

### FINDING_3:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lib-vote-tally.sh:56-70
- **Concern**: Unfenced-anywhere [SCOPE-REDUCTION] detection can protect unrelated findings. Scenario: A normal correctness finding about the tag contract can mention [SCOPE-REDUCTION] in its concern or fix text. The proposed detector would classify it as a scope-reduction block and accept it on YES=1,NO=1.
- **Proposed resolution**: Detect the tag only as a leading marker in the normalized finding problem field or heading, such as "- **Concern**: [SCOPE-REDUCTION]"; add a negative test for non-leading unfenced mentions.

### FINDING_4:
- **Reviewer(s)**: Codex-Edge
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/scripts/tally-plan-review.sh:416-421
- **Concern**: MainAgent scope-cut acceptance will not reach findings-classification.tsv. Scenario: The plan says the MainAgent 0-judge path and write_findings_classification read the overridden result, but this code forces tsv_result=rejected for every MainAgent adjudication. Accepted artifacts can say accepted while the forensic TSV says rejected.
- **Proposed resolution**: Either update the plan to preserve the existing MainAgent forensic behavior, or include the needed tally-plan-review.sh/docs/tests change so scope-reduction MainAgent results are classified consistently.

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/scripts/test-plan-review-scope-anchor.sh:77-99
- **Concern**: Dedicated end-to-end harness duplicates surfaces already extended elsewhere. Scenario: Plan adds test-plan-review-scope-anchor.sh plus Makefile/agent-lint siblings while also extending test-tally-plan-review.sh, test-plan-review-prompt.sh, and test-render-voter-prompt.sh for the same tally and prompt contracts; ~520 added lines already buy coverage
- **Proposed resolution**: Fold tally YES>=1 scope-cut cases into test-tally-plan-review.sh and keep prompt byte-equality in the existing prompt harnesses; drop the new harness/Makefile target unless it adds a unique assertion

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/scripts/tally-plan-review.sh:58-61
- **Concern**: Scope-reduction override can accept exonerated findings. Scenario: Plan applies protected accept when classify_result is not accepted and only checks YES>=1 and YES>=NO; EXONERATE is neutral so YES=1 with EXONERATE=2 yields exonerated then flips to accepted, applying a cut voters explicitly exonerated
- **Proposed resolution**: Restrict the override to classify_result=rejected (not exonerated), or require YES strictly greater than EXONERATE before promoting

### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: latent
- **Focus area**: security
- **Location**: scripts/lib-vote-tally.sh:74-80
- **Concern**: Planned [SCOPE-REDUCTION] detector is broader than the promised prefix contract. Scenario: Any unfenced mention of the literal token in copied issue text or scenario prose can turn an unrelated finding into a protected scope-cut and accept it on a one-YES tie
- **Proposed resolution**: Match only a leading [SCOPE-REDUCTION] on the structured Concern/what text (or heading if aggregation moves it) and add a false-positive test for non-leading mentions

### FINDING_8:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/scripts/tally-plan-review.sh:416-421
- **Concern**: Plan says MainAgent classifications read the overridden accepted result, but the current 0-judge contract forces voting_result=rejected. Scenario: Implementing the plan literally conflicts with the existing MainAgent forensic TSV behavior documented in skills/design/SKILL.md and can fail or mislead downstream classification consumers
- **Proposed resolution**: Keep the MainAgent TSV override and narrow the plan text/tests to accepted artifacts plus voting-tally output, or explicitly update the SKILL/docs/tests if changing that contract is intended

### FINDING_9:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-plan-review-scope-anchor.sh (planned)
- **Concern**: Control case expects untagged YES=1 NO=1 tie to be rejected. Scenario: With three eligible voters classify_result returns neutral on a 1-1 YES-NO tie not rejected; asserting the literal rejected label would fail or encode the wrong contract
- **Proposed resolution**: Assert the finding is absent from accepted-plan-findings.md and the tally row shows neutral (do not require the rejected label)

### FINDING_10:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/tally-plan-review.sh:416-423
- **Concern**: Plan says MainAgent scope cuts are accepted and classification uses the overridden tally result, but the current classification path forces every MainAgent result to rejected. Scenario: The 0-judge MainAgent path can show a [SCOPE-REDUCTION] finding as accepted in accepted-plan-findings.md while findings-classification.tsv records rejected
- **Proposed resolution**: Include a plan step to remove or narrow the MainAgent tsv_result=rejected override so accepted scope-reduction results are recorded consistently, and cover it in test-tally-plan-review.sh

### FINDING_11:
- **Reviewer(s)**: Cursor-dyn-shared-consumers
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1094
- **Concern**: MainAgent 0-judge adjudication omits scope-anchor and [SCOPE-REDUCTION] voter rubric. Scenario: The plan wires --scope-anchor-file only through dispatch-plan-voters.sh to render-voter-prompt.sh. On TALLY_ELIGIBLE_COUNT==0, tally-plan-review.sh exits main-agent-vote-required and SKILL.md tells the orchestrator to vote using the generic proportionality rubric only. A MainAgent EXONERATE (or NO) on a valid scope-cut leaves YES=0, so the proposed tally-plan-review.sh override (YES>=1 && YES>=NO) never fires — contradicting the plan edge-case that a lone advocate accepts scope cuts.
- **Proposed resolution**: Add MainAgent instructions mirroring the new render-voter-prompt scope-anchor block and [SCOPE-REDUCTION] problem-first rule (read FEATURE_FILE/issue scope; judge over-scope claim, not removal precision), or document an explicit exception if 0-judge panels are out of scope.

### FINDING_12:
- **Reviewer(s)**: Codex-dyn-shared-consumers
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/tally-plan-review.sh:416-421
- **Concern**: Plan says the scope-reduction override applies to MainAgent and write_findings_classification reads the overridden result, but current classification code coerces every MainAgent result back to rejected after tally_votes_for_id.. Scenario: In the 0-judge fallback, a MainAgent YES on a [SCOPE-REDUCTION] block can place the block in accepted-plan-findings.md while findings-classification.tsv records rejected, drifting downstream tally/log artifacts from the accepted result.
- **Proposed resolution**: Revise the plan to update this MainAgent coercion: preserve the overridden accepted result for scope-reduction blocks, or explicitly remove/narrow the forced rejected assignment when MainAgent adjudication is the accepted source; add a MainAgent protected-acceptance harness assertion.

### FINDING_13:
- **Reviewer(s)**: Cursor-dyn-marker-lifecycle
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:1172-1184
- **Concern**: Pre-aggregator Jaccard dedup can drop the [SCOPE-REDUCTION] literal when it merges a tagged finding into an earlier similar untagged block. Scenario: merge_reviewers keeps the first block body and only appends reviewer names; the discarded block Concern (often the only unfenced tag site) is thrown away before aggregate-findings.sh or tally-plan-review.sh run, so is_scope_reduction_block never fires and the finding reverts to the 2-YES threshold
- **Proposed resolution**: In dedup(), when merging, prefer the block whose Concern contains an unfenced [SCOPE-REDUCTION], or copy that prefix into the kept Concern; add a harness case in test-plan-review-scope-anchor.sh or test-plan-review-loop.sh

### FINDING_14:
- **Reviewer(s)**: Codex-dyn-marker-lifecycle
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/scripts/aggregate-findings.sh:502-620
- **Concern**: Plan relies on an aggregator prompt to preserve [SCOPE-REDUCTION] but has no validation fallback. Scenario: When the plan-mode aggregator merges or normalizes a tagged reviewer finding and drops the literal, the final ballot block loses the marker and tally-plan-review.sh applies the normal threshold, so a one-YES scope cut is rejected despite the proposed protection
- **Proposed resolution**: Add a minimal plan-mode validation guard: if any input FINDING block contains an unfenced leading [SCOPE-REDUCTION] marker, require the merged output to contain the marker too or reject the merge so the original tagged findings file is kept; cover that path in the scope-anchor harness

### FINDING_15:
- **Reviewer(s)**: Codex-dyn-marker-lifecycle
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lib-vote-tally.sh:56-69; skills/design/scripts/plan-review-loop.sh:1005-1012; skills/design/scripts/tally-plan-review.sh:248-276
- **Concern**: Planned detector is broader than the marker contract. Scenario: The prompt says reviewers prefix TSV what, which the collector renders as Concern, but planned is_scope_reduction_block matches any unfenced occurrence in any block/id; a normal finding or OOS item that mentions the literal in a suggested fix or prose would get protected acceptance with YES=1 NO=1
- **Proposed resolution**: Restrict the override to FINDING_* blocks whose normalized - **Concern**: text starts with [SCOPE-REDUCTION] after fence stripping; add controls for non-leading and OOS literals

### FINDING_16:
- **Reviewer(s)**: Codex-dyn-marker-lifecycle
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/scripts/tally-plan-review.sh:406-421; skills/design/scripts/tally-plan-review.md:23-27; skills/design/scripts/test-findings-classification.sh:232-239
- **Concern**: MainAgent classification output will not read the overridden result. Scenario: The plan says the scope-reduction override applies in the 0-judge MainAgent path and write_findings_classification reads TALLY_RESULT, but current code forces voting_result=rejected whenever MAIN_AGENT_VOTER is set; voting-tally.md and accepted-plan-findings.md can say accepted while findings-classification.tsv says rejected
- **Proposed resolution**: Keep the minimum contract explicit: either revise the plan/docs to preserve the existing MainAgent forensic TSV exception, or change this branch and its test only for accepted scope-reduction rows

### FINDING_17:
- **Reviewer(s)**: Cursor-dyn-scope-anchor-flow
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:115-116; skills/design/scripts/render-plan-review-prompt.sh (proposed)
- **Concern**: Round-1 baseline no-op is specified as path equality but wiring always uses a separate baseline file. Scenario: Round 1 copies plan.txt to plan-review-baseline.txt and passes both paths to render-plan-review-prompt.sh; the proposed degrade guard is only when --baseline-plan-file equals --plan-file, so the drift-compare block always fires even when contents are identical, contradicting the edge-case contract and adding noise on every first review
- **Proposed resolution**: Skip the baseline block when cmp -s baseline plan (or hashes match), not only when argv paths are the same string; update the edge-case text to match

### FINDING_18:
- **Reviewer(s)**: Codex-dyn-scope-anchor-flow
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:119-134,797-814,1287-1292
- **Concern**: The planned scope anchor reuses FEATURE_FILE after the brainstorm merge instead of preserving the originating issue as the anchor. Scenario: When brainstorm.md contains optional ideas, the scout, reviewers, and voters can treat those ideas as issue scope; SIMPLE/HARD review may still choose bloat-shaped specialists or reject [SCOPE-REDUCTION] findings as out of proportion to the merged context
- **Proposed resolution**: Capture the base issue path before the brainstorm merge and use that issue-scope file for the new scout/reviewer/voter anchor flags; keep the merged brainstorm context separate and explicitly non-binding if it must still be shown

