### FINDING_1: Pruned-empty rounds converge or degrade instead of skipping toward the re-probe
- **Reviewer(s)**: Cursor-Arch, Codex-Arch
- **Severity**: important
- **Concern**: All-pruned/pruned-empty rounds are not consistently represented as a skipped, non-degraded round that still advances the loop. In /implement and standalone /review they can terminate as convergence before the intended later full re-probe; in /design they can fall into degraded-empty collector handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Pruned-empty rounds are wired as terminal convergence not round advancement Plan requires PANEL_PRUNED_EMPTY to consume the round counter while keeping round 5's full re-probe reachable but proposes REVIEW_CORE_STATUS=ok review-and-fix maps ok to complete and the Step 5 loop exits immediately on complete no-changes no-findings converged-small-changes Standalone /review Step 3f also exits when ok has zero accepted findings Round 3 all-pruned never reaches round 5 Add a distinct non-terminal status e.g. prune-skipped emit and forward PANEL_PRUNED_EMPTY from review-core through review-and-fix Update review-implement-step5-loop.sh to increment round_num and continue when pruned-empty and round_num less than cap Update skills/review/SKILL.md Step 3f to continue not converge on prune-skip Replace the proposed all-pruned round converges prose
  - From Codex-Arch: Have dispatch emit the filtered manifest path or replace the conventional manifest with the filtered one, then use that path for slot_count, reviewer mapping, label-map, and record; add a PANEL_PRUNED_EMPTY guard or direct terminal path before the final degraded-empty-collector normalization


### FINDING_2: /design loop keeps using the unfiltered manifest after pruning
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Codex-Pragmatic, Codex-Requirements, Codex-dyn-ledger-path-threading
- **Severity**: important
- **Concern**: After /design dispatch filters the panel, plan-review-loop still derives slot counts, reviewer-path mapping, label-map generation, degradation checks, and prune recording from the original plan-review-slots.ndjson. Partial-prune rounds can therefore be marked degraded or recorded against unlaunched slots.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Have dispatch emit the filtered manifest path or replace the conventional manifest with the filtered one, then use that path for slot_count, reviewer mapping, label-map, and record; add a PANEL_PRUNED_EMPTY guard or direct terminal path before the final degraded-empty-collector normalization
  - From Codex-Edge: Have dispatch-plan-review-panel emit a PANEL_MANIFEST for the filtered manifest and update plan-review-loop to use it for slot_count, plan_review_slot_for_reviewer, label-map generation, and reviewer-prune record; add a non-empty partial-prune design-loop harness asserting DEGRADED_PANEL stays false.
  - From Codex-Pragmatic: Have dispatch-plan-review-panel emit the filtered manifest path, then parse and use it in plan-review-loop for slot mapping, slot counts, label-map/record inputs, and degradation checks
  - From Codex-Requirements: Make dispatch replace plan-review-slots.ndjson with the filtered manifest or emit a filtered PANEL_MANIFEST path, update plan-review-loop mapping, slot_count, record, and add a partial-prune non-degraded harness case
  - From Codex-dyn-ledger-path-threading: Have dispatch-plan-review-panel.sh emit an effective PANEL_MANIFEST path and have plan-review-loop.sh parse and use it for slot_count, output-to-slot mapping, label-map generation, and reviewer-prune record


### FINDING_3: Claude fallback review slots are invisible to prune collector history
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: When external review tools are unavailable and slots run through Claude fallback, collect-findings does not emit collector OK rows for those outputs. The prune ledger can treat successful fallback slots as uncollected and fail to prune them in later rounds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Extend the plan so record can mark Claude fallback outputs collected, either by writing collector rows for CLAUDE_OUTPUT_FILES or by matching normalized phase2/phase3/retry output files with successful non-empty outputs when no collector row exists; add a both-vendors-down fixture for this case


### FINDING_4: Step 5 loop still extends the fixed round cap after degraded rounds
- **Reviewer(s)**: Cursor-Edge, Cursor-Pragmatic, Cursor-dyn-cap-removal-completeness, Codex-dyn-cap-removal-completeness
- **Severity**: important
- **Concern**: The plan removes degraded-round cap inflation at entry/resume points but leaves the post-round effective_round_cap increment when DEGRADED_ROUND=true. A degraded Step 5 round can still push the effective cap beyond the fixed cap of 5.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Delete this post-round inflation block (and any harness pins); keep EFFECTIVE_ROUND_CAP equal to the base ROUND_CAP everywhere
  - From Cursor-Pragmatic: Step 5 can still exceed the advertised fixed cap of 5 after a degraded round, failing acceptance and reintroducing unbounded review Remove the post-round effective_round_cap increment block; keep DEGRADED_ROUND classification for telemetry only; update review-implement-step5-loop.md and test-review-and-fix inflation assertions
  - From Cursor-dyn-cap-removal-completeness: Delete the DEGRADED_ROUND post-round bump; set effective_round_cap = ROUND_CAP everywhere including lines 439 452 458
  - From Codex-dyn-cap-removal-completeness: Explicitly delete the post-round effective_round_cap increment at lines 404-407 and keep DEGRADED_ROUND only for non-cap classification; pin a degraded-round loop case where EFFECTIVE_ROUND_CAP remains 5


### FINDING_5: /design pruning uses artifact ROUND_NUM instead of Gate C review round
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-ledger-path-threading
- **Severity**: important
- **Concern**: /design prune filtering and ledger recording are planned around ROUND_NUM, but /design review rounds are Gate C re-entries tracked by STEP3_REVIEW_ROUND_NUM. SIMPLE runs can keep ROUND_NUM at 1, so rounds 3-4 pruning and the later re-probe never engage and ledger rows are keyed to the wrong round.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Plan threads plan-review-loop --round-num from run-step3-review ROUND_NUM (artifact cursor; stays 1 on SIMPLE and tracks plan-after-round snapshots on HARD). Issue scope and outline define a review round as a Gate C re-entry (STEP3_REVIEW_ROUND_NUM / review-round-count.txt). With ROUND_NUM, filter always sees N≤2 on SIMPLE, so rounds 3–4 pruning and round-5 re-probe never run; ledger rows also land under the wrong round key and corrupt the two-strike window. Add skills/design/scripts/run-step3-review.sh to the plan: pass STEP3_REVIEW_ROUND_NUM (or a dedicated --prune-round-num) into plan-review-loop; forward that value to dispatch-plan-review-panel.sh filter and reviewer-prune.sh record --round. Keep existing ROUND_NUM only for plan-review/round-N artifact paths. Extend test-plan-review-loop.sh to simulate Gate C re-entry 3 with a populated ledger.
  - From Cursor-Pragmatic: Conditional spawning does not run on /design despite being the primary multi-round surface Add --review-round-num (or pass STEP3_REVIEW_ROUND_NUM) from run-step3-review.sh into plan-review-loop.sh; use that value in reviewer-prune.sh filter/record --round N; keep ROUND_NUM for plan-review/round-N artifact paths only; extend test-plan-review-loop.sh with a second Gate C entry where review-round=2 but artifact round stays 1
  - From Cursor-Requirements: run-step3-review.sh passes --round-num "$ROUND_NUM" to plan-review-loop; for SIMPLE ROUND_NUM stays 1 across Gate C re-entries while STEP3_REVIEW_ROUND_NUM increments, so reviewer-prune.sh filter always sees N≤2 (full panel) and ledger rows collapse onto round=1 — acceptance "round 3-4 pruning" never applies on /design Thread a separate --prune-round-num (or pass STEP3_REVIEW_ROUND_NUM) from run-step3-review.sh through plan-review-loop.sh to dispatch-plan-review-panel.sh and reviewer-prune.sh record; keep ROUND_NUM only for plan-review/round-N artifact paths; add test-run-step3-review.sh case asserting prune round tracks review-round-count not artifact index
  - From Cursor-dyn-ledger-path-threading: Ledger at DESIGN_TMPDIR/reviewer-prune-ledger.tsv accumulates rows with wrong round column; filter never sees N=3/4 on SIMPLE and mis-keys HARD re-reviews without plan revision so conditional spawning does not match acceptance criteria Plumb STEP3_REVIEW_ROUND_NUM as a separate --prune-round-num (or equivalent) from run-step3-review.sh through plan-review-loop.sh to dispatch-plan-review-panel.sh and reviewer-prune.sh record; leave ROUND_NUM for forensic artifact dirs only


### FINDING_6: Step 5 telemetry fence and banner still report degraded-inflated caps
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Codex-dyn-cap-removal-completeness
- **Severity**: important
- **Concern**: The executable Step 5 telemetry fence and related banner/prose still compute or expose PRIOR_DEGRADED_ROUNDS and an inflated EFFECTIVE_ROUND_CAP, even though loop behavior is meant to use a fixed cap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Update the Step 5 telemetry fence and banner prose in skills/implement/SKILL.md to use the fixed base cap only (drop PRIOR_DEGRADED_ROUNDS / inflated EFFECTIVE_ROUND_CAP or pin them to the base). Align scripts/test-run-step5-review.sh and any STEP5_REVIEW_STATUS consumers that read EFFECTIVE_ROUND_CAP.
  - From Cursor-Pragmatic: Operators see inflated round caps and misleading banners after cap inflation is removed from the loop Remove degraded counting from the Step 5 telemetry fence; emit ROUND_CAP=5 only; update the banner line and the prose at 849-853 to match fixed-cap behavior
  - From Codex-dyn-cap-removal-completeness: Expand the SKILL.md plan item to update the Step 5 telemetry fence and banner to a fixed cap, remove or redefine PRIOR_DEGRADED_ROUNDS/EFFECTIVE_ROUND_CAP accordingly, and update scripts/test-implement-structure.sh pins in the same PR


### FINDING_7: Code-review PANEL_MANIFEST remains pre-filtered after pruning
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: In the /review and /implement dispatch path, the manifest passed onward for record and coverage can still identify the pre-prune panel rather than the filtered panel that actually launched. Accepted-count attribution and slot coverage can therefore disagree with executed reviewers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: PANEL_MANIFEST today points at the pre-filter panel-manifest.ndjson. After filter writes --out, review-core record and the planned coverage-gate change need the post-prune manifest; if PANEL_MANIFEST is left on the unfiltered file, accepted_count attribution and STATIC_SLOT_COUNT can disagree with what was actually launched. After filter, set PANEL_MANIFEST (and any manifest path passed to record) to the filtered --out file; keep the unfiltered manifest only for forensics if needed. Add a dispatch-panel harness assertion that PANEL_MANIFEST matches the filtered NDJSON when PRUNE_ACTIVE=true.


### FINDING_9: /implement can record prune data for a degraded attempt that is retried
- **Reviewer(s)**: Codex-Pragmatic, Codex-dyn-ledger-path-threading
- **Severity**: important
- **Concern**: If review-core records prune ledger rows before review-and-fix detects a degraded tally and retries the same round, later pruning can be based on a discarded attempt whose artifacts were overwritten.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Delay reviewer-prune record for /implement until review-and-fix has completed any degraded retry, or otherwise suppress recording on non-final round attempts
  - From Codex-dyn-ledger-path-threading: Skip reviewer-prune record when the code-review tally contains the degraded-panel banner, or move /implement recording until review-and-fix.sh has completed any degraded retry


### FINDING_10: /review --diff --subagent heavy-worker path omits pruning semantics
- **Reviewer(s)**: Codex-Pragmatic, Codex-Requirements, Codex-dyn-ledger-path-threading
- **Severity**: important
- **Concern**: The standalone /review subagent contract still describes the old full-panel, three-round behavior and does not pass a prune ledger into review-core. Conditional spawning and the full re-probe behavior would be bypassed in /review --diff --subagent mode.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Update the heavy-worker contract alongside skills/review/SKILL.md: use the run-stable prune ledger, pass it to each review-core round, document rounds 3-4 pruning, all-pruned convergence, and the fixed 5-round cap/reprobe semantics
  - From Codex-Requirements: Update heavy-worker.md to mirror the conditional spawning contract, pass --prune-ledger "$REVIEW_TMPDIR/reviewer-prune-ledger.tsv" to each review-core round, and align its round-cap/re-probe prose with the new 5-round behavior
  - From Codex-dyn-ledger-path-threading: Amend heavy-worker.md to pass --prune-ledger "$REVIEW_TMPDIR/reviewer-prune-ledger.tsv" on each review-core.sh round and align its round loop with the 5-round rule


### FINDING_11: Accepted-count matching is not pinned to exact normalized attribution tokens
- **Reviewer(s)**: Cursor-dyn-attribution-fidelity, Codex-dyn-attribution-fidelity
- **Severity**: important
- **Concern**: The prune record logic can miscount accepted findings if it uses substring matching or the wrong delimiter normalization. Pipe-delimited code-review reviewer_slots and comma-delimited plan-review attributions need exact normalized token equality, especially for labels that share prefixes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-attribution-fidelity: Pin in scripts/reviewer-prune.md: code path counts accepted rows only when the ledger label equals a | token in reviewer_slots (or apply the same pipe-normalization as reviewer_slots_for_tsv before substring match)
  - From Codex-dyn-attribution-fidelity: Split attribution cells into tokens and compare exact normalized tokens: code reviewer_slots on |, plan finding_reviewers on comma, trim whitespace, then test equality; add prefix-label fixtures for both skills


### FINDING_12: Collector-status joins miss phase2, phase3, and retry basename normalization
- **Reviewer(s)**: Codex-dyn-attribution-fidelity
- **Severity**: important
- **Concern**: Code-review prune recording may fail to mark a launched reviewer as collected when successful output arrives through phase2, phase3, or empty-output retry filenames. The accepted attribution can normalize to the original basename while collector status remains tied to the suffixed path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-attribution-fidelity: Normalize collector REVIEWER_FILE basenames with the same phase2, phase3, and retry stripping loop before joining to manifest output; add phase3 and retry fixtures in scripts/test-reviewer-prune.sh


### FINDING_13:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:20-28
- **Concern**: [SCOPE-REDUCTION] Collected-only history changes the required launched-round pruning rule. Scenario: A reviewer slot that launches in rounds 1 and 2 but returns NOT_SUBSTANTIVE, EMPTY_OUTPUT, or is dropped under no-fallback has zero accepted findings in its last two launched rounds, yet the plan keeps it eligible because collected=false rows do not count
- **Proposed resolution**: Count every filtered manifest row that was actually launched as a strike-window row with accepted_count=0 unless the whole round is rolled back or history is missing/corrupt; use collector status for diagnostics, not to erase launched rounds


