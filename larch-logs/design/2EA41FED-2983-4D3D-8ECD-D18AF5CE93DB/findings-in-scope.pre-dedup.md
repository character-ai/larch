### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: docs/workflow-lifecycle.md:78-79
- **Concern**: Proposed title Step 5 external-stop recovery collides with /design finalize Step 5 in the preceding bullet. Scenario: The /design bullet ends with Finalize (Step 5) for 5b/5c; the new sibling title Step 5 external-stop recovery reads as another design-step note and can send operators to the wrong recovery playbook
- **Proposed resolution**: Title the new bullet /implement Step 5 external-stop recovery and open with code-review or review-and-fix context like the Step 3 plan-review anchor



### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: docs/workflow-lifecycle.md:79
- **Concern**: Content intent uses next Step 5 entry instead of next Step 5 wrapper entry despite mirror Step 3 structure. Scenario: Step 3 says wrapper entry; omitting wrapper can imply a fresh /implement Step 5 rerun rather than same-session step-5-review.sh reattach after exit 143
- **Proposed resolution**: Mirror Step 3 wording: the next Step 5 wrapper entry reattaches to the recorded identity 1. **[architecture]** `docs/workflow-lifecycle.md:78-79` — The proposed bullet title **Step 5 external-stop recovery** sits directly under a `/design` paragraph that already uses **Step 5** for finalize (5b/5c). Without an `/implement` prefix, operators can read the new note as design finalize recovery instead of `/implement` code-review detach/reattach. Revise the title to **`/implement` Step 5 external-stop recovery** and anchor the opening clause to the code-review worker (parallel to Step 3’s “plan-review loop” anchor). 2. **[correctness]** `docs/workflow-lifecycle.md:79` — The plan asks to mirror the Step 3 bullet but prescribes “the next **Step 5 entry**” instead of Step 3’s “the next **Step 3 wrapper entry**.” That weakens the same-session recovery contract the OOS rollup targets (exit 143 plus absent `step-5-terminal` is expected detach, not a failed run). Use “wrapper entry” in the lifecycle text. The two-file scope, `orphan-timeout` placement in Tool Failures only (not lint-fix tokens), and the signal-detach vs orphan-timeout split match current contracts in `skills/implement/scripts/step-5-review.md`, `skills/implement/SKILL.md`, and `python/larch/review/review_and_fix.py`. No further in-scope additions are needed for minimum-change delivery.



### FINDING_3:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: docs/workflow-lifecycle.md:79
- **Concern**: Lifecycle Step 5 bullet does not disambiguate /implement code review from /design finalize Step 5. Scenario: The Standalone Usage list names /design Finalize (Step 5) in the preceding bullet and would add a sibling Step 5 external-stop recovery bullet without naming /implement or code review. Operators can read the new bullet as /design finalize recovery instead of /implement Step 5 detach and reattach.
- **Proposed resolution**: Title the bullet /implement Step 5 external-stop recovery and open with the same harness framing as the Step 3 bullet: immediate-background /implement Step 5 code-review wrapper, detached review-and-fix loop, .step5-wrapper-detached, withheld .completed/step-5-terminal, and reattach normalization. ### 1. correctness — `docs/workflow-lifecycle.md:79` The plan correctly targets the two rolled-up OOS gaps (`workflow-lifecycle.md` operator doc and `orphan-timeout` in the Step 5 stall taxonomy). Edge cases, failure modes, scoped file limits, and markdownlint validation are adequate for this TRIVIAL doc-only change. One completeness gap remains in the lifecycle bullet intent. In Standalone Usage, Step 3 external-stop recovery is unambiguous because only `/design` plan review uses a detached wrapper at Step 3; `/implement` Step 3 is checks, not that pattern. Step 5 is not parallel: the same section already mentions `/design` Finalize (**Step 5**) and would add a sibling **Step 5 external-stop recovery** bullet with no `/implement` or code-review qualifier. Operators can misread the new bullet as design-finalize recovery. **Suggested revision:** Mirror the Step 3 bullet structure, but explicitly bind the bullet to `/implement` Step 5 code review and the detached `review-and-fix step5` loop. Keep `orphan-timeout` classification only in `step5-review-branches.md`, as the plan already requires.



