### FINDING_1: Proposed findings helper parses markdown headings, but plan reviewers are prompted to emit
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh (proposed Step 5); skills/design/scripts/render-plan-review-prompt.sh:92-101
- **Concern**: Proposed findings helper parses markdown headings, but plan reviewers are prompted to emit TSV or the JSON sentinel. Scenario: Valid Cursor/Codex reviewers return the required TSV block; the new helper looks only for ### FINDING_N / ### OOS_N blocks, builds an empty findings.md, and Step 3 silently loses real plan-review findings
- **Proposed resolution**: Parse the collector STRUCTURED_SIDECAR TSV/JSONL outputs and convert those records into ballot blocks, or update render-plan-review-prompt.sh, validate-research-output.sh, and tests in the same PR to use the markdown block contract end to end


### FINDING_10: The proposed panel-failed path is after an unconditional collect-agent-results.sh --paths-
- **Reviewer(s)**: Codex-dyn-kv-contract
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:27,35-38,73-74; skills/design/SKILL.md:97; scripts/collect-agent-results.sh:248-256
- **Concern**: The proposed panel-failed path is after an unconditional collect-agent-results.sh --paths-file call, but collect-agent-results.sh fail-closes on empty paths files before the loop can emit LOOP_STATUS=panel-failed. Scenario: The planned test case with DISPATCH_OK=false and empty reviewer outputs can exit from collect-agent-results.sh without emitting the parsed LOOP_STATUS/ACCEPTED_COUNT/DEGRADED_PANEL KVs, so SKILL.md cannot surface the intended hard failure state
- **Proposed resolution**: Add an explicit non-empty paths-file guard before collect-agent-results.sh; when the panel dispatcher reports DISPATCH_OK=false and there are zero usable reviewer paths, emit the loop KVs including LOOP_STATUS=panel-failed and exit 1 without calling collect-agent-results.sh


### FINDING_11: The proposed SKILL.md block does not capture plan-review-loop.sh exit status even though t
- **Reviewer(s)**: Codex-dyn-kv-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:47-50,94-113; skills/design/SKILL.md:856-862
- **Concern**: The proposed SKILL.md block does not capture plan-review-loop.sh exit status even though the loop uses exit 1 for panel-failed and exit 2 for argv/file errors. Scenario: In a non-errexit shell the assignment can swallow the loop failure and continue to Step 3.5 after parsing partial output; in an errexit shell the parser may not run, so the MAV/panel-failed KVs are not available to gate prose
- **Proposed resolution**: Wrap the loop invocation with set +e, capture _plan_review_rc, parse stdout, then explicitly branch: allow rc 0, run MAV prose when TALLY_PLAN_REVIEW_STATUS=main-agent-vote-required, and stop/surface diagnostics for rc 1 or 2 before Step 3.5


### FINDING_12: The plan is not a no-behavior refactor: current /design Step 3 does not invoke aggregate-f
- **Reviewer(s)**: Codex-dyn-scope-creep
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:5,29,247-255; skills/design/SKILL.md:650-706; skills/design/references/plan-review.md:104-118; skills/review/scripts/aggregate-findings.sh:746-748
- **Concern**: The plan is not a no-behavior refactor: current /design Step 3 does not invoke aggregate-findings.sh at all, while the proposed loop invokes it by default and accepts that byte-identical ballots are impossible.. Scenario: A multi-finding plan-review run that currently produces a manually deduped ballot and tallies that exact ballot can now have findings.md rewritten by the aggregator before ballot.txt is copied, changing ballot body, IDs, voter prompts, accepted/rejected artifacts, OOS artifacts, and scoreboard.
- **Proposed resolution**: Remove aggregator absorption from this refactor, or explicitly rescope the issue as a behavior change with separate acceptance criteria; preserve a byte-equivalence regression for the pure Step 3 script extraction path.


### FINDING_13: --input-mode plan changes observable aggregation outcomes by bypassing the current severit
- **Reviewer(s)**: Codex-dyn-scope-creep
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:28-29,76,164-179; skills/review/scripts/aggregate-findings.sh:240-248,620-633,746-748; agents/orchestrator-aggregator.md:25-37
- **Concern**: --input-mode plan changes observable aggregation outcomes by bypassing the current severity validator for no-severity plan ballots.. Scenario: Under current validator semantics, merged output without - **Severity** fails validation and leaves findings.md unchanged; the proposed flag makes the same shape AGGREGATED=true and permits findings.md replacement. The plan also leaves the aggregator prompt unchanged even though that prompt mandates severity, so tests expecting severity-free merged output conflict with the prompt contract.
- **Proposed resolution**: For no behavior change, keep strict validation and make plan-review helper emit severity if aggregation is retained; otherwise split --input-mode plan and no-severity aggregation into a separate behavior-changing issue and update the aggregator prompt/docs/tests consistently.


### FINDING_14: Proposed plan-review-loop parses markdown FINDING/OOS blocks even though plan reviewers ar
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/render-plan-review-prompt.sh:90-108; skills/review/scripts/collect-findings.sh:306-329
- **Concern**: Proposed plan-review-loop parses markdown FINDING/OOS blocks even though plan reviewers are prompted to emit TSV or JSON sentinel. Scenario: Reviewers obey the current prompt and return schema_version TSV rows; the new inline helper finds no ### FINDING_N or ### OOS_N headings, produces an empty findings.md, and /design silently treats real findings as no findings
- **Proposed resolution**: Reuse collect-findings.sh or the structured sidecars from collect-agent-results, or update render-plan-review-prompt.sh plus validators/tests so production reviewers emit the exact markdown block format the helper parses


### FINDING_15: Aggregator plan mode does not preserve OOS_N blocks
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/scripts/aggregate-findings.sh:176-183; skills/review/scripts/aggregate-findings.sh:610-652
- **Concern**: Aggregator plan mode does not preserve OOS_N blocks. Scenario: The proposed ballot can contain ### OOS_N blocks, but aggregate-findings.sh only splits and validates ### FINDING_N blocks; on a mixed finding plus OOS ballot a successful aggregation can replace findings.md with only FINDING blocks and silently drop accepted issue-filing observations
- **Proposed resolution**: Run aggregation only over in-scope FINDING blocks and append OOS blocks unchanged afterward, or extend aggregate-findings.sh, its validator, and tests to round-trip OOS_N blocks explicitly


### FINDING_16: Collector statuses are not consumed before building the ballot
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/collect-agent-results.sh:77-83; skills/design/references/plan-review.md:98-102
- **Concern**: Collector statuses are not consumed before building the ballot. Scenario: If every reviewer times out, fails validation, or produces empty output while output path files still exist, the proposed loop reads files directly, creates an empty ballot, and emits LOOP_STATUS=complete instead of surfacing panel collapse and logging External Reviewer Issues
- **Proposed resolution**: Parse collect-agent-results stdout, log every non-OK record using the existing failure contract, pass only STATUS=OK reviewer files into finding extraction, and return panel-failed when zero usable reviewer outputs remain


### FINDING_17: Plan removes the plan-review dirty-tree recovery boundary
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md:713; scripts/launch-review.sh:231-254
- **Concern**: Plan removes the plan-review dirty-tree recovery boundary. Scenario: The existing Step 3 checks launcher .dirty-tree sidecars and check-mid-run-dirty-tree.sh after external review collection; moving orchestration into plan-review-loop without that check lets Codex/Cursor mutations or unknown dirty state proceed into voting and Gate B
- **Proposed resolution**: Keep the SKILL.md boundary after the loop or implement the same sidecar scan plus checkpoint and recovery prompt inside plan-review-loop immediately after collection


### FINDING_18: Proposed SKILL.md wrapper can swallow plan-review-loop exit 1 or 2
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:650-687
- **Concern**: Proposed SKILL.md wrapper can swallow plan-review-loop exit 1 or 2. Scenario: The new script defines meaningful nonzero exits for panel-failed and argv/file errors, but the proposed command substitution block does not capture and re-exit on the script status; the subsequent parse loop can return success and Step 3 continues with unset LOOP_STATUS
- **Proposed resolution**: Capture the loop exit code with set +e around the command substitution, print/parse captured output, and exit nonzero or explicitly branch when the loop status is panel-failed or argv validation failed


### FINDING_19: Plan says dispatch-plan-voters can source parse-rate helpers that are not actually in the 
- **Reviewer(s)**: Codex-Edge
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/lib-voter-parse-rate.sh:1-16; scripts/dispatch-code-voters.sh:125-195
- **Concern**: Plan says dispatch-plan-voters can source parse-rate helpers that are not actually in the shared library. Scenario: The existing lib-voter-parse-rate.sh only contains diag path/hash helpers; check_voter_parse_rate and parse_rate_status_from_output remain local to dispatch-code-voters.sh, so a literal implementation of the plan leaves dispatch-plan-voters.sh with undefined functions or duplicated drift-prone logic
- **Proposed resolution**: Move the full parse-rate checker, status parser, tool-label, and harness-suppression helpers into lib-voter-parse-rate.sh and update both dispatchers to source the shared implementation, with tests covering Voter 1 retry/status KVs


### FINDING_2: Proposed collector call drops the existing validation and failure-reporting contract
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/plan-review-loop.sh (proposed Step 4); skills/design/references/plan-review.md:95-102
- **Concern**: Proposed collector call drops the existing validation and failure-reporting contract. Scenario: The plan calls collect-agent-results.sh with only --paths-file and --timeout, so non-substantive outputs are not downgraded, structured sidecars are not produced, and non-OK reviewer failures are not appended to execution-issues.md as the current Step 3 contract requires
- **Proposed resolution**: Invoke collect-agent-results.sh with --substantive-validation --validation-mode --structured-reviewer-validation, parse STATUS / REVIEWER_FILE / STRUCTURED_SIDECAR records, log every non-OK result through append-tool-failure.sh, and feed only validated structured records into ballot construction


### FINDING_20: Proposed OOS ballot construction does not require the canonical security token used by tal
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: security
- **Location**: skills/design/references/plan-review.md:146-148; scripts/lib-vote-tally.sh:56-68
- **Concern**: Proposed OOS ballot construction does not require the canonical security token used by tally security filtering. Scenario: Accepted security OOS is excluded from public oos.md and oos-accepted-design.md only when the block contains an unfenced focus-area = security token; the new helper contract only mentions Reviewer and Concern/Description lines, so security OOS can be serialized publicly after a YES vote
- **Proposed resolution**: When converting structured reviewer records to OOS_N blocks, preserve focus_area and emit an unfenced focus-area = security line for security records, or extend is_security_block to recognize the structured focus-area field that the helper writes


### FINDING_21: Proposed findings helper parses markdown FINDING/OOS blocks, but plan reviewers are prompt
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/render-plan-review-prompt.sh:90-108
- **Concern**: Proposed findings helper parses markdown FINDING/OOS blocks, but plan reviewers are prompted to emit TSV records. Scenario: The new loop can collect valid reviewer output and still produce an empty findings.md because there are no ### FINDING_N or ### OOS_N headings to extract
- **Proposed resolution**: Call collect-agent-results.sh with structured reviewer validation, consume STRUCTURED_SIDECAR outputs, and convert TSV rows into canonical FINDING_N/OOS_N ballot blocks with manifest-derived attribution


### FINDING_22: Collector invocation drops existing validation and failure-logging contract
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/references/plan-review.md:91-102
- **Concern**: Collector invocation drops existing validation and failure-logging contract. Scenario: Narrative or malformed reviewer output can be treated as usable input, while non-OK collector statuses stop being appended to execution-issues.md
- **Proposed resolution**: Use --substantive-validation --validation-mode --structured-reviewer-validation, parse collector result records, exclude non-OK entries, and preserve the compose-collector-failure-log.sh plus append-tool-failure.sh path


### FINDING_23: Aggregator path is FINDING-centric while the proposed ballot uses first-class OOS_N blocks
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: agents/orchestrator-aggregator.md:21-39
- **Concern**: Aggregator path is FINDING-centric while the proposed ballot uses first-class OOS_N blocks. Scenario: OOS observations may be ignored by aggregate-findings.sh validation, converted into FINDING_[OUT_OF_SCOPE], or pass through unvalidated, after which tally-plan-review.sh treats FINDING_* as in-scope plan findings
- **Proposed resolution**: Keep OOS_N blocks out of aggregate-findings.sh and append them after in-scope aggregation, or update the aggregator prompt, parser, validator, tests, and tally assumptions to support OOS_N as a first-class validated block type


### FINDING_24: Planned SKILL.md replacement captures plan-review-loop.sh stdout but does not check the sc
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:650-687
- **Concern**: Planned SKILL.md replacement captures plan-review-loop.sh stdout but does not check the script exit status. Scenario: A panel-failed exit 1 can be overwritten by the subsequent parse loop, leaving Step 3 to continue with unset LOOP_STATUS instead of surfacing the hard failure
- **Proposed resolution**: Capture rc with set +e around the command substitution, restore set -e if needed, and exit nonzero or explicitly branch on LOOP_STATUS=panel-failed before continuing


### FINDING_25: Dirty-tree probe is deleted from inline Step 3 and not reintroduced in plan-review-loop.sh
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: security
- **Location**: skills/design/SKILL.md:713
- **Concern**: Dirty-tree probe is deleted from inline Step 3 and not reintroduced in plan-review-loop.sh. Scenario: External reviewer or voter side effects can leave the repo dirty while /design proceeds into Gate B and later plan finalization
- **Proposed resolution**: Add the same check-mid-run-dirty-tree checkpoint and dirty-tree sidecar consultation inside plan-review-loop.sh after reviewer collection, and consider a second checkpoint after voter dispatch if voter subprocesses can write sidecars


### FINDING_26: Plan says dispatch-plan-voters.sh should source shared parse-rate helpers, but the existin
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: code-quality
- **Location**: scripts/lib-voter-parse-rate.sh:1-18
- **Concern**: Plan says dispatch-plan-voters.sh should source shared parse-rate helpers, but the existing library only contains diag helpers. Scenario: An implementation that merely sources lib-voter-parse-rate.sh will not provide check_voter_parse_rate or parse_rate_status_from_output, causing dispatch-plan-voters.sh to fail or duplicate stale logic
- **Proposed resolution**: Move the full parse-rate helpers from dispatch-code-voters.sh:125-193 into scripts/lib-voter-parse-rate.sh, update dispatch-code-voters.sh and dispatch-plan-voters.sh to source the shared implementations, and add tests for both callers


### FINDING_27: Panel-failed fallback assumes empty reviewer output can be classified after collection, bu
- **Reviewer(s)**: Codex-Innovation
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/collect-agent-results.sh:228-256
- **Concern**: Panel-failed fallback assumes empty reviewer output can be classified after collection, but collect-agent-results.sh exits on empty paths files. Scenario: When dispatch-plan-review-panel.sh returns DISPATCH_OK=false with no output paths, the loop may die at collection before emitting LOOP_STATUS=panel-failed
- **Proposed resolution**: Before invoking collect-agent-results.sh, detect a missing or empty PANEL_PATHS_FILE and emit LOOP_STATUS=panel-failed; alternatively wrap collector failure and map this specific empty-path condition to the planned panel-failed state


### FINDING_28: Proposed plan-review-loop parser expects ### FINDING_N/OOS_N blocks, but live plan reviewe
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/render-plan-review-prompt.sh:92-108
- **Concern**: Proposed plan-review-loop parser expects ### FINDING_N/OOS_N blocks, but live plan reviewers are instructed to emit TSV or the JSON no-issues sentinel; collect-agent-results only normalizes those TSV rows into sidecars when --structured-reviewer-validation is used.. Scenario: The new loop's Step 4 omits the validation flags and Step 5 parses raw reviewer files, so normal reviewer findings are not converted into ballot blocks; /design can complete with an empty ballot even when reviewers reported TSV findings.
- **Proposed resolution**: In plan-review-loop.sh call collect-agent-results with --substantive-validation --validation-mode --structured-reviewer-validation, consume only STATUS=OK records and STRUCTURED_SIDECAR paths, and build FINDING/OOS ballot blocks from normalized TSV rows rather than raw ### headings.


### FINDING_29: Aggregator absorption is planned for a combined ballot containing OOS_N blocks, but aggreg
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/scripts/aggregate-findings.sh:176-183
- **Concern**: Aggregator absorption is planned for a combined ballot containing OOS_N blocks, but aggregate-findings currently counts and validates only FINDING_N blocks.. Scenario: If findings.md has two in-scope findings plus OOS observations, a successful aggregate run can replace findings.md with output that validates while omitting all OOS blocks; tally then never writes those observations to oos.md or oos-accepted-design.md.
- **Proposed resolution**: Either aggregate only in-scope FINDING blocks and append untouched OOS blocks after success, or extend aggregate-findings counting, input/output validators, and prompts to treat OOS_N as first-class; add a mixed FINDING/OOS regression test.


### FINDING_3: Aggregator integration ignores OOS_N blocks
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh (proposed Step 6); skills/review/scripts/aggregate-findings.sh:176-183
- **Concern**: Aggregator integration ignores OOS_N blocks. Scenario: The plan feeds a mixed FINDING_N / OOS_N findings.md into aggregate-findings.sh, but that script splits and validates only ### FINDING_N blocks; when aggregation succeeds, OOS observations can be dropped before voting and never reach oos.md or oos-accepted-design.md
- **Proposed resolution**: Either aggregate only in-scope FINDING blocks and append OOS_N blocks unchanged after aggregation, or extend aggregate-findings.sh, its prompt, validator, and tests to parse, preserve, and validate OOS_N blocks explicitly


### FINDING_30: The proposed SKILL.md deletion moves Step 3 orchestration into plan-review-loop.sh but doe
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md:713
- **Concern**: The proposed SKILL.md deletion moves Step 3 orchestration into plan-review-loop.sh but does not preserve the plan-review dirty-tree checkpoint or recovery prompt contract.. Scenario: An external reviewer or fallback launcher can dirty the worktree during plan review; the flow then proceeds to Gate B with unreviewed local changes instead of stopping for recovery.
- **Proposed resolution**: Keep the dirty-tree boundary after collector completion: either leave a prompt-side check after plan-review-loop.sh or have the loop emit dirty-tree status/artifacts and require SKILL.md to run the existing recovery prompt before Step 3.5.


### FINDING_34: Empty-review behavior changes from the documented no-voting short-circuit to launching vot
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/plan-review.md:108
- **Concern**: Empty-review behavior changes from the documented no-voting short-circuit to launching voters against an empty ballot. Scenario: When all reviewers report no issues, the plan says voting still runs; this violates the no-behavior-change acceptance, changes voting-tally.md content, creates unnecessary voter artifacts, and can even route to main-agent-vote-required if all voters fail on an empty ballot
- **Proposed resolution**: Add an explicit zero-findings branch before dispatch-plan-voters.sh that writes the canonical no-voting tally plus empty accepted-plan-findings.md, rejected-findings.md, oos.md, and oos-accepted-design.md, then emits LOOP_STATUS=complete ACCEPTED_COUNT=0


### FINDING_36: The plan changes reviewer collection timeout from the stated 1860-second contract to plan-
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/plan-review.md:91-96
- **Concern**: The plan changes reviewer collection timeout from the stated 1860-second contract to plan-review-loop.sh's default 1800 seconds. Scenario: The feature description requires reviewer output collection via collect-agent-results.sh with --timeout 1860; using 1800 can prematurely time out reviewers relative to the existing Step 3 contract and fails the no-behavior-change goal
- **Proposed resolution**: Set the loop default or SKILL.md invocation to 1860 for collect-agent-results.sh, and keep any dispatch timeout distinction explicit if dispatch remains 1800


### FINDING_38: CI pins 14c1–14c3 still require scout wrapper dispatch-plan-review-panel and PANEL_PATHS_F
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/test-design-structure.sh:411-422
- **Concern**: CI pins 14c1–14c3 still require scout wrapper dispatch-plan-review-panel and PANEL_PATHS_FILE strings anywhere in skills/design/SKILL.md while the plan also requires those tokens disappear from Step 3 and greps them absent from SKILL for the new driver. Scenario: Implementer satisfies new plan-review-loop pins but either leaves stale tokens in SKILL (fails negative grep) or deletes prose tokens and fails 14c1–14c3
- **Proposed resolution**: Extend the plan: replace 14c1–14c3 with greps against skills/design/scripts/plan-review-loop.sh (or another stable contract surface) and drop the conflicting whole-file SKILL negative requirement for those three tokens


### FINDING_4: The plan relies on voter parse-rate helpers that are not in the shared library
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/dispatch-plan-voters.sh (proposed); scripts/lib-voter-parse-rate.sh:1-32
- **Concern**: The plan relies on voter parse-rate helpers that are not in the shared library. Scenario: scripts/lib-voter-parse-rate.sh currently contains only diagnostic path/hash helpers, while check_voter_parse_rate and check_and_retry_voter_parse_rate remain private in dispatch-code-voters.sh; following the plan literally leaves dispatch-plan-voters.sh with undefined functions or another local copy
- **Proposed resolution**: Make scripts/lib-voter-parse-rate.sh an actual shared implementation for parse-rate checking and retry orchestration, update dispatch-code-voters.sh and dispatch-plan-voters.sh to call it, and ensure the shared checker counts both FINDING_N and OOS_N IDs for plan ballots


### FINDING_40: New harness case asserts VOTER_1_PARSE_RATE_STATUS=OK but the UPDATED dispatch-plan-voters
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/dispatch-plan-voters.sh:121-240 scripts/test-dispatch-plan-voters.sh:158-161
- **Concern**: New harness case asserts VOTER_1_PARSE_RATE_STATUS=OK but the UPDATED dispatch-plan-voters section never requires emitting that KV pair (code path emits it via dispatch-code-voters.sh:399-434). Scenario: Test added in the plan cannot pass or implementers omit the status line breaking observability parity with code review
- **Proposed resolution**: Extend dispatch-plan-voters.sh spec to emit VOTER_1_PARSE_RATE_STATUS (and align naming with code voters) whenever parse-rate retry runs


### FINDING_41: SKILL.md still instructs skipping voting when all reviewers report no issues while the pla
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:715 skills/design/scripts/plan-review-loop.sh (planned)
- **Concern**: SKILL.md still instructs skipping voting when all reviewers report no issues while the plan’s driver always runs dispatch-plan-voters and tally including on an empty ballot. Scenario: Orchestrator may skip voting after the script already spent external budget or diverges from scripted Step 3 semantics
- **Proposed resolution**: Update SKILL prose and or add an early-exit branch in plan-review-loop.sh so skip-voting and the scripted path agree


### FINDING_42: The long MANDATORY plan-review.md paragraph still states scout plus dispatch-plan-review-p
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: code-quality
- **Location**: skills/design/SKILL.md:632-634
- **Concern**: The long MANDATORY plan-review.md paragraph still states scout plus dispatch-plan-review-panel Bash blocks live inline in SKILL.md below. Scenario: Contradicts the post-PR architecture and misleads implementers and agents reading the skill
- **Proposed resolution**: Rewrite that paragraph to name plan-review-loop.sh as the owner of scout panel collect aggregate vote tally and list what remains inline in SKILL.md


### FINDING_46: Text says extract helpers into lib then immediately says the library already exists and on
- **Reviewer(s)**: Cursor-dyn-conditional-dependency
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: plan.txt:144 (UPDATED dispatch-plan-voters.sh)
- **Concern**: Text says extract helpers into lib then immediately says the library already exists and only needs sourcing. Scenario: Contradictory implementation scope
- **Proposed resolution**: Choose one narrative extraction vs reuse vs plan-only helpers


### FINDING_5: SKILL.md replacement block does not preserve plan-review-loop.sh nonzero failures
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md (proposed Step 3 block); skills/design/scripts/plan-review-loop.sh (proposed exit codes)
- **Concern**: SKILL.md replacement block does not preserve plan-review-loop.sh nonzero failures. Scenario: The plan-review-loop.sh contract exits 1 for panel-failed, but the proposed SKILL.md command substitution is followed by parsing commands and no rc check, so a panel-failed run can be converted into an apparently successful Bash block with empty LOOP_STATUS
- **Proposed resolution**: Wrap the plan-review-loop.sh invocation in set +e / rc capture, parse stdout regardless, and explicitly surface or exit when rc is nonzero or LOOP_STATUS=panel-failed; alternatively make the loop always exit 0 for machine-readable terminal states and let SKILL.md branch solely on LOOP_STATUS


### FINDING_58: MAV guidance contradicts itself: L126 says `LOOP_STATUS=main-agent-vote-required` triggers
- **Reviewer(s)**: Cursor-dyn-kv-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: session implementation plan (cache `.../plan.txt` L126-L128)
- **Concern**: MAV guidance contradicts itself: L126 says `LOOP_STATUS=main-agent-vote-required` triggers the MAV paragraph; L128 says the paragraph is reached when `TALLY_PLAN_REVIEW_STATUS` equals `main-agent-vote-required`. Scenario: Implementers may gate SKILL prose on the wrong variable or leave dead text if `LOOP_STATUS` and tally status ever diverge
- **Proposed resolution**: Pick one normative predicate (recommend keeping `TALLY_PLAN_REVIEW_STATUS` to match current SKILL.md L709) and delete the conflicting sentence


### FINDING_6: The plan says lib-voter-parse-rate.sh exists and dispatch-plan-voters.sh can just source i
- **Reviewer(s)**: Codex-dyn-conditional-dependency
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:135-148; scripts/lib-voter-parse-rate.sh:4-31; scripts/dispatch-code-voters.sh:125-279
- **Concern**: The plan says lib-voter-parse-rate.sh exists and dispatch-plan-voters.sh can just source it for check_and_retry_voter_parse_rate/check_voter_parse_rate, but the current library only exports diagnostic path/hash helpers; the requested parse-rate functions still live inside dispatch-code-voters.sh.. Scenario: An implementer following the plan will source scripts/lib-voter-parse-rate.sh and call check_and_retry_voter_parse_rate/check_voter_parse_rate from scripts/dispatch-plan-voters.sh, producing command-not-found failures or forcing ad hoc duplication of the code-review helpers.
- **Proposed resolution**: Add an explicit UPDATED scripts/lib-voter-parse-rate.sh section that moves check_voter_parse_rate, parse_rate_status_from_output, check_and_retry_voter_parse_rate, and required dependencies into the library with parameters for ballot file, tmpdir, prompt retry renderer, launcher, and issue-log suppression; then update both dispatch-code-voters.sh and dispatch-plan-voters.sh to source the shared API.


### FINDING_61: Testing strategy admits byte-identical session artifacts are impossible while the issue is
- **Reviewer(s)**: Cursor-dyn-scope-creep
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:247-256
- **Concern**: Testing strategy admits byte-identical session artifacts are impossible while the issue is framed as NO behavior change. Scenario: Acceptance criteria contradict the headline refactor scope; manual diff gate cannot prove non-behavioral change
- **Proposed resolution**: Rescope the issue body or split aggregation and severity-mode into a follow-up; make semantic-only equivalence the explicit acceptance contract in the issue and in plan-review-loop.md


### FINDING_64: SECURITY.md models plan-review voters as Codex or Cursor via run-external-agent.sh and doe
- **Reviewer(s)**: Cursor-dyn-scope-creep
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:40-44
- **Concern**: SECURITY.md models plan-review voters as Codex or Cursor via run-external-agent.sh and does not mention Claude subprocess voters or pre-vote aggregation under DESIGN_TMPDIR. Scenario: Security reviewers lose an accurate map of external delegation and argv-hardening expectations for the new lanes
- **Proposed resolution**: Update SECURITY.md in the same change set per AGENTS.md guidance when security-relevant delegation changes


### FINDING_66: Collector argv contract not carried into plan-review-loop step 4
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/plan-review.md:91-96
- **Concern**: Collector argv contract not carried into plan-review-loop step 4. Scenario: Plan only passes --paths-file and TIMEOUT default 1800s; normative plan-review uses --timeout 1860 plus --substantive-validation --validation-mode --structured-reviewer-validation so ballot inputs and NOT_SUBSTANTIVE handling can drift from today’s contract
- **Proposed resolution**: Mirror the full collect invocation from plan-review.md (or update plan-review.md and harnesses together) and align default timeout with 1860s discipline


### FINDING_7: dispatch-plan-review-panel.sh is already present, so the loop need not implement an absenc
- **Reviewer(s)**: Codex-dyn-conditional-dependency
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:26-34; <TMPDIR>/plan.txt:66-76; skills/design/scripts/dispatch-plan-review-panel.sh:130-180; skills/design/scripts/test-dispatch-plan-review-panel.sh:115-169
- **Concern**: dispatch-plan-review-panel.sh is already present, so the loop need not implement an absence fallback, but the proposed plan-review-loop harness does not exercise the usable degraded panel path it must parse from that dispatcher.. Scenario: Existing dispatcher tests cover DEGRADED_ROUND boundaries in isolation, but the new loop can still misparse STATIC_DISPATCH_OK/FALLBACK_COUNT or fail to set DEGRADED_PANEL=1 while continuing to collect reviewers and tally; the listed loop tests only cover happy path and total panel-failed collapse.
- **Proposed resolution**: Add a plan-review-loop test case where the dispatcher stub returns DISPATCH_OK=true plus valid reviewer paths and either STATIC_DISPATCH_OK=false or FALLBACK_COUNT greater than half; assert collect/tally still run, LOOP_STATUS=complete, and DEGRADED_PANEL=1.


### FINDING_70: --input-mode plan targets wrong validator branch
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/scripts/aggregate-findings.sh:628-632
- **Concern**: --input-mode plan targets wrong validator branch. Scenario: The only block_has_severity enforcement today is on merged aggregator output blocks in main() not on raw input; gating only an imaginary input check would still fail validation when merge output lacks Severity
- **Proposed resolution**: Extend --input-mode plan to skip merged-output severity validation (same gate as input would be wrong); update aggregate-findings.md accordingly


### FINDING_73: Dedup and in-scope-wins-OOS rules absent from ballot builder
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/plan-review.md:104-107
- **Concern**: Dedup and in-scope-wins-OOS rules absent from ballot builder. Scenario: plan-review.md requires separate dedup for in-scope vs OOS and merging duplicates that appear as both; proposed step 5 only concatenates renumbered blocks from raw reviewer files
- **Proposed resolution**: Specify and implement the same merge/dedup semantics before aggregation or document an intentional contract change with harness coverage


### FINDING_8: VOTING_TALLY_FILE is promised by the plan-review-loop stdout protocol and emitted by tally
- **Reviewer(s)**: Codex-dyn-kv-contract
- **Severity**: latent
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:39-45,104-113; skills/design/scripts/tally-plan-review.sh:105-110,214-215
- **Concern**: VOTING_TALLY_FILE is promised by the plan-review-loop stdout protocol and emitted by tally-plan-review.sh, but the proposed SKILL.md parser does not initialize or parse it. Scenario: Any downstream Step 3 prose, diagnostics, or future Step 3.5/4/5 condition that relies on the propagated tally path will see an empty/unset variable despite the loop having emitted the KV
- **Proposed resolution**: Add VOTING_TALLY_FILE="" beside TALLY_PLAN_REVIEW_STATUS and include VOTING_TALLY_FILE in the parser case arm; add a harness assertion that SKILL.md parses every loop protocol KV


### FINDING_81: UPDATED dispatch-plan-voters bullet names scripts/render-voter-prompt.sh
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: nit
- **Focus area**: correctness
- **Location**: plan.txt:139
- **Concern**: UPDATED dispatch-plan-voters bullet names scripts/render-voter-prompt.sh. Scenario: Actual contract path is skills/shared/scripts/render-voter-prompt.sh (used by dispatch-plan-voters.sh:45-48)
- **Proposed resolution**: Correct the plan and plan-review.md cross-references to skills/shared/scripts/render-voter-prompt.sh


### FINDING_83: Testing strategy references a Makefile umbrella named test-design
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: nit
- **Focus area**: architecture
- **Location**: plan.txt:216-217
- **Concern**: Testing strategy references a Makefile umbrella named test-design. Scenario: There is no test-design phony target in Makefile (only test-design-structure, test-design-driver, test-design-log-publish, harness shards)
- **Proposed resolution**: Name the real shard or add an explicit new umbrella target so implementers wire CI consistently


### FINDING_88: After moving panel/collect into plan-review-loop.sh, the paragraph that describes parsing 
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: code-quality
- **Location**: skills/design/SKILL.md:689-693
- **Concern**: After moving panel/collect into plan-review-loop.sh, the paragraph that describes parsing PANEL_PATHS_FILE from the preceding bash loop likely remains. Scenario: Operators read contradictory Step-3 instructions relative to the new single invocation block
- **Proposed resolution**: Rewrite or delete the stale narrative so it points at plan-review-loop outputs and preserves the dirty-tree checkpoint ordering


### FINDING_89: New harness asserts DISPATCH_OK=false when Voter 1 fails but UPDATED dispatch-plan-voters 
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:158-161 plus scripts/dispatch-plan-voters.sh:93-240
- **Concern**: New harness asserts DISPATCH_OK=false when Voter 1 fails but UPDATED dispatch-plan-voters bullets omit tightening DISPATCH_OK. Scenario: dispatch-plan-voters.sh only forwards DISPATCH_OK from dispatch-with-waterfall.sh today; Voter 2/3 empty output does not flip DISPATCH_OK
- **Proposed resolution**: Mirror scripts/dispatch-code-voters.sh:450-451 (set DISPATCH_OK false when VOTER_1_STATUS is failed) in the plan’s dispatch-plan-voters checklist so tests and behavior align


### FINDING_9: The plan parses DISPATCH_OK from both panel dispatch and voter dispatch without requiring 
- **Reviewer(s)**: Codex-dyn-kv-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:26,31,35-38; skills/design/scripts/dispatch-plan-review-panel.sh:141-156; scripts/dispatch-plan-voters.sh:93-104,233-240
- **Concern**: The plan parses DISPATCH_OK from both panel dispatch and voter dispatch without requiring distinct variable names, but LOOP_STATUS=panel-failed is defined in terms of the panel dispatcher result. Scenario: Voter dispatch can overwrite the panel DISPATCH_OK value before Step 12 decides LOOP_STATUS, making panel-failed misclassify or become unreachable depending implementation order
- **Proposed resolution**: Specify separate variables such as PANEL_DISPATCH_OK and VOTER_DISPATCH_OK in plan-review-loop.sh; use PANEL_DISPATCH_OK for panel-failed and VOTER_DISPATCH_OK only for voter degradation diagnostics


### FINDING_93: Check 7 requires one plan-review.md line with collect + timeout 1860 + substantive + valid
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-design-structure.sh:216-229
- **Concern**: Check 7 requires one plan-review.md line with collect + timeout 1860 + substantive + validation. Scenario: CI fails if collect moves to script and the MD line is split or flags drop
- **Proposed resolution**: Update plan-review.md canonical one-liner or change Check 7 in the same PR with documented tradeoff


### FINDING_97: Failure modes promise aggregate-findings --input-mode plan pin; test-design-structure list
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:241 vs plan.txt:194-209
- **Concern**: Failure modes promise aggregate-findings --input-mode plan pin; test-design-structure list omits it. Scenario: Regression could ship without the promised earliest-warning grep
- **Proposed resolution**: Add grep literal --input-mode plan to test-design-structure.sh pins or revise Failure modes text


