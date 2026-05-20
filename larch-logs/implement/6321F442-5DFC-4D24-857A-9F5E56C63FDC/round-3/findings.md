### FINDING_1: **Important** `correctness` `skills/review/scripts/review-core.sh:509` — Round 2+ votes are now intentionally 2-judge, but `tally-code-votes.sh` still emits `⚠ Degraded code-review panel` whenever effective voters are below 3 (`skills/review/scripts/tally-code-votes.sh:265-267`). Concrete failing scenario: round 2 launches Claude+Cursor successfully, `voting-tally.md` gets a degraded banner, then `review-and-fix.sh` sees that banner (`skills/review-and-fix/scripts/review-and-fix.sh:1005-1039`), retries the panel, and records `DEGRADED_ROUND=true`, which inflates round caps and excludes the round from convergence. Pass the round or expected voter count into `tally-code-votes.sh` and only emit the degraded banner when effective voters fall below the expected count for that round; add a round-2 regression test.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `correctness` `skills/review/scripts/review-core.sh:509` — Round 2+ votes are now intentionally 2-judge, but `tally-code-votes.sh` still emits `⚠ Degraded code-review panel` whenever effective voters are below 3 (`skills/review/scripts/tally-code-votes.sh:265-267`). Concrete failing scenario: round 2 launches Claude+Cursor successfully, `voting-tally.md` gets a degraded banner, then `review-and-fix.sh` sees that banner (`skills/review-and-fix/scripts/review-and-fix.sh:1005-1039`), retries the panel, and records `DEGRADED_ROUND=true`, which inflates round caps and excludes the round from convergence. Pass the round or expected voter count into `tally-code-votes.sh` and only emit the degraded banner when effective voters fall below the expected count for that round; add a round-2 regression test.
- **Suggested revision**: Address the concern above.

### FINDING_2: **Nit** `risk-integration` `README.md:84` — Several public/reference docs still say code review uses Codex every round or still describe the old full panel shape (`README.md:84`, `docs/collaborative-sketches.md:55`, `docs/workflow-lifecycle.md:154`, `docs/skills.md:95`, `skills/shared/topology.tsv:13`). This will mislead consumers even though the runtime now omits Codex after round 1. Update the remaining docs/topology source and regenerate generated projections as needed.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Nit** `risk-integration` `README.md:84` — Several public/reference docs still say code review uses Codex every round or still describe the old full panel shape (`README.md:84`, `docs/collaborative-sketches.md:55`, `docs/workflow-lifecycle.md:154`, `docs/skills.md:95`, `skills/shared/topology.tsv:13`). This will mislead consumers even though the runtime now omits Codex after round 1. Update the remaining docs/topology source and regenerate generated projections as needed. No out-of-scope observations.   Checks run: `bash -n` on the changed shell scripts and updated test harnesses.
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] code-quality: docs/review-agents.md:100
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Unchanged fallback prose still describes skipping “6 Codex specialist slots” for all /review shapes. Was already imprecise for SIMPLE; not introduced by this branch. Optional follow-up doc pass outside this PR scope.
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] code-quality: scripts/test-review-structure.sh:110
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Structural test prose still says “3-judge code-review panel.” Unchanged by this branch. Update separately if you want wording aligned with round-aware voting.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] code-quality: skills/review/scripts/tally-code-votes.sh:1-5
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] File header still describes code review as 3-voter-only; comment drift predates full diff hunk. Misleading onboarding for contributors reading only the script header. Refresh header comment when editing tally for round-aware banners.
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] code-quality: skills/review/scripts/tally-code-votes.sh:4
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] File banner still frames code review as strictly 3-voter threshold rules. Operators reading only tally-code-votes.sh may miss that lib-vote-tally already defines unanimous-2 behavior for EFFECTIVE_VOTERS=2; not introduced by this branch. Optionally align the tally script header with lib-vote-tally.md / voting-protocol wording.
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] risk-integration: skills/shared/topology.tsv:9
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] topology row still unconditional 3-reviewer panel Diverges from updated review-agents table for implement conflict review Update topology in a change that owns cross-doc projection
- **Suggested revision**: Address the concern above.

### FINDING_8: code-quality: docs/voting-process.md:26
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] JUDGE_ERROR note still hard-codes 3-judge panel Round 2+ /review is intentionally 2-judge; readers may think parse rules always assume a 3-judge shape Generalize to 2- and 3-judge /review or scope the sentence to contexts where three judges are always intended
- **Suggested revision**: Address the concern above.

### FINDING_9: code-quality: docs/voting-process.md:72-76
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Voting Flow diagram says 3 reviewers submit findings Misaligned with multi-specialist /review and new round-aware voter docs Rewrite lead line to neutral reviewer wording or split by skill
- **Suggested revision**: Address the concern above.

### FINDING_10: code-quality: scripts/dispatch-code-voters.sh (make_voter_prompt_file / codex_prompt)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Codex voter prompt file still generated when Codex voter is skipped Extra tmpdir artifact and minor confusion when debugging Generate Codex prompt only on round 1
- **Suggested revision**: Address the concern above.

### FINDING_11: code-quality: scripts/test-dispatch-code-voters.sh:7-17
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Harness header still documents 11 scenarios and happy=scenarios 1-3. The happy section now includes a fourth round-2 scenario; comments mislead triage of CI shards and local --section usage. Refresh scenario counts and the happy section description to include the round-2 case.
- **Suggested revision**: Address the concern above.

### FINDING_12: code-quality: skills/review/SKILL.md:37
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Step 2 dispatch-panel example omits --round-num Maintainers may miss round-aware dispatch wiring Add --round-num to example or note review-core forwards it
- **Suggested revision**: Address the concern above.

### FINDING_13: code-quality: skills/review/scripts/review-core.sh:503-507
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Voter file inclusion relies on empty path for skipped voter-2 instead of explicit skipped guard. If a future bug ever left a stale non-empty path while status=skipped, tally could ingest an unintended file. Add explicit != skipped (and keep -s) when appending voter_files.
- **Suggested revision**: Address the concern above.

### FINDING_14: correctness: docs/voting-process.md:26
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] JUDGE_ERROR sentence still hardcodes a 3-judge panel after the doc now describes 2-voter rounds 2+ for /review. Readers can mis-parse how parse failures interact with tiering on rounds after the first. Reword to reference eligible voters or round-specific panel size instead of “3-judge.”
- **Suggested revision**: Address the concern above.

### FINDING_15: correctness: skills/review/scripts/tally-code-votes.sh:265-268
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Unconditional EFFECTIVE_VOTERS<3 emits Degraded banner; intentional 2-judge rounds (round 2+ after Codex omission) always look degraded. Round 2+ with healthy Claude+Cursor votes: voting-tally.md opens with false degraded warning despite nominal unanimous-2 panel. Thread nominal expected voter count (from ROUND_NUM) into tally and only warn when effective < nominal or stripped below nominal.
- **Suggested revision**: Address the concern above.

### FINDING_16: correctness: skills/review/scripts/tally-code-votes.sh:265-268 (plan gap)
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Plan covers dispatch expected_judges and classify_result but not tally banner semantics. Operators see conflicting signals: dispatch-code-voters stops false 2/3 warnings but tally still shouts Degraded for healthy 2 judges. Update plan + tally UX to match the new round-aware contract.
- **Suggested revision**: Address the concern above.

### FINDING_17: risk-integration: docs vs feature_description
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Feature text scopes to /implement and /fix-issue; code+docs also change multi-round /review Codex participation. Standalone /review round 2+ no longer uses Codex; someone trusting only the narrow feature blurb may be surprised. Align release notes / feature blurb with shipped cross-skill behavior (or gate Codex omission on nested-only if that was the true intent).
- **Suggested revision**: Address the concern above.

### FINDING_18: risk-integration: skills/review/SKILL.md:37
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Step 2 narrative does not mention Codex reviewer slots are round-1-only while Step 3 documents round-aware voting. Orchestrator-facing instructions under-describe round 2+ specialist topology versus scripts. Add a short round-1-only Codex clause and note review-core passes --round-num into dispatch-panel.
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: skills/review/scripts/test-check-reviewer-failure-threshold.sh:116-139
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] New round-2+ threshold tests only exercise --panel hard. check-reviewer-failure-threshold.sh applies STATIC_INTENDED_SLOTS=6 to simple and hard for ROUND_NUM>1; a simple-only regression could ship while CI stays green. Add at least one simple --round-num 2 threshold case (INTENDED_SLOTS/FAILED_SLOTS/THRESHOLD_OK) parallel to the hard cases.
- **Suggested revision**: Address the concern above.

### FINDING_20: risk-integration: skills/review/scripts/test-dispatch-panel.sh:1186-1210
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Round-2 panel tests omit dynamic-archetypes/scout combinations. Interaction bugs between ROUND_NUM>1 and appended dynamic Cursor slots would not be exercised by the new assertions. Add a focused harness for round 2 + small dynamic cap if this stack is considered regression-prone.
- **Suggested revision**: Address the concern above.

