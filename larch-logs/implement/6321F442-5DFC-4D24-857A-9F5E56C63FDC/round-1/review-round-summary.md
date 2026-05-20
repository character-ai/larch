# Review Round 1

- Mode: `diff`
- Accepted findings: 33
- Rejected findings: 1
- Exonerated findings: 0
- Neutral findings: 0

## Accepted Findings

### FINDING_1: **Important** `risk-integration` [skills/review/scripts/dispatch-panel.sh:117](<OPERATOR_REPO_PATH>/skills/review/scripts/dispatch-panel.sh:117), [scripts/dispatch-code-voters.sh:367](<OPERATOR_REPO_PATH>/scripts/dispatch-code-voters.sh:367) — Codex can still run in round 2+ through the existing waterfall fallback. The patch removes Codex-primary reviewer/voter slots, but both remaining Cursor-primary paths still call `dispatch-with-waterfall.sh` with `--codex-present "$CODEX_AVAILABLE"`; when `ROUND_NUM=2`, `CURSOR_AVAILABLE=false` or Cursor phase 1 fails, [dispatch-with-waterfall.sh:283](<OPERATOR_REPO_PATH>/scripts/dispatch-with-waterfall.sh:283)-289 picks `alt=codex` and launches Codex for every Cursor specialist slot and for `voter-3`. Concrete scenario: `/implement` round 2 with Codex available and Cursor unavailable produces Codex review/vote output despite the feature requiring Codex reviewers/voter to be round-1-only. Set the waterfall Codex presence to `false` for review/voter dispatch when `ROUND_NUM != 1` (or add an explicit waterfall option to disable Codex fallback for these round-2+ calls), and add harness coverage for round 2 with Cursor absent and Codex present.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `risk-integration` [skills/review/scripts/dispatch-panel.sh:117](<OPERATOR_REPO_PATH>/skills/review/scripts/dispatch-panel.sh:117), [scripts/dispatch-code-voters.sh:367](<OPERATOR_REPO_PATH>/scripts/dispatch-code-voters.sh:367) — Codex can still run in round 2+ through the existing waterfall fallback. The patch removes Codex-primary reviewer/voter slots, but both remaining Cursor-primary paths still call `dispatch-with-waterfall.sh` with `--codex-present "$CODEX_AVAILABLE"`; when `ROUND_NUM=2`, `CURSOR_AVAILABLE=false` or Cursor phase 1 fails, [dispatch-with-waterfall.sh:283](<OPERATOR_REPO_PATH>/scripts/dispatch-with-waterfall.sh:283)-289 picks `alt=codex` and launches Codex for every Cursor specialist slot and for `voter-3`. Concrete scenario: `/implement` round 2 with Codex available and Cursor unavailable produces Codex review/vote output despite the feature requiring Codex reviewers/voter to be round-1-only. Set the waterfall Codex presence to `false` for review/voter dispatch when `ROUND_NUM != 1` (or add an explicit waterfall option to disable Codex fallback for these round-2+ calls), and add harness coverage for round 2 with Cursor absent and Codex present.
- **Suggested revision**: Address the concern above.


### FINDING_11: architecture: docs/voting-process.md:37-38
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Prose claims both skills always use 3-voter panels; contradicts /review round 2+ table. Readers infer /review always has three judges every round. Rewrite the sentence to reflect round-dependent /review composition.
- **Suggested revision**: Address the concern above.


### FINDING_12: code-quality: docs/voting-process.md:37-38
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Lead paragraph claims both skills always use 3-voter panels while the same section table documents /review round 2+ as 2-voter. Operators and maintainers read conflicting rules in one doc section. Rewrite the paragraph to scope 3-voter to /design and round-1 /review or qualify /review by round.
- **Suggested revision**: Address the concern above.


### FINDING_13: code-quality: scripts/dispatch-code-voters.md:20-30
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Still documents three voter dispatches, joint V2+V3 waterfall, and a fixed two-slot manifest. Round 2+ only runs the Cursor waterfall slot; docs misdescribe runtime. Make Behavior/Voter-role sections conditional on round (1 vs 2+).
- **Suggested revision**: Address the concern above.


### FINDING_14: code-quality: scripts/dispatch-code-voters.sh:14-15
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] usage() omits --round-num despite the flag being part of the public CLI. Operators relying on --help may miss round-aware behavior. Add --round-num to the usage string.
- **Suggested revision**: Address the concern above.


### FINDING_15: code-quality: scripts/dispatch-code-voters.sh:14-15
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] usage() omits --round-num flag. Harder to discover CLI contract from --help path. Add --round-num to usage string.
- **Suggested revision**: Address the concern above.


### FINDING_16: code-quality: scripts/dispatch-code-voters.sh:14-16
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] usage() omits --round-num. Operators invoking --help miss the new flag. Add [--round-num N] to usage.
- **Suggested revision**: Address the concern above.


### FINDING_17: code-quality: scripts/dispatch-code-voters.sh:14-16
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] usage() omits --round-num. Operators using --help see an incomplete contract vs dispatch-code-voters.md. Extend usage() to list [--round-num N].
- **Suggested revision**: Address the concern above.


### FINDING_18: code-quality: scripts/dispatch-code-voters.sh:14-16
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] usage() omits --round-num. Operators discover the flag only from errors or deep docs. Extend usage string with [--round-num N].
- **Suggested revision**: Address the concern above.


### FINDING_19: code-quality: skills/implement/SKILL.md:154
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] --no-dynamic-archetypes text still claims 7 static SIMPLE slots every round. After change, round 2+ SIMPLE is 6 slots; doc is false for follow-up rounds. Update bullet to round-1 vs round-2+ slot counts.
- **Suggested revision**: Address the concern above.


### FINDING_20: code-quality: skills/review/scripts/review-core.sh:470-472
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Stale 3-judge comment above voter dispatch. Maintainer confusion only. Update comment for round-aware panels.
- **Suggested revision**: Address the concern above.


### FINDING_21: code-quality: skills/review/scripts/review-core.sh:470-472
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Stale 3-judge comment above voter dispatch. Maintainers may assume three judges every round when debugging round 2+ runs. Update comment to describe round-dependent judge count.
- **Suggested revision**: Address the concern above.


### FINDING_22: code-quality: skills/review/scripts/review-core.sh:470-472
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Stale comment refers to a fixed 3-judge panel. Future edits may assume Codex always votes. Update comment to describe round-dependent dispatch.
- **Suggested revision**: Address the concern above.


### FINDING_23: code-quality: skills/review/scripts/review-core.sh:470-472
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Stale 3-judge comment above voter dispatch. Future edits may assume fixed 3-judge tally input. Update comment to mention round-dependent judge count.
- **Suggested revision**: Address the concern above.


### FINDING_24: correctness: docs/voting-process.md:35-38
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Lead prose still claims both skills use 3-voter panels everywhere. Contradicts new /review round 2+ two-voter behavior in the same document; misleads operators and anyone calibrating quorum rules. Rewrite the section lead to distinguish /design vs /review by round and align with the table below.
- **Suggested revision**: Address the concern above.


### FINDING_25: correctness: docs/voting-process.md:36-38
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Heading claims both skills always use 3-voter panels contradicting /review round 2+ table. Readers infer /review always has three judges. Rewrite sentence to exclude /review follow-up rounds or reference round-specific table.
- **Suggested revision**: Address the concern above.


### FINDING_26: correctness: docs/voting-process.md:38
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Stale prose claims both skills always use 3-voter panels while the same doc describes 2-voter /review rounds 2+. Readers see contradictory voting topology in one document. Rewrite the sentence to distinguish /design vs /review and rounds.
- **Suggested revision**: Address the concern above.


### FINDING_27: correctness: scripts/dispatch-code-voters.sh:46
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] ROUND_NUM=0 passes digit validation but contradicts positive-integer error copy. ROUND_NUM=0 skips Codex like round 2+ with unclear contract. Require ((10#$ROUND_NUM>0)) like review-and-fix.sh.
- **Suggested revision**: Address the concern above.


### FINDING_28: correctness: scripts/dispatch-code-voters.sh:46
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Round validation is digits-only; 0 and values like 01 are accepted but do not match ROUND_NUM==1. A buggy or oddly formatted round label could skip Codex on the intended first round. Enforce positive integer semantics or normalize (strip leading zeros) before the round-1 gate.
- **Suggested revision**: Address the concern above.


### FINDING_29: correctness: scripts/dispatch-code-voters.sh:46
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] ROUND_NUM validation allows 0 while docs say positive integer; 0 omits Codex like round 2+. Surprising behavior if a caller passes --round-num 0. Reject 0 or document explicitly.
- **Suggested revision**: Address the concern above.


### FINDING_3: **code-quality** — [`scripts/dispatch-code-voters.sh:14-16`](scripts/dispatch-code-voters.sh): `usage()` does not document `[--round-num N]` even though the script parses `--round-num` ([`scripts/dispatch-code-voters.sh:25-53`](scripts/dispatch-code-voters.sh)). **Suggested fix:** extend the usage string (and keep `dispatch-code-voters.md` as the fuller contract).
- **Reviewer**: dyn-voter-integration-output.txt
- **Concern**: - **code-quality** — [`scripts/dispatch-code-voters.sh:14-16`](scripts/dispatch-code-voters.sh): `usage()` does not document `[--round-num N]` even though the script parses `--round-num` ([`scripts/dispatch-code-voters.sh:25-53`](scripts/dispatch-code-voters.sh)). **Suggested fix:** extend the usage string (and keep `dispatch-code-voters.md` as the fuller contract).
- **Suggested revision**: Address the concern above.


### FINDING_30: correctness: scripts/dispatch-code-voters.sh:46 skills/review/scripts/dispatch-panel.sh:81 skills/review/scripts/review-core.sh:69
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Digit-only ROUND_NUM validation accepts 0 while messaging says positive integer. ROUND_NUM=0 skips Codex like round 2+ without matching review-and-fix validation. Add (( 10#$ROUND_NUM > 0 )) or equivalent after digit check in each script.
- **Suggested revision**: Address the concern above.


### FINDING_31: correctness: scripts/dispatch-code-voters.sh:53-65
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Voter prompt always describes a 3-judge panel. Round 2+ Cursor voter gets mismatched framing vs actual 2-judge unanimous rule. Parameterize prompt text by ROUND_NUM.
- **Suggested revision**: Address the concern above.


### FINDING_32: correctness: skills/review/scripts/check-reviewer-failure-threshold.sh:32-110;skills/review/scripts/review-core.sh:348-351
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Fixed INTENDED_SLOTS (12 hard / 7 simple) with launched_slots from dispatch after round-2+ Codex omission adds six phantom never-launched failures for HARD. On HARD panel ROUND_NUM>=2 one counted specialist failure yields FAILED_SLOTS=1+NEVER_LAUNCHED>=7>=HALF_PLUS_ONE_MIN(7) and THRESHOLD_OK=false spurious panel-failed. Make intended denominator round-aware or emit/pass intended static slot count from dispatch-panel.
- **Suggested revision**: Address the concern above.


### FINDING_33: correctness: skills/review/scripts/check-reviewer-failure-threshold.sh:32-119 + skills/review/scripts/review-core.sh:350-351 + skills/review/scripts/dispatch-panel.sh (round 2+ static slots)
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] INTENDED_SLOTS stays 12/7 while LAUNCHED_SLOTS drops to 6 in round 2+; NEVER_LAUNCHED adds omitted Codex slots as failures. HARD round 2+: six phantom failures each round (12-6); threshold ceil is 7 so any one real specialist failure yields FAILED_SLOTS>=7 and REVIEW_CORE_STATUS=panel-failed / exit 2, stalling /implement and /fix-issue multi-round HARD reviews. Thread round-aware intended static slot count (or pass explicit denominator) into check-reviewer-failure-threshold.sh so omitted-by-policy slots are not counted as never-launched vendor failures.
- **Suggested revision**: Address the concern above.


### FINDING_34: risk-integration: scripts/dispatch-code-voters.sh:46-53
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Digit-only ROUND_NUM validation allows 0 while messaging says positive integer. Direct script invocation with --round-num 0 skips Codex like round 2+ without tripping review-and-fix.sh's stricter guard. Reject ROUND_NUM<1 the same way review-and-fix.sh does.
- **Suggested revision**: Address the concern above.


### FINDING_35: risk-integration: scripts/dispatch-code-voters.sh:49-54 (make_voter_prompt_file)
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Voter prompt still says 3-judge panel for all rounds. On round 2+ models may calibrate confidence or tie-breaks as if a third judge exists. Make the opening sentence depend on ROUND_NUM (or effective judge count).
- **Suggested revision**: Address the concern above.


### FINDING_36: risk-integration: scripts/dispatch-code-voters.sh:49-66
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Voter prompts always describe a 3-judge panel even when round 2+ omits Codex. Judge models may apply the wrong mental model of quorum / dissent vs the actual 2-judge unanimous tally, skewing YES/NO/EXONERATE behavior vs protocol. Parameterize prompt copy on ROUND_NUM or expected_judge_count.
- **Suggested revision**: Address the concern above.


### FINDING_37: risk-integration: scripts/test-dispatch-code-voters.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] No harness coverage for --round-num 2+ voter dispatch (manifest skip Codex expected_judges degraded warning parse-rate). Regression in dispatch-code-voters.sh ROUND_NUM branch can merge with green CI while breaking 2-judge rounds or false degraded warnings. Add a test-dispatch-code-voters.sh scenario asserting --round-num 2 KVs manifest shape skipped voter2 and degraded warning threshold 2.
- **Suggested revision**: Address the concern above.


### FINDING_38: risk-integration: skills/implement/SKILL.md:154
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] --no-dynamic-archetypes still documents 7 static slots every round including Codex. Misaligned with round-1-only Codex on SIMPLE path. Qualify Codex generalist and slot count as round 1 only.
- **Suggested revision**: Address the concern above.


### FINDING_39: risk-integration: skills/implement/SKILL.md:154
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] --no-dynamic-archetypes still claims 7 static slots including Codex every round. Operators mis-size parallel reviewer cost or expect Codex generalist on rounds 2+ of SIMPLE review. Update text to round-1 vs round-2+ static slot counts matching dispatch-panel.sh.
- **Suggested revision**: Address the concern above.


### FINDING_4: **risk-integration** — [`skills/review/scripts/check-reviewer-failure-threshold.sh:32-41`](skills/review/scripts/check-reviewer-failure-threshold.sh) and [`skills/review/scripts/check-reviewer-failure-threshold.sh:104-109`](skills/review/scripts/check-reviewer-failure-threshold.sh): `INTENDED_SLOTS` for `hard` is hard-coded to **12**, but on round 2+ [`skills/review/scripts/dispatch-panel.sh:117-130`](skills/review/scripts/dispatch-panel.sh) only queues **6** static Cursor slots, so [`skills/review/scripts/review-core.sh:350-356`](skills/review/scripts/review-core.sh) passes `--launched-slots` equal to **6**. The script then does `NEVER_LAUNCHED=$((INTENDED_SLOTS - LAUNCHED_SLOTS))` and adds that to `FAILED_SLOTS`, which **always injects six “never launched” failures** for slots that were intentionally omitted, not skipped by vendor health. With `HALF_PLUS_ONE_MIN=$((12/2+1))` (= **7**), **any one genuine static failure** from the collector (e.g. one `NOT_SUBSTANTIVE` or bad slot) yields `1 + 6 >= 7` and forces `THRESHOLD_OK=false` / `panel-failed`, i.e. a false hard-stop relative to the real 6-slot panel. **Suggested fix:** drive `INTENDED_SLOTS` from the same round-aware static layout as the manifest (e.g. new KV from `dispatch-panel.sh`, or a `--round-num` / `--static-intended-slots` argument to this script), so round 2+ HARD uses **6** not **12**.
- **Reviewer**: dyn-voter-integration-output.txt
- **Concern**: - **risk-integration** — [`skills/review/scripts/check-reviewer-failure-threshold.sh:32-41`](skills/review/scripts/check-reviewer-failure-threshold.sh) and [`skills/review/scripts/check-reviewer-failure-threshold.sh:104-109`](skills/review/scripts/check-reviewer-failure-threshold.sh): `INTENDED_SLOTS` for `hard` is hard-coded to **12**, but on round 2+ [`skills/review/scripts/dispatch-panel.sh:117-130`](skills/review/scripts/dispatch-panel.sh) only queues **6** static Cursor slots, so [`skills/review/scripts/review-core.sh:350-356`](skills/review/scripts/review-core.sh) passes `--launched-slots` equal to **6**. The script then does `NEVER_LAUNCHED=$((INTENDED_SLOTS - LAUNCHED_SLOTS))` and adds that to `FAILED_SLOTS`, which **always injects six “never launched” failures** for slots that were intentionally omitted, not skipped by vendor health. With `HALF_PLUS_ONE_MIN=$((12/2+1))` (= **7**), **any one genuine static failure** from the collector (e.g. one `NOT_SUBSTANTIVE` or bad slot) yields `1 + 6 >= 7` and forces `THRESHOLD_OK=false` / `panel-failed`, i.e. a false hard-stop relative to the real 6-slot panel. **Suggested fix:** drive `INTENDED_SLOTS` from the same round-aware static layout as the manifest (e.g. new KV from `dispatch-panel.sh`, or a `--round-num` / `--static-intended-slots` argument to this script), so round 2+ HARD uses **6** not **12**.
- **Suggested revision**: Address the concern above.


### FINDING_41: risk-integration: skills/review/scripts/test-dispatch-panel.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] No new assertions for ROUND_NUM>1 static slot counts after dispatch-panel Codex gating. Regression could re-expand Codex slots without failing CI. Add harness cases for simple/hard round 2 STATIC_SLOT_COUNT/SLOT_COUNT expectations.
- **Suggested revision**: Address the concern above.


