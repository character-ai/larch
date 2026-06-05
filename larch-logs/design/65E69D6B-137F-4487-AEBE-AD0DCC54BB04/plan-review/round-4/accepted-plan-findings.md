### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:55-56
- **Concern**: Marker-loss fallback points at pre-merge findings file. Scenario: aggregate-findings.sh validates before replacing findings-in-scope.md so AGGREGATED=false already keeps the pre-merge in-scope ballot; copying findings.md or findings.md.tmp can bypass the in-scope/OOS split and reintroduce dedup-removed blocks
- **Proposed resolution**: Drop the extra restore step; on AGGREGATED=false (optionally only when aggregator stderr shows scope-reduction marker loss) keep using findings-in-scope.md for ballot.txt


### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:119-134; scripts/launch-review.sh:387-416; scripts/dispatch-plan-voters.sh:59-66,148-156
- **Concern**: Scope anchor may remain outside the design tmpdir. Scenario: The plan defaults SCOPE_ANCHOR_FILE to ORIGINAL_FEATURE_FILE when no approved outline exists, but Codex prompt-file launches only add the output/design tmpdir as sandbox context, and plan voters dispatch prompt files without extra context flags. If IMPLEMENT_TMPDIR differs from DESIGN_TMPDIR, Codex reviewers or voters are told to read an anchor path they cannot access.
- **Proposed resolution**: Always materialize plan-review-scope-anchor.txt under DESIGN_TMPDIR by copying the original issue even when no outline is approved; append the approved outline when present, and pass that staged path everywhere.


### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/review/scripts/aggregate-findings.sh:174-631
- **Concern**: Aggregator marker-preservation plan lacks a reliable merge-group key. Scenario: The plan asks aggregate-validate.py to require a leading [SCOPE-REDUCTION] marker when any input block in that merge group has one, but the current aggregator contract exposes reviewer slots, not source finding IDs. A reviewer with one tagged and one untagged finding can cause either false rejection or marker loss depending on how the validator infers the group.
- **Proposed resolution**: Keep the SIMPLE path conservative: do not aggregate tagged scope-reduction blocks, or reject aggregation when tagged inputs are not preserved as leading-tag output blocks and fall back to the original findings. Avoid adding per-merge-group inference unless the output contract also gains explicit source IDs.


### FINDING_4:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:1413-1452
- **Concern**: Baseline snapshot has two first-round entry points. Scenario: Plan says copy plan to plan-review-baseline.txt before the first _run_plan_review_round, but the script calls that function on separate legacy (~1416) and multi-round (~1452) paths. A cp placed only on one branch leaves the other without a baseline; putting cp inside _run_plan_review_round without a once-per-invocation guard refreshes every round.
- **Proposed resolution**: Snapshot once after SCOPE_ANCHOR_FILE setup and before the ROUND_CAP_ARG_SEEN fork (or duplicate the same cp on both branches); never refresh inside _run_plan_review_round.


### FINDING_5:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/scripts/aggregate-findings.sh:193-209,520-613
- **Concern**: Plan does not define a reliable merge-group mapping for scope-reduction marker validation. Scenario: The proposed plan-mode validator must preserve markers per merged group, but the current validator only has reviewer-slot attribution. If one reviewer contributes both a tagged scope-cut and an unrelated untagged finding, aggregation can drop the tag on one group while preserving another tag elsewhere, and the planned all-markers-dropped test would miss the partial loss. The protected tally rule then silently does not apply to the lost scope-cut.
- **Proposed resolution**: Define the validation mapping concretely: for each tagged input block, require at least one merged output block with a leading [SCOPE-REDUCTION] marker plus reviewer overlap and normalized Concern/problem token overlap above the dedup threshold; reject/fallback otherwise. Add a partial-loss fixture with mixed tagged and untagged findings from the same reviewer.


### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/review/scripts/aggregate-findings.sh:174-632
- **Concern**: Plan-mode `[SCOPE-REDUCTION]` validation re-implements marker normalization in `aggregate-validate.py` while claiming one canonical detector in `scripts/check-scope-reduction-marker.sh`. Scenario: Validator and shell helper drift; tagged scope cuts pass dedup but fail validation (or vice versa) after regex edits in only one copy
- **Proposed resolution**: Have plan-mode validation call `scripts/check-scope-reduction-marker.sh --file` per block (or per merge group) instead of inlining equivalent regex in Python


### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:1531-1544
- **Concern**: Invocation-wide baseline drift check would re-flag accepted in-loop revisions. Scenario: Round 1 accepts a required test or doc step, auto-revise applies it, then round 2 compares against the pre-round-1 baseline and treats that legitimate addition as drift, creating a scope-cut tug-of-war
- **Proposed resolution**: Drop the baseline snapshot and --baseline-plan-file drift block for this SIMPLE fix; anchor reviewers to the original issue only


### FINDING_8:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/lib-vote-tally.sh:137-140, skills/design/scripts/plan-review-loop.sh:1531-1534
- **Concern**: Protected scope-reduction tie override bypasses the existing quorum before auto-revision. Scenario: A tagged finding with YES=1 and NO=1 is neutral today, but the plan would accept it and feed it into automatic plan revision, allowing one reviewer to remove required scope without a majority
- **Proposed resolution**: Keep classify_result thresholds unchanged; use the issue-anchor prompt to improve votes, and leave neutral scope-cut ties for MainAgent or Gate B/manual handling


### FINDING_10:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/scripts/collect-findings.sh:408-412 vs plan detector contract
- **Concern**: TSV collect prepends [severity] before what so Concern never leads with [SCOPE-REDUCTION]. Scenario: Reviewers emit TSV with [SCOPE-REDUCTION] in what per plan; collect builds Concern as [important] [SCOPE-REDUCTION] …; check-scope-reduction-marker requires a leading marker in Concern/what, so dedup preservation, aggregation validation, and protected tally never fire on real panel output
- **Proposed resolution**: Normalize Concern before marker detection (strip one leading [important|nit|latent] bracket) in check-scope-reduction-marker.sh and document it; or change collect-findings TSV→Concern mapping when what already starts with [SCOPE-REDUCTION]; add a collect→ballot harness case


### FINDING_11:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: Makefile:4-112
- **Concern**: New detector harness is not registered in Makefile. Scenario: The plan creates scripts/test-check-scope-reduction-marker.sh but only registers test-plan-review-scope-anchor, so make lint can pass while the canonical marker detector cases are never run
- **Proposed resolution**: Add a test-check-scope-reduction-marker .PHONY target and shard entry, or have the registered scope-anchor harness invoke that detector harness explicitly


### FINDING_12:
- **Reviewer(s)**: Cursor-dyn-anchor-provenance
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:469
- **Concern**: skills/design/scripts/plan-review-loop.sh:119-134. Scenario: Scope anchor is pre-merge feature-description.txt but that file is written from full issue title+body with no larch:plan stripping
- **Proposed resolution**: On re-design or replace flows the issue body often still contains a prior larch:plan block; binding scope evidence then embeds the old plan and can defeat [SCOPE-REDUCTION] proportionality (voters/reviewers treat stale plan text as required scope) Build SCOPE_ANCHOR_FILE from issue narrative with larch:plan markers stripped (reuse plan-block-read.sh / issue-body.txt minus plan block) rather than raw feature-description.txt; keep brainstorm merge out of the anchor


### FINDING_13:
- **Reviewer(s)**: Codex-dyn-anchor-provenance
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/dispatch-plan-voters.sh:59-83,148-156; skills/shared/scripts/render-voter-prompt.sh:66-74
- **Concern**: Voter scope anchor is only prompt-threaded, not delivered as readable context. Scenario: Plan says voters get --scope-anchor-file and the voter prompt tells them to read that path, but the Claude voter launch currently gets only the prompt file and no Read-tool/context-file access unless dispatch also passes a context flag; the voter can then judge from the ballot/current plan text instead of the issue anchor
- **Proposed resolution**: Revise the plan so dispatch-plan-voters.sh either inlines the scope anchor as an untrusted block in render-voter-prompt.sh when --scope-anchor-file is set, or passes the anchor through voter launch context (including retry LARCH_VPR_CTX) so all voter tiers can actually read the same binding anchor.


### FINDING_14:
- **Reviewer(s)**: Cursor-dyn-marker-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:1106-1219
- **Concern**: Aggregator marker-loss validation cannot catch tags stripped by pre-aggregation Jaccard dedup. Scenario: Jaccard dedup runs on the combined findings stream before split/aggregate. If the inline deduper merges a tagged block into an untagged keeper and drops the leading `[SCOPE-REDUCTION]` prefix, downstream plan-mode aggregation never sees a tagged input, so the new validator has nothing to reject and protected tally never fires
- **Proposed resolution**: Add an explicit post-dedup marker parity gate (compare pre/post dedup via `check-scope-reduction-marker.sh`) or extend the ephemeral dedup script in-place; do not rely on aggregation validation alone


### FINDING_15:
- **Reviewer(s)**: Codex-dyn-marker-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/tally-plan-review.sh:248-276,474-516
- **Concern**: Protected scope-reduction acceptance is not limited to FINDING blocks. Scenario: The tally loop applies one TALLY_RESULT path to both FINDING and OOS ids, so a tagged OOS heading could get the YES>=NO protected promotion even though the contract says scope cuts remain in_scope findings
- **Proposed resolution**: Guard the protected override and MainAgent classification preservation with id matching FINDING_*; add an OOS tagged negative case


### FINDING_17:
- **Reviewer(s)**: Cursor-dyn-env-handoff
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:1106-1210
- **Concern**: Plan requires pre-aggregation Jaccard dedup to call check-scope-reduction-marker.sh per block and never drop a leading [SCOPE-REDUCTION] marker, but does not specify how to wire that into the existing inline Python heredoc deduper. Scenario: The heredoc dedup() at plan-review-loop.sh:1172-1184 still merges blocks solely on Jaccard overlap via merge_reviewers(); an implementer can add the shell helper elsewhere yet leave this path unchanged, so tagged scope-cut findings can lose their marker before aggregation/tally
- **Proposed resolution**: Spell out the dedup integration: either extend the heredoc merge loop to subprocess check-scope-reduction-marker.sh (or a Python-callable equivalent) before merging, or replace the inline deduper with a bash driver that enforces the tagged/untagged merge rules; add a test-plan-review-loop.sh case that proves a tagged block merged into an overlapping untagged block keeps a leading marker


### FINDING_18:
- **Reviewer(s)**: Codex-dyn-env-handoff
- **Severity**: important
- **Focus area**: security
- **Location**: skills/design/scripts/plan-review-loop.sh:119-123,155-175
- **Concern**: Proposed SCOPE_ANCHOR_FILE result-env emission lacks CR/LF path sanitation before raw env writing. Scenario: A direct or legacy plan-review-loop.sh --feature-file path containing a newline can inject extra lines into .step3-plan-review-result.env, or make emit_kv fail after the raw env file was already written
- **Proposed resolution**: Validate/canonicalize SCOPE_ANCHOR_FILE before emitting or writing it, rejecting CR/LF, or switch write_step3_result_env to phase_driver_write_result_env for all keys


### FINDING_19:
- **Reviewer(s)**: Codex-dyn-env-handoff
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/run-step3-review.md:38-40
- **Concern**: Plan omits the run-step3-review.md handoff doc update for SCOPE_ANCHOR_FILE. Scenario: After scripts add SCOPE_ANCHOR_FILE to .step3-review-result.env, the normalized result-env contract doc still lists the old key set and describes a different handoff
- **Proposed resolution**: Add SCOPE_ANCHOR_FILE to the normalized result env list and note that it is forwarded from the inner plan-review result when present


