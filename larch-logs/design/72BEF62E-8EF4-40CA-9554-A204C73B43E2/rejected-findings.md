### [Plan Review] FINDING_100

### FINDING_100: SKILL still claims scout+dispatch block remains inline after moving to plan-review-loop.md
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:633-634
- **Concern**: SKILL still claims scout+dispatch block remains inline after moving to plan-review-loop.md. Scenario: Operators read contradictory instructions
- **Proposed resolution**: Edit the Step 3 intro paragraph in the SKILL.md worklist


### [Plan Review] FINDING_31

### FINDING_31: The proposed SKILL.md invocation captures plan-review-loop.sh output in a command substitu
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:697-707
- **Concern**: The proposed SKILL.md invocation captures plan-review-loop.sh output in a command substitution but does not check the script exit status.. Scenario: When plan-review-loop.sh exits 1 for panel-failed or 2 for argv/file errors, the rest of the Bash block can continue and finish successfully with empty parsed variables, allowing Step 3.5 to proceed after a failed review.
- **Proposed resolution**: Capture rc explicitly around the command substitution and exit nonzero or branch on LOOP_STATUS before continuing; add harness coverage for panel-failed and argv-error propagation through the SKILL.md wrapper.


### [Plan Review] FINDING_32

### FINDING_32: The plan says to source lib-voter-parse-rate.sh for the same check_and_retry_voter_parse_r
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: scripts/lib-voter-parse-rate.sh:1-32
- **Concern**: The plan says to source lib-voter-parse-rate.sh for the same check_and_retry_voter_parse_rate discipline as dispatch-code-voters.sh, but that library currently only contains diagnostic helpers; the actual parse-rate functions remain local to dispatch-code-voters.sh.. Scenario: A direct source-and-call implementation in dispatch-plan-voters.sh will fail with command not found, while copying the functions duplicates stateful code that depends on REVIEW_TMPDIR, mode, ctx_args, and code-review timing-kind assumptions.
- **Proposed resolution**: Add scripts/lib-voter-parse-rate.sh to the UPDATED file list and refactor the shared functions with explicit parameters for ballot file, temp dir, launcher mode/context args, timing kind, and issue-log site; then update both voter dispatchers to use the shared API.


### [Plan Review] FINDING_33

### FINDING_33: plan-review-loop stages findings by scanning raw reviewer files for markdown ### FINDING_N
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/render-plan-review-prompt.sh:90-108; scripts/collect-agent-results.sh:54-60
- **Concern**: plan-review-loop stages findings by scanning raw reviewer files for markdown ### FINDING_N/OOS_N blocks, but plan-review prompts require TSV/JSONL and the collector exposes normalized structured sidecars. Scenario: External reviewers that follow the prompt produce TSV records or the JSON no-issues sentinel; the proposed helper sees no markdown blocks, emits an empty findings.md, and silently drops valid review findings
- **Proposed resolution**: Revise the plan to call collect-agent-results.sh with --substantive-validation --validation-mode --structured-reviewer-validation and build findings.md from STRUCTURED_SIDECAR records, mapping scope=in_scope to FINDING_N and scope=out_of_scope to OOS_N; add a TSV fixture to test-plan-review-loop.sh


### [Plan Review] FINDING_35

### FINDING_35: The planned panel-failed path depends on reaching post-collection logic, but collect-agent
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/collect-agent-results.sh:228-256
- **Concern**: The planned panel-failed path depends on reaching post-collection logic, but collect-agent-results.sh exits 1 for a missing or empty paths file. Scenario: The plan's Phase 3 collapse test stubs DISPATCH_OK=false with empty reviewer outputs; the foreground collector can fail before plan-review-loop.sh emits LOOP_STATUS=panel-failed, so SKILL.md cannot surface the intended degradation contract
- **Proposed resolution**: Handle empty or unreadable PANEL_PATHS_FILE immediately after dispatch when DISPATCH_OK=false, or wrap the collector and normalize that specific empty-output case into LOOP_STATUS=panel-failed with exit 1 and a regression assertion


### [Plan Review] FINDING_37

### FINDING_37: The testing strategy does not cover the required /design --simple equivalence path or the 
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/references/approval-gates.md:11
- **Concern**: The testing strategy does not cover the required /design --simple equivalence path or the /design --trivial bypass. Scenario: Acceptance requires /design --hard and /design --simple to produce the same session-root artifacts as pre-refactor and /design --trivial to remain unchanged; the plan only names manual /design --hard equivalence and unit/structure tests, so tier-specific routing can regress unnoticed
- **Proposed resolution**: Add explicit validation for --simple equivalence and --trivial non-invocation, either as manual acceptance steps recorded in the plan or harness coverage that proves quick review does not call plan-review-loop.sh while full-budget hard/simple paths do


### [Plan Review] FINDING_39

### FINDING_39: The plan claims sourcing scripts/lib-voter-parse-rate.sh supplies check_and_retry_voter_pa
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lib-voter-parse-rate.sh:1-32 scripts/dispatch-code-voters.sh:125-278
- **Concern**: The plan claims sourcing scripts/lib-voter-parse-rate.sh supplies check_and_retry_voter_parse_rate check_voter_parse_rate for Voter 1 but that library only holds diag helpers; the substantive parse-rate functions remain inline in dispatch-code-voters.sh. Scenario: Voter 1 parse-rate work is underspecified or wrongly scoped to a one-line source leading to broken or duplicated logic
- **Proposed resolution**: Revise plan: either extract check_voter_parse_rate and check_and_retry_voter_parse_rate into a shared sourced module (real refactor) or spell out adapting the existing plan-specific retry_voter pattern for a new Claude slot without mis-attributing it to lib-voter-parse-rate.sh


### [Plan Review] FINDING_43

### FINDING_43: Proposed SKILL.md edits remove scout/panel/PANEL_PATHS tokens and add negative greps but t
- **Reviewer(s)**: Cursor-dyn-conditional-dependency
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh:417-422
- **Concern**: Proposed SKILL.md edits remove scout/panel/PANEL_PATHS tokens and add negative greps but the plan only lists removing Check 14b2 not 14c1-14c3. Scenario: CI still requires those strings in SKILL.md or new negative pins fight existing positives
- **Proposed resolution**: Rewrite or delete Checks 14c1-14c3 and add explicit grep -Fq -v style assertions aligned with plan lines 205-208


### [Plan Review] FINDING_44

### FINDING_44: Plan UPDATED dispatch-plan-voters claims check_and_retry_voter_parse_rate can come from so
- **Reviewer(s)**: Cursor-dyn-conditional-dependency
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lib-voter-parse-rate.sh:1-32 vs scripts/dispatch-code-voters.sh:95-279
- **Concern**: Plan UPDATED dispatch-plan-voters claims check_and_retry_voter_parse_rate can come from sourced lib-voter-parse-rate.sh. Scenario: Those functions still live only in dispatch-code-voters.sh after sourcing the 3 small helpers
- **Proposed resolution**: Extend lib with the full parse-rate + retry surface and refactor dispatch-code-voters.sh or revise the plan to extend plan-specific check_plan_voter_substantive retry_voter to Voter 1


### [Plan Review] FINDING_45

### FINDING_45: Harness lists stubbed DISPATCH_OK=false panel failure only
- **Reviewer(s)**: Cursor-dyn-conditional-dependency
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:66-76 (proposed test-plan-review-loop.sh)
- **Concern**: Harness lists stubbed DISPATCH_OK=false panel failure only. Scenario: No coverage for missing dispatch-plan-review-panel.sh or pure inline dispatch-with-waterfall fallback
- **Proposed resolution**: Document no-compat branch and keep pins or add a dedicated fixture test if a fallback remains required


### [Plan Review] FINDING_47

### FINDING_47: Voter 1 failure logging copies code-voters append-tool-failure pattern without pinning DES
- **Reviewer(s)**: Cursor-dyn-conditional-dependency
- **Severity**: latent
- **Focus area**: security
- **Location**: plan.txt:137-148 (UPDATED dispatch-plan-voters.sh)
- **Concern**: Voter 1 failure logging copies code-voters append-tool-failure pattern without pinning DESIGN_TMPDIR-relative diag paths and redact parity in this PR. Scenario: Execution-issues append might omit --redact or write diags outside the design session directory
- **Proposed resolution**: Spell full paths flags and log resolution mirroring dispatch-code-voters.sh:303-345 adapted to DESIGN_TMPDIR


### [Plan Review] FINDING_48

### FINDING_48: Unconditional dispatch-plan-review-panel call plus grep pin with no compat story for absen
- **Reviewer(s)**: Cursor-dyn-conditional-dependency
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:24-26 and plan.txt:203-206
- **Concern**: Unconditional dispatch-plan-review-panel call plus grep pin with no compat story for absent script or inline waterfall. Scenario: Implementers cannot tell whether forks must vendor the panel script or embed fallback
- **Proposed resolution**: Declare mandatory surface and delete fallback talk or specify detection plus test and pin updates


### [Plan Review] FINDING_49

### FINDING_49: Voter1 diag append-tool-failure adaptation underspecified
- **Reviewer(s)**: Cursor-dyn-conditional-dependency
- **Severity**: latent
- **Focus area**: security
- **Location**: plan.txt:137-148
- **Concern**: Voter1 diag append-tool-failure adaptation underspecified. Scenario: Leakage or wrong log path
- **Proposed resolution**: Specify DESIGN_TMPDIR paths and --redact parity


### [Plan Review] FINDING_50

### FINDING_50: Proposed SKILL.md removes scout/panel/PANEL_PATHS tokens while the plan only removes Check
- **Reviewer(s)**: Cursor-dyn-conditional-dependency
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh:417-422
- **Concern**: Proposed SKILL.md removes scout/panel/PANEL_PATHS tokens while the plan only removes Check 14b2 not the 14c1-14c3 positive greps. Scenario: CI still mandates those SKILL substrings or conflicts with new negative greps
- **Proposed resolution**: Rewrite or delete Checks 14c1-14c3 and add explicit negative SKILL assertions per plan lines 205-208


### [Plan Review] FINDING_51

### FINDING_51: Plan claims check_and_retry_voter_parse_rate lives in lib-voter-parse-rate.sh after sourci
- **Reviewer(s)**: Cursor-dyn-conditional-dependency
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lib-voter-parse-rate.sh:1-32 vs scripts/dispatch-code-voters.sh:95-279
- **Concern**: Plan claims check_and_retry_voter_parse_rate lives in lib-voter-parse-rate.sh after sourcing. Scenario: Functions remain only in dispatch-code-voters.sh; sourcing the lib alone is insufficient
- **Proposed resolution**: Extract the full parse-rate and retry helpers into the lib and refactor dispatchers or rewrite the plan to extend plan-specific helpers instead


### [Plan Review] FINDING_52

### FINDING_52: Harness case 6 only stubs failing dispatch-plan-review-panel.sh
- **Reviewer(s)**: Cursor-dyn-conditional-dependency
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:66-76 (proposed test-plan-review-loop.sh)
- **Concern**: Harness case 6 only stubs failing dispatch-plan-review-panel.sh. Scenario: No test for missing panel script or inline-only dispatch-with-waterfall fallback
- **Proposed resolution**: Declare no fallback and drop related dialectic text or add a fixture plus pins for the alternate entrypoint


### [Plan Review] FINDING_53

### FINDING_53: Contradictory extract-into-new-lib versus library-already-exists wording
- **Reviewer(s)**: Cursor-dyn-conditional-dependency
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: plan.txt:144 (UPDATED dispatch-plan-voters.sh)
- **Concern**: Contradictory extract-into-new-lib versus library-already-exists wording. Scenario: Implementer scope confusion
- **Proposed resolution**: Use one coherent story for what code moves versus what already exists


### [Plan Review] FINDING_54

### FINDING_54: Unconditional dispatch-plan-review-panel invocation plus mandatory grep token inside plan-
- **Reviewer(s)**: Cursor-dyn-conditional-dependency
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:24-26 and plan.txt:203-206
- **Concern**: Unconditional dispatch-plan-review-panel invocation plus mandatory grep token inside plan-review-loop.sh with no compat branch. Scenario: Implementers cannot tell whether forks without the panel script must inline waterfall or fail closed
- **Proposed resolution**: Document mandatory #2665 surface or specify existence detection fallback and matching tests or pins


### [Plan Review] FINDING_55

### FINDING_55: Voter 1 append-tool-failure pattern referenced without pinning DESIGN_TMPDIR-relative path
- **Reviewer(s)**: Cursor-dyn-conditional-dependency
- **Severity**: latent
- **Focus area**: security
- **Location**: plan.txt:137-148 (UPDATED dispatch-plan-voters.sh)
- **Concern**: Voter 1 append-tool-failure pattern referenced without pinning DESIGN_TMPDIR-relative paths and --redact parity vs code review. Scenario: Ballot-bearing diagnostics could log to the wrong execution-issues path or omit redaction
- **Proposed resolution**: Spell adapted paths flags and log resolution mirroring dispatch-code-voters.sh:303-345 for DESIGN_TMPDIR


### [Plan Review] FINDING_56

### FINDING_56: `VOTING_TALLY_FILE` is part of the script stdout contract (plan L44-L45) but is omitted fr
- **Reviewer(s)**: Cursor-dyn-kv-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md (proposed Step 3 parse block per session plan L104-L112)
- **Concern**: `VOTING_TALLY_FILE` is part of the script stdout contract (plan L44-L45) but is omitted from the `case` whitelist and from the pre-loop clears (plan L104-L105). Scenario: Orchestrator cannot record the tally path from machine output; any future Step 3/4/5 logic or breadcrumbs keyed on `VOTING_TALLY_FILE` would silently miss it
- **Proposed resolution**: Add `VOTING_TALLY_FILE` to the cleared vars and extend the `case` arm alongside `TALLY_PLAN_REVIEW_STATUS`


### [Plan Review] FINDING_57

### FINDING_57: `plan-review-loop.sh` is specified to exit `1` (`panel-failed`, plan L50) and `2` (argv or
- **Reviewer(s)**: Cursor-dyn-kv-contract
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md (proposed Step 3 invocation per session plan L94-L103)
- **Concern**: `plan-review-loop.sh` is specified to exit `1` (`panel-failed`, plan L50) and `2` (argv or pre-dispatch errors, plan L49); the draft block uses `_plan_review_out=$(...)` with no `set +e` / `$?` guard before downstream parsing. Scenario: Under typical `set -e` skill shells, a non-zero exit from command substitution aborts the step before the `while` loop runs, so KVs are never applied and MAV / degradation prose never runs
- **Proposed resolution**: Match other blocks (e.g. Step 5b pattern at L859): wrap capture with `set +e`; save `rc`; `set -e`; parse stdout when non-empty; branch on `rc` and `LOOP_STATUS`


### [Plan Review] FINDING_59

### FINDING_59: Plan requires SKILL to lose `scout-plan-archetypes-wrapper.sh`, `dispatch-plan-review-pane
- **Reviewer(s)**: Cursor-dyn-kv-contract
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-design-structure.sh:416-421 vs session plan L194-L212
- **Concern**: Plan requires SKILL to lose `scout-plan-archetypes-wrapper.sh`, `dispatch-plan-review-panel.sh`, and `PANEL_PATHS_FILE` (plan L208) but the Pin removals subsection only removes Check 14b2 (plan L211-L212); current CI still enforces 14c1-14c3 with `grep -Fq` on those tokens in SKILL.md. Scenario: `make lint` / `test-design-structure` fails after SKILL edits unless additional pins are deleted or rewritten
- **Proposed resolution**: Extend Pin removals to explicitly drop or replace `(14c1)`, `(14c2)`, and `(14c3)` (and align any prose that still claims those pins hold)


### [Plan Review] FINDING_60

### FINDING_60: Stdout KVs are only useful if the script always prints the promised `LOOP_STATUS` / `AGGRE
- **Reviewer(s)**: Cursor-dyn-kv-contract
- **Severity**: latent
- **Focus area**: correctness
- **Location**: session plan L35-L36 and L236 (tally exit 2)
- **Concern**: Stdout KVs are only useful if the script always prints the promised `LOOP_STATUS` / `AGGREGATOR_*` lines before a non-zero exit; mid-pipeline `tally-plan-review.sh` exit `2` is called out as fatal without specifying partial KV emission. Scenario: Operator or harness sees empty `_plan_review_out` plus failure, so `TALLY_PLAN_REVIEW_STATUS` / `LOOP_STATUS` stay blank despite the contract narrative
- **Proposed resolution**: Specify emission order on error paths (emit diagnostic KVs to stdout, then `exit`) or document that SKILL must rely on exit code and filesystem artifacts only


### [Plan Review] FINDING_62

### FINDING_62: Full Step 3 today follows plan-review.md orchestration and never calls aggregate-findings.
- **Reviewer(s)**: Cursor-dyn-scope-creep
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md:691-707
- **Concern**: Full Step 3 today follows plan-review.md orchestration and never calls aggregate-findings.sh; the PR adds an LLM aggregation hop before ballot.txt. Scenario: Reviewer-visible ballot text and downstream tallies can diverge from the pre-PR orchestrator-only path for the same raw reviewer outputs
- **Proposed resolution**: Document this as an intentional behavioral addition or narrow the script to mechanical concatenation without LLM merge when true non-behavior is required


### [Plan Review] FINDING_63

### FINDING_63: Prose describes bypassing block_has_severity as a simple input guard matching if not block
- **Reviewer(s)**: Cursor-dyn-scope-creep
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: plan.txt:166-171
- **Concern**: Prose describes bypassing block_has_severity as a simple input guard matching if not block_has_severity return 1. Scenario: Implementers may patch the wrong validation layer when extending the embedded Python
- **Proposed resolution**: Mirror the real control flow: merged output blocks are scanned in aggregate-findings.sh:611-633 and severity is enforced there unless plan mode gates it


### [Plan Review] FINDING_65

### FINDING_65: Default code mode rejects merged blocks missing Severity while plan mode would accept the 
- **Reviewer(s)**: Cursor-dyn-scope-creep
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/review/scripts/aggregate-findings.sh:628-633
- **Concern**: Default code mode rejects merged blocks missing Severity while plan mode would accept the same bytes. Scenario: Accidental default invocation on plan-shaped ballots or future refactors could reintroduce silent AGGREGATED=false fallbacks
- **Proposed resolution**: Keep default INPUT_MODE=code, retain failing fixtures, and add a grep pin for --input-mode plan in plan-review-loop.sh as the plan already proposes


### [Plan Review] FINDING_67

### FINDING_67: Zero-findings short-circuit vs loop edge case
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/plan-review.md:108-109
- **Concern**: Zero-findings short-circuit vs loop edge case. Scenario: Normative text and SKILL.md:715 require skipping voters and writing a specific voting-tally.md sentinel when there are no findings; the plan Edge cases section instead runs full voter dispatch and tally on an empty ballot
- **Proposed resolution**: Implement the plan-review.md:108 path in plan-review-loop.sh (or explicitly amend plan-review.md + SKILL.md + Gate B expectations together with a regression test)


### [Plan Review] FINDING_68

### FINDING_68: Collector argv incompleteness
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/plan-review.md:91-96
- **Concern**: Collector argv incompleteness. Scenario: plan-review-loop.sh step 4 omits --substantive-validation --validation-mode --structured-reviewer-validation and uses default 1800s not 1860s; breaks substantive-validation contract #661 and scripts/test-design-structure.sh:216-229
- **Proposed resolution**: Mirror the single-line collect invocation from plan-review.md (and extend pins to assert those flags survive the refactor)


### [Plan Review] FINDING_69

### FINDING_69: Post-collection dirty-tree probe omitted
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/references/plan-review.md:98
- **Concern**: Post-collection dirty-tree probe omitted. Scenario: plan-review.md requires Mid-Run Dirty-Tree Probe (heavy-worker STAGE=plan-review-collection) immediately after collect returns; the proposed loop steps do not include it
- **Proposed resolution**: Either invoke the same probe from plan-review-loop.sh after collect or relocate the contract into SKILL.md with an explicit sequencing guarantee


### [Plan Review] FINDING_71

### FINDING_71: Misidentified shared parse-rate library
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/lib-voter-parse-rate.sh:1-32
- **Concern**: Misidentified shared parse-rate library. Scenario: lib-voter-parse-rate.sh only holds diag helpers; check_voter_parse_rate and check_and_retry_voter_parse_rate live in dispatch-code-voters.sh and are ballot-shape-specific
- **Proposed resolution**: Plan dispatch-plan-voters work to either factor real shared helpers or adapt plan-specific substantive checks (see existing check_plan_voter_substantive) instead of only sourcing lib-voter-parse-rate.sh


### [Plan Review] FINDING_72

### FINDING_72: Naive reuse of code voter parse-rate for plan ballots
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/dispatch-code-voters.sh:131-133
- **Concern**: Naive reuse of code voter parse-rate for plan ballots. Scenario: check_voter_parse_rate counts only ### FINDING_ headings in the ballot; OOS-only or OOS-heavy ballots yield ids_count=0 and short-circuit OK without validating OOS vote lines
- **Proposed resolution**: Extend parse-rate logic for FINDING|OOS vote grammar or keep plan-specific check_plan_voter_substantive for Claude plan voter


### [Plan Review] FINDING_74

### FINDING_74: Zero-findings short-circuit vs loop edge case
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/plan-review.md:108-109
- **Concern**: Zero-findings short-circuit vs loop edge case. Scenario: Normative text and SKILL.md:715 require skipping voters and writing a specific voting-tally.md sentinel when there are no findings; the plan Edge cases section instead runs full voter dispatch and tally on an empty ballot
- **Proposed resolution**: Implement the plan-review.md:108 path in plan-review-loop.sh (or explicitly amend plan-review.md + SKILL.md + Gate B expectations together with a regression test)


### [Plan Review] FINDING_75

### FINDING_75: Collector argv incompleteness
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/plan-review.md:91-96
- **Concern**: Collector argv incompleteness. Scenario: plan-review-loop.sh step 4 omits --substantive-validation --validation-mode --structured-reviewer-validation and uses default 1800s not 1860s; breaks substantive-validation contract #661 and scripts/test-design-structure.sh:216-229
- **Proposed resolution**: Mirror the single-line collect invocation from plan-review.md (and extend pins to assert those flags survive the refactor)


### [Plan Review] FINDING_76

### FINDING_76: Post-collection dirty-tree probe omitted
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/references/plan-review.md:98
- **Concern**: Post-collection dirty-tree probe omitted. Scenario: plan-review.md requires Mid-Run Dirty-Tree Probe (heavy-worker STAGE=plan-review-collection) immediately after collect returns; the proposed loop steps do not include it
- **Proposed resolution**: Either invoke the same probe from plan-review-loop.sh after collect or relocate the contract into SKILL.md with an explicit sequencing guarantee


### [Plan Review] FINDING_77

### FINDING_77: --input-mode plan targets wrong validator branch
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/scripts/aggregate-findings.sh:628-632
- **Concern**: --input-mode plan targets wrong validator branch. Scenario: The only block_has_severity enforcement today is on merged aggregator output blocks in main() not on raw input; gating only an imagined input check would still fail validation when merge output lacks Severity
- **Proposed resolution**: Extend --input-mode plan to skip merged-output severity validation (same gate as input would be wrong); update aggregate-findings.md accordingly


### [Plan Review] FINDING_78

### FINDING_78: Misidentified shared parse-rate library
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/lib-voter-parse-rate.sh:1-32
- **Concern**: Misidentified shared parse-rate library. Scenario: lib-voter-parse-rate.sh only holds diag helpers; check_voter_parse_rate and check_and_retry_voter_parse_rate live in dispatch-code-voters.sh and are ballot-shape-specific
- **Proposed resolution**: Plan dispatch-plan-voters work to either factor real shared helpers or adapt plan-specific substantive checks (see existing check_plan_voter_substantive) instead of only sourcing lib-voter-parse-rate.sh


### [Plan Review] FINDING_79

### FINDING_79: Naive reuse of code voter parse-rate for plan ballots
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/dispatch-code-voters.sh:131-133
- **Concern**: Naive reuse of code voter parse-rate for plan ballots. Scenario: check_voter_parse_rate counts only ### FINDING_ headings in the ballot; OOS-only or OOS-heavy ballots yield ids_count=0 and short-circuit OK without validating OOS vote lines
- **Proposed resolution**: Extend parse-rate logic for FINDING|OOS vote grammar or keep plan-specific check_plan_voter_substantive for Claude plan voter


### [Plan Review] FINDING_80

### FINDING_80: Dedup and in-scope-wins-OOS rules absent from ballot builder
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/plan-review.md:104-107
- **Concern**: Dedup and in-scope-wins-OOS rules absent from ballot builder. Scenario: plan-review.md requires separate dedup for in-scope vs OOS and merging duplicates that appear as both; proposed step 5 only concatenates renumbered blocks from raw reviewer files
- **Proposed resolution**: Specify and implement the same merge/dedup semantics before aggregation or document an intentional contract change with harness coverage


### [Plan Review] FINDING_82

### FINDING_82: Failure-modes text claims merged FINDING ids cannot drift because validator lines 614-619 
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: correctness
- **Location**: plan.txt:245-246 plus skills/review/scripts/aggregate-findings.sh:611-652
- **Concern**: Failure-modes text claims merged FINDING ids cannot drift because validator lines 614-619 bind output ids to input ids. Scenario: Those lines enforce duplicate merged ids and reviewer-slot membership (645-647); they do not prove every output ### FINDING_N: originated unchanged from a specific input heading
- **Proposed resolution**: Rephrase the mitigation to cite reviewer-slot and duplicate-id rules or add an explicit id-trace check if that invariant is truly required


### [Plan Review] FINDING_84

### FINDING_84: Parenthetical claims parse-rate helpers live in scripts/lib-voter-parse-rate.sh and can be
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:145-146
- **Concern**: Parenthetical claims parse-rate helpers live in scripts/lib-voter-parse-rate.sh and can be sourced there. Scenario: check_and_retry_voter_parse_rate and check_voter_parse_rate are defined in scripts/dispatch-code-voters.sh (lines 125-279); lib-voter-parse-rate.sh only holds small shared helpers (lines 1-32)
- **Proposed resolution**: Sourcing the library alone does not provide the planned discipline; either move the functions into lib-voter-parse-rate.sh (shared refactor) or explicitly port the dispatch-code-voters block into dispatch-plan-voters.sh


### [Plan Review] FINDING_85

### FINDING_85: UPDATED dispatch-plan-voters bullet names scripts/render-voter-prompt.sh
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: nit
- **Focus area**: correctness
- **Location**: plan.txt:139
- **Concern**: UPDATED dispatch-plan-voters bullet names scripts/render-voter-prompt.sh. Scenario: Actual contract path is skills/shared/scripts/render-voter-prompt.sh (used by dispatch-plan-voters.sh:45-48)
- **Proposed resolution**: Correct the plan and plan-review.md cross-references to skills/shared/scripts/render-voter-prompt.sh


### [Plan Review] FINDING_86

### FINDING_86: Failure-modes text claims merged FINDING ids cannot drift because validator lines 614-619 
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: correctness
- **Location**: plan.txt:245-246 plus skills/review/scripts/aggregate-findings.sh:611-652
- **Concern**: Failure-modes text claims merged FINDING ids cannot drift because validator lines 614-619 bind output ids to input ids. Scenario: Those lines enforce duplicate merged ids and reviewer-slot membership (645-647); they do not prove every output ### FINDING_N: originated unchanged from a specific input heading
- **Proposed resolution**: Rephrase the mitigation to cite reviewer-slot and duplicate-id rules or add an explicit id-trace check if that invariant is truly required


### [Plan Review] FINDING_87

### FINDING_87: Edge-case section says empty ballots still run dispatch-plan-voters and tally
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md:715-716 vs plan.txt:228-231
- **Concern**: Edge-case section says empty ballots still run dispatch-plan-voters and tally. Scenario: SKILL still instructs skipping voting when all reviewers report no issues, which implies no voter launches on a clean review
- **Proposed resolution**: Reconcile: add an explicit early-exit branch in plan-review-loop.sh when the constructed ballot has zero FINDING and OOS blocks, or update SKILL Step 3 prose to match the always-vote driver


### [Plan Review] FINDING_90

### FINDING_90: Testing strategy references a Makefile umbrella named test-design
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: nit
- **Focus area**: architecture
- **Location**: plan.txt:216-217
- **Concern**: Testing strategy references a Makefile umbrella named test-design. Scenario: There is no test-design phony target in Makefile (only test-design-structure, test-design-driver, test-design-log-publish, harness shards)
- **Proposed resolution**: Name the real shard or add an explicit new umbrella target so implementers wire CI consistently


### [Plan Review] FINDING_91

### FINDING_91: Plan implies sourcing lib-voter-parse-rate.sh supplies voter parse-rate retry discipline
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lib-voter-parse-rate.sh:1-32 vs scripts/dispatch-code-voters.sh:125-279
- **Concern**: Plan implies sourcing lib-voter-parse-rate.sh supplies voter parse-rate retry discipline. Scenario: Implementer sources only the small helper file and omits voter-1 parse-rate retries
- **Proposed resolution**: Port check_and_retry_voter_parse_rate (and deps) into lib-voter-parse-rate.sh with dispatch-code-voters refactor or explicitly duplicate the discipline for dispatch-plan-voters.sh


### [Plan Review] FINDING_92

### FINDING_92: Collector invocation omits substantive/validation flags and uses 1800s default vs 1860 con
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/plan-review.md:91-96 vs plan Step 4
- **Concern**: Collector invocation omits substantive/validation flags and uses 1800s default vs 1860 contract. Scenario: Banner-only outputs may pass as OK; diverges from issue #661 pin intent
- **Proposed resolution**: Match collect flags and timeout to plan-review.md or amend test-design-structure Check 7 with rationale


### [Plan Review] FINDING_94

### FINDING_94: Zero-findings path must skip voting; plan edge case runs voters on empty ballot
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:715-717 skills/design/references/plan-review.md:108
- **Concern**: Zero-findings path must skip voting; plan edge case runs voters on empty ballot. Scenario: Extra external launches and tally shape drift from documented /design flow
- **Proposed resolution**: Add explicit short-circuit matching SKILL + plan-review.md before dispatch-plan-voters


### [Plan Review] FINDING_95

### FINDING_95: Mid-run dirty-tree probe after plan-review collection not listed in loop steps
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/references/plan-review.md:98
- **Concern**: Mid-run dirty-tree probe after plan-review collection not listed in loop steps. Scenario: Uncaught dirty workspace during Step 3
- **Proposed resolution**: Invoke check-mid-run-dirty-tree.sh after collect or document an explicit waiver in normative refs


### [Plan Review] FINDING_96

### FINDING_96: compose-collector-failure-log + append-tool-failure for non-OK collector rows not carried 
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/references/plan-review.md:11-21
- **Concern**: compose-collector-failure-log + append-tool-failure for non-OK collector rows not carried into driver. Scenario: Partial collector failures lose structured execution-issues entries
- **Proposed resolution**: Port collector structured-parse + failure logging from current Step 3 prose into plan-review-loop.sh


### [Plan Review] FINDING_98

### FINDING_98: Plan cites scripts/render-voter-prompt.sh but repo path is skills/shared/scripts/render-vo
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: correctness
- **Location**: plan.txt:139
- **Concern**: Plan cites scripts/render-voter-prompt.sh but repo path is skills/shared/scripts/render-voter-prompt.sh. Scenario: Wrong file target in implementation notes
- **Proposed resolution**: Fix path references in plan + dispatch-plan-voters.md to match PLUGIN_ROOT skills/shared path


### [Plan Review] FINDING_99

### FINDING_99: Test expects VOTER_1_PARSE_RATE_STATUS but emit list omits that KV
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:147-161
- **Concern**: Test expects VOTER_1_PARSE_RATE_STATUS but emit list omits that KV. Scenario: Harness case 3 cannot pass as written
- **Proposed resolution**: Emit VOTER_1_PARSE_RATE_STATUS like dispatch-code-voters or adjust the test plan


