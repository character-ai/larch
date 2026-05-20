### FINDING_15: correctness: skills/review/scripts/tally-code-votes.sh:265-268
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Unconditional EFFECTIVE_VOTERS<3 emits Degraded banner; intentional 2-judge rounds (round 2+ after Codex omission) always look degraded. Round 2+ with healthy Claude+Cursor votes: voting-tally.md opens with false degraded warning despite nominal unanimous-2 panel. Thread nominal expected voter count (from ROUND_NUM) into tally and only warn when effective < nominal or stripped below nominal.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_16: correctness: skills/review/scripts/tally-code-votes.sh:265-268 (plan gap)
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Plan covers dispatch expected_judges and classify_result but not tally banner semantics. Operators see conflicting signals: dispatch-code-voters stops false 2/3 warnings but tally still shouts Degraded for healthy 2 judges. Update plan + tally UX to match the new round-aware contract.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_2: **Nit** `risk-integration` `README.md:84` — Several public/reference docs still say code review uses Codex every round or still describe the old full panel shape (`README.md:84`, `docs/collaborative-sketches.md:55`, `docs/workflow-lifecycle.md:154`, `docs/skills.md:95`, `skills/shared/topology.tsv:13`). This will mislead consumers even though the runtime now omits Codex after round 1. Update the remaining docs/topology source and regenerate generated projections as needed.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Nit** `risk-integration` `README.md:84` — Several public/reference docs still say code review uses Codex every round or still describe the old full panel shape (`README.md:84`, `docs/collaborative-sketches.md:55`, `docs/workflow-lifecycle.md:154`, `docs/skills.md:95`, `skills/shared/topology.tsv:13`). This will mislead consumers even though the runtime now omits Codex after round 1. Update the remaining docs/topology source and regenerate generated projections as needed. No out-of-scope observations.   Checks run: `bash -n` on the changed shell scripts and updated test harnesses.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_3: [OUT_OF_SCOPE] code-quality: docs/review-agents.md:100
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Unchanged fallback prose still describes skipping “6 Codex specialist slots” for all /review shapes. Was already imprecise for SIMPLE; not introduced by this branch. Optional follow-up doc pass outside this PR scope.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_4: [OUT_OF_SCOPE] code-quality: scripts/test-review-structure.sh:110
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Structural test prose still says “3-judge code-review panel.” Unchanged by this branch. Update separately if you want wording aligned with round-aware voting.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_5: [OUT_OF_SCOPE] code-quality: skills/review/scripts/tally-code-votes.sh:1-5
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] File header still describes code review as 3-voter-only; comment drift predates full diff hunk. Misleading onboarding for contributors reading only the script header. Refresh header comment when editing tally for round-aware banners.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_6: [OUT_OF_SCOPE] code-quality: skills/review/scripts/tally-code-votes.sh:4
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] File banner still frames code review as strictly 3-voter threshold rules. Operators reading only tally-code-votes.sh may miss that lib-vote-tally already defines unanimous-2 behavior for EFFECTIVE_VOTERS=2; not introduced by this branch. Optionally align the tally script header with lib-vote-tally.md / voting-protocol wording.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_7: [OUT_OF_SCOPE] risk-integration: skills/shared/topology.tsv:9
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] topology row still unconditional 3-reviewer panel Diverges from updated review-agents table for implement conflict review Update topology in a change that owns cross-doc projection
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

