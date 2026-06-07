### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-implement-step5-loop.sh:278-281
- **Concern**: skills/review-and-fix/scripts/review-and-fix.sh:1583-1584. Scenario: skills/review/SKILL.md:120
- **Proposed resolution**: Pruned-empty rounds are wired as terminal convergence not round advancement Plan requires PANEL_PRUNED_EMPTY to consume the round counter while keeping round 5's full re-probe reachable but proposes REVIEW_CORE_STATUS=ok review-and-fix maps ok to complete and the Step 5 loop exits immediately on complete no-changes no-findings converged-small-changes Standalone /review Step 3f also exits when ok has zero accepted findings Round 3 all-pruned never reaches round 5 Add a distinct non-terminal status e.g. prune-skipped emit and forward PANEL_PRUNED_EMPTY from review-core through review-and-fix Update review-implement-step5-loop.sh to increment round_num and continue when pruned-empty and round_num less than cap Update skills/review/SKILL.md Step 3f to continue not converge on prune-skip Replace the proposed all-pruned round converges prose

### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:738-790,857-884,1615-1624
- **Concern**: Design loop prune state is not threaded through the existing manifest and terminal-status paths. Scenario: A partially pruned /design round can still be compared against the unfiltered plan-review-slots.ndjson and marked degraded because fewer paths returned than original slots; an all-pruned round can fall through the final collect_ok_count==0 logic and become degraded-empty-collector despite the plan requiring LOOP_STATUS=complete and no degraded flags
- **Proposed resolution**: Have dispatch emit the filtered manifest path or replace the conventional manifest with the filtered one, then use that path for slot_count, reviewer mapping, label-map, and record; add a PANEL_PRUNED_EMPTY guard or direct terminal path before the final degraded-empty-collector normalization

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/scripts/collect-findings.sh:268-333; skills/review/scripts/dispatch-panel.sh:111-123
- **Concern**: Claude fallback review slots do not produce collector OK rows for the prune ledger. Scenario: When both external tools are unavailable, dispatch creates cursor-shaped rows that run via Claude fallback; collect-findings only writes collector-results.env for external outputs, so reviewer-prune record will treat successful Claude fallback slots as uncollected and rounds 3-4 will never prune those code-review combos
- **Proposed resolution**: Extend the plan so record can mark Claude fallback outputs collected, either by writing collector rows for CLAUDE_OUTPUT_FILES or by matching normalized phase2/phase3/retry output files with successful non-empty outputs when no collector row exists; add a both-vendors-down fixture for this case

### FINDING_1:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-implement-step5-loop.sh:404-407
- **Concern**: Plan removes entry/mav degraded cap inflation but omits the per-round `effective_round_cap++` when `DEGRADED_ROUND=true`. Scenario: A degraded round 3 still bumps the cap to 6, violating acceptance “fixed 5 (no degraded inflation)” and can run a sixth review round
- **Proposed resolution**: Delete this post-round inflation block (and any harness pins); keep `EFFECTIVE_ROUND_CAP` equal to the base `ROUND_CAP` everywhere

### FINDING_1:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:857-898
- **Concern**: /design loop has no contract for the filtered plan-review manifest. Scenario: After a partial prune, dispatch can launch a reduced non-empty panel, but plan-review-loop still reads $DESIGN_TMPDIR/plan-review-slots.ndjson for slot_count and reviewer-path mapping; if that file remains the full pre-filter manifest, successful pruned rounds are marked degraded because path count is lower than slot_count and later record/label mapping can include pruned slots.
- **Proposed resolution**: Have dispatch-plan-review-panel emit a PANEL_MANIFEST for the filtered manifest and update plan-review-loop to use it for slot_count, plan_review_slot_for_reviewer, label-map generation, and reviewer-prune record; add a non-empty partial-prune design-loop harness asserting DEGRADED_PANEL stays false.

### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:52-102
- **Concern**: skills/design/scripts/run-step3-review.sh:312. Scenario: /design pruning keys off the wrong round counter
- **Proposed resolution**: Plan threads plan-review-loop --round-num from run-step3-review ROUND_NUM (artifact cursor; stays 1 on SIMPLE and tracks plan-after-round snapshots on HARD). Issue scope and outline define a review round as a Gate C re-entry (STEP3_REVIEW_ROUND_NUM / review-round-count.txt). With ROUND_NUM, filter always sees N≤2 on SIMPLE, so rounds 3–4 pruning and round-5 re-probe never run; ledger rows also land under the wrong round key and corrupt the two-strike window. Add skills/design/scripts/run-step3-review.sh to the plan: pass STEP3_REVIEW_ROUND_NUM (or a dedicated --prune-round-num) into plan-review-loop; forward that value to dispatch-plan-review-panel.sh filter and reviewer-prune.sh record --round. Keep existing ROUND_NUM only for plan-review/round-N artifact paths. Extend test-plan-review-loop.sh to simulate Gate C re-entry 3 with a populated ledger.

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:794-807
- **Concern**: Step 5 telemetry fence still inflates EFFECTIVE_ROUND_CAP. Scenario: Plan removes degraded cap inflation in run-step5-review.sh and review-implement-step5-loop.sh but does not update the executable Step 5 telemetry fence that still calls lib-implement-round-cap.sh --count-prior-degraded and prints EFFECTIVE_ROUND_CAP=$((round_cap + prior_degraded_rounds)). Banner and downstream parsing can advertise a higher cap than the loop enforces after the change.
- **Proposed resolution**: Update the Step 5 telemetry fence and banner prose in skills/implement/SKILL.md to use the fixed base cap only (drop PRIOR_DEGRADED_ROUNDS / inflated EFFECTIVE_ROUND_CAP or pin them to the base). Align scripts/test-run-step5-review.sh and any STEP5_REVIEW_STATUS consumers that read EFFECTIVE_ROUND_CAP.

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/review/scripts/review-core.sh:64-65
- **Concern**: skills/review/scripts/dispatch-panel.sh:507. Scenario: Filtered manifest path not pinned for record/coverage
- **Proposed resolution**: PANEL_MANIFEST today points at the pre-filter panel-manifest.ndjson. After filter writes --out, review-core record and the planned coverage-gate change need the post-prune manifest; if PANEL_MANIFEST is left on the unfiltered file, accepted_count attribution and STATIC_SLOT_COUNT can disagree with what was actually launched. After filter, set PANEL_MANIFEST (and any manifest path passed to record) to the filtered --out file; keep the unfiltered manifest only for forensics if needed. Add a dispatch-panel harness assertion that PANEL_MANIFEST matches the filtered NDJSON when PRUNE_ACTIVE=true.

### FINDING_1:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:20-28
- **Concern**: [SCOPE-REDUCTION] Collected-only history changes the required launched-round pruning rule. Scenario: A reviewer slot that launches in rounds 1 and 2 but returns NOT_SUBSTANTIVE, EMPTY_OUTPUT, or is dropped under no-fallback has zero accepted findings in its last two launched rounds, yet the plan keeps it eligible because collected=false rows do not count
- **Proposed resolution**: Count every filtered manifest row that was actually launched as a strike-window row with accepted_count=0 unless the whole round is rolled back or history is missing/corrupt; use collector status for diagnostics, not to erase launched rounds

### FINDING_1:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:52-102
- **Concern**: skills/design/scripts/run-step3-review.sh:194-313. Scenario: /design pruning keys filter off ROUND_NUM but Gate C review rounds use STEP3_REVIEW_ROUND_NUM from review-round-count.txt; for SIMPLE ROUND_NUM stays 1 on every re-entry so rounds 3-4 pruning and round-5 re-probe never engage
- **Proposed resolution**: Conditional spawning does not run on /design despite being the primary multi-round surface Add --review-round-num (or pass STEP3_REVIEW_ROUND_NUM) from run-step3-review.sh into plan-review-loop.sh; use that value in reviewer-prune.sh filter/record --round N; keep ROUND_NUM for plan-review/round-N artifact paths only; extend test-plan-review-loop.sh with a second Gate C entry where review-round=2 but artifact round stays 1

### FINDING_2:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/reviewer-prune.sh (filter rule)
- **Concern**: skills/design/scripts/run-step3-review.sh:194-198. Scenario: SIMPLE tier review cap is 3 so round-5 full re-probe never runs; round 3 is both pruned (N=3) and the terminal review round, contradicting the approved outline last round full panel intent
- **Proposed resolution**: SIMPLE /design exits with a reduced panel on its final Gate C pass and never gets a full re-probe Extend filter bypass to treat N >= tier_review_cap (SIMPLE 3 HARD 5) as full panel, not only N >= 5; document tier mapping in reviewer-prune.md and acceptance criteria

### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-implement-step5-loop.sh:404-407
- **Concern**: skills/review-and-fix/scripts/review-implement-step5-loop.md:15. Scenario: Plan removes degraded cap inflation at loop entry and in run-step5-review.sh but leaves mid-loop effective_round_cap += 1 when DEGRADED_ROUND=true
- **Proposed resolution**: Step 5 can still exceed the advertised fixed cap of 5 after a degraded round, failing acceptance and reintroducing unbounded review Remove the post-round effective_round_cap increment block; keep DEGRADED_ROUND classification for telemetry only; update review-implement-step5-loop.md and test-review-and-fix inflation assertions

### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:794-853
- **Concern**: scripts/run-step5-review.sh:200-213. Scenario: Step 5 telemetry fence and banner still compute PRIOR_DEGRADED_ROUNDS and EFFECTIVE_ROUND_CAP via count_prior_degraded_rounds while the plan only greps adjacent prose
- **Proposed resolution**: Operators see inflated round caps and misleading banners after cap inflation is removed from the loop Remove degraded counting from the Step 5 telemetry fence; emit ROUND_CAP=5 only; update the banner line and the prose at 849-853 to match fixed-cap behavior

### FINDING_1:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-and-fix.sh:1346-1384
- **Concern**: Planned ledger recording inside review-core would record discarded degraded-retry attempts. Scenario: /implement can run review-core, detect a degraded tally, then immediately rerun review-core for the same round; if the first attempt appends prune rows before the retry, later pruning can be based on accepted counts from an attempt whose artifacts were overwritten
- **Proposed resolution**: Delay reviewer-prune record for /implement until review-and-fix has completed any degraded retry, or otherwise suppress recording on non-final round attempts

### FINDING_2:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/dispatch-plan-review-panel.sh:249-321; skills/design/scripts/plan-review-loop.sh:857-883
- **Concern**: Filtered design manifest is not surfaced to the loop. Scenario: After pruning, dispatch can launch fewer paths, but plan-review-loop still hardcodes plan-review-slots.ndjson for slot counting and degradation math; a correctly pruned partial panel can be marked degraded because successful paths are compared against the unfiltered slot count
- **Proposed resolution**: Have dispatch-plan-review-panel emit the filtered manifest path, then parse and use it in plan-review-loop for slot mapping, slot counts, label-map/record inputs, and degradation checks

### FINDING_3:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/references/heavy-worker.md:32-36
- **Concern**: /review subagent path is omitted from the plan. Scenario: Standalone /review --diff --subagent follows this binding contract, which still says full panel and a 3-round safety limit and does not pass a prune ledger to review-core, so conditional spawning and the round-5 full reprobe are not applied in that /review mode
- **Proposed resolution**: Update the heavy-worker contract alongside skills/review/SKILL.md: use the run-stable prune ledger, pass it to each review-core round, document rounds 3-4 pruning, all-pruned convergence, and the fixed 5-round cap/reprobe semantics

### FINDING_1:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/run-step3-review.sh:251-313
- **Concern**: skills/design/scripts/plan-review-loop.sh:738-744. Scenario: /design prune filter and ledger record use ROUND_NUM but issue scope defines a design round as a Gate C re-entry (review-round-count / STEP3_REVIEW_ROUND_NUM)
- **Proposed resolution**: run-step3-review.sh passes --round-num "$ROUND_NUM" to plan-review-loop; for SIMPLE ROUND_NUM stays 1 across Gate C re-entries while STEP3_REVIEW_ROUND_NUM increments, so reviewer-prune.sh filter always sees N≤2 (full panel) and ledger rows collapse onto round=1 — acceptance "round 3-4 pruning" never applies on /design Thread a separate --prune-round-num (or pass STEP3_REVIEW_ROUND_NUM) from run-step3-review.sh through plan-review-loop.sh to dispatch-plan-review-panel.sh and reviewer-prune.sh record; keep ROUND_NUM only for plan-review/round-N artifact paths; add test-run-step3-review.sh case asserting prune round tracks review-round-count not artifact index

### FINDING_1:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:857-883
- **Concern**: Plan filters design slots in dispatch but leaves plan-review-loop downstream slot_count and path-count checks tied to the unfiltered plan-review-slots.ndjson. Scenario: Round 3 prunes one slot and launches the rest; dispatcher emits DEGRADED_ROUND=false, but the loop counts the original manifest and sees fewer output paths than slots, so DEGRADED_PANEL becomes 1 and violates the pruned rounds are not degraded acceptance criterion
- **Proposed resolution**: Make dispatch replace plan-review-slots.ndjson with the filtered manifest or emit a filtered PANEL_MANIFEST path, update plan-review-loop mapping, slot_count, record, and add a partial-prune non-degraded harness case

### FINDING_2:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/review/references/heavy-worker.md:34-36
- **Concern**: The plan updates inline /review but not the /review --subagent heavy-worker contract, which still says full panel and rounds 1-3. Scenario: Standalone /review --diff --subagent would continue launching all reviewer combos and cannot exercise the round-5 full re-probe, so the /review diff-mode scope is only partially delivered
- **Proposed resolution**: Update heavy-worker.md to mirror the conditional spawning contract, pass --prune-ledger "$REVIEW_TMPDIR/reviewer-prune-ledger.tsv" to each review-core round, and align its round-cap/re-probe prose with the new 5-round behavior

### FINDING_1:
- **Reviewer(s)**: Cursor-dyn-attribution-fidelity
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/scripts/tally-code-votes.md:67
- **Concern**: Plan does not require record to match code-review labels against pipe-delimited reviewer_slots TSV cells. Scenario: After tally, reviewer_slots is pipe-delimited (reviewer_slots_for_tsv converts comma ballot attribution to |). If reviewer-prune.sh record splits finding_reviewers on commas or compares against pre-TSV ballot text, accepted_count stays 0 while voting-tally shows accepts → silent over-pruning by round 4
- **Proposed resolution**: Pin in scripts/reviewer-prune.md: code path counts accepted rows only when the ledger label equals a | token in reviewer_slots (or apply the same pipe-normalization as reviewer_slots_for_tsv before substring match)

### FINDING_1:
- **Reviewer(s)**: Codex-dyn-attribution-fidelity
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/reviewer-prune.sh (new); skills/design/scripts/plan-review-loop.sh:616-635,927-950; scripts/scout-dynamic-archetypes.sh:571-581; skills/review/scripts/tally-code-votes.sh:168-178
- **Concern**: Accepted-count matching is specified as substring containment instead of exact attribution-token matching. Scenario: Plan labels such as Cursor-dyn-cache and Cursor-dyn-cache-api can both be valid dynamic archetypes; an accepted finding attributed to Cursor-dyn-cache-api would also satisfy a contains check for Cursor-dyn-cache, so the wrong combo stays eligible in rounds 3-4
- **Proposed resolution**: Split attribution cells into tokens and compare exact normalized tokens: code reviewer_slots on |, plan finding_reviewers on comma, trim whitespace, then test equality; add prefix-label fixtures for both skills

### FINDING_2:
- **Reviewer(s)**: Codex-dyn-attribution-fidelity
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/reviewer-prune.sh (new); scripts/dispatch-with-waterfall.sh:191-200,453-477,535-548; skills/review/scripts/collect-findings.sh:419-432,465-500; scripts/collect-agent-results.sh:992-997,1142-1148
- **Concern**: Collector-status lookup for code-review record is not pinned to the same fallback/retry basename normalization as attribution. Scenario: A reviewer accepted only after phase2, phase3, or empty-output retry is classified under the original basename, but collector results can name a -phase2.txt, -phase3.txt, or -retry.txt path; if record checks STATUS against the manifest output literally, collected=false keeps that combo out of the 2-round window and it is not pruned
- **Proposed resolution**: Normalize collector REVIEWER_FILE basenames with the same phase2, phase3, and retry stripping loop before joining to manifest output; add phase3 and retry fixtures in scripts/test-reviewer-prune.sh

### FINDING_1:
- **Reviewer(s)**: Cursor-dyn-ledger-path-threading
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/run-step3-review.sh:251-313
- **Concern**: skills/design/scripts/plan-review-loop.sh:86-102. Scenario: Plan reuses ROUND_NUM for prune filter/record but caller binds it to SIMPLE literal 1 or HARD plan-revision cursor not STEP3_REVIEW_ROUND_NUM
- **Proposed resolution**: Ledger at DESIGN_TMPDIR/reviewer-prune-ledger.tsv accumulates rows with wrong round column; filter never sees N=3/4 on SIMPLE and mis-keys HARD re-reviews without plan revision so conditional spawning does not match acceptance criteria Plumb STEP3_REVIEW_ROUND_NUM as a separate --prune-round-num (or equivalent) from run-step3-review.sh through plan-review-loop.sh to dispatch-plan-review-panel.sh and reviewer-prune.sh record; leave ROUND_NUM for forensic artifact dirs only

### FINDING_1:
- **Reviewer(s)**: Codex-dyn-ledger-path-threading
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/dispatch-plan-review-panel.sh:249-321; skills/design/scripts/plan-review-loop.sh:738-771,857-883
- **Concern**: Filtered /design manifest path is not threaded back to the loop. Scenario: The plan filters into a separate manifest but current loop hard-codes plan-review-slots.ndjson for slot counts and later recording, so a reduced round can be treated as degraded or recorded against unlaunched slots
- **Proposed resolution**: Have dispatch-plan-review-panel.sh emit an effective PANEL_MANIFEST path and have plan-review-loop.sh parse and use it for slot_count, output-to-slot mapping, label-map generation, and reviewer-prune record

### FINDING_2:
- **Reviewer(s)**: Codex-dyn-ledger-path-threading
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/scripts/review-core.sh:842-861; skills/review-and-fix/scripts/review-and-fix.sh:1369-1384
- **Concern**: /implement degraded retry can record a rolled-back attempt. Scenario: The proposed record call in review-core runs before review-and-fix.sh detects the degraded tally banner and retries the same round, so a non-settled first attempt can affect later pruning
- **Proposed resolution**: Skip reviewer-prune record when the code-review tally contains the degraded-panel banner, or move /implement recording until review-and-fix.sh has completed any degraded retry

### FINDING_3:
- **Reviewer(s)**: Codex-dyn-ledger-path-threading
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/review/references/heavy-worker.md:32-36
- **Concern**: /review --diff --subagent contract is not updated for pruning. Scenario: The supported subagent path runs the review loop from heavy-worker.md; leaving it without the same --prune-ledger path means standalone /review diff mode can bypass conditional spawning
- **Proposed resolution**: Amend heavy-worker.md to pass --prune-ledger "$REVIEW_TMPDIR/reviewer-prune-ledger.tsv" on each review-core.sh round and align its round loop with the 5-round rule

### FINDING_1:
- **Reviewer(s)**: Cursor-dyn-cap-removal-completeness
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-implement-step5-loop.sh:404-407
- **Concern**: Plan removes count_prior_degraded_rounds inflation but leaves per-round effective_round_cap += 1 when DEGRADED_ROUND=true. Scenario: A degraded round can still extend the cap past 5 for bulk-skip substantiality and cap-hit gates contradicting acceptance fixed cap 5
- **Proposed resolution**: Delete the DEGRADED_ROUND post-round bump; set effective_round_cap = ROUND_CAP everywhere including lines 439 452 458

### FINDING_1:
- **Reviewer(s)**: Codex-dyn-cap-removal-completeness
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-implement-step5-loop.sh:205-215,404-458; plan.txt:86-88
- **Concern**: Plan misses the post-round degraded cap increment. Scenario: Even if entry and MAV-resume math switch to base ROUND_CAP, a remaining DEGRADED_ROUND=true branch would still add 1 to effective_round_cap and let degraded rounds silently exceed the fixed 5-round cap in bulk-skip/substantial continuation paths
- **Proposed resolution**: Explicitly delete the post-round effective_round_cap increment at lines 404-407 and keep DEGRADED_ROUND only for non-cap classification; pin a degraded-round loop case where EFFECTIVE_ROUND_CAP remains 5

### FINDING_2:
- **Reviewer(s)**: Codex-dyn-cap-removal-completeness
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:794-807,845-853; scripts/test-implement-structure.sh:473-481; plan.txt:126-128
- **Concern**: Step 5 SKILL update is scoped as prose but the executable telemetry fence still computes degraded cap inflation. Scenario: The prompt can still print up to 5+prior_degraded_rounds and the structure harness still pins PRIOR_DEGRADED_ROUNDS/EFFECTIVE_ROUND_CAP, so either the old inflated banner survives or make lint fails when the fence is corrected
- **Proposed resolution**: Expand the SKILL.md plan item to update the Step 5 telemetry fence and banner to a fixed cap, remove or redefine PRIOR_DEGRADED_ROUNDS/EFFECTIVE_ROUND_CAP accordingly, and update scripts/test-implement-structure.sh pins in the same PR

