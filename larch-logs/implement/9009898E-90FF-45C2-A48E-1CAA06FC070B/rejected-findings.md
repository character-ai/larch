### [rejected] FINDING_1

**Rejected subtype:** dismissed (0 YES)

### FINDING_1: correctness: .claude/skills/rebalance-test-harnesses/scripts/rebalance.py:266-299
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Feasibility preflight only checks whether the heaviest single packed target exceeds ideal_shard + threshold/2; that is necessary but not sufficient for the spread threshold. With n_shards=2, threshold=15, and measured targets {a:100, b:50, c:50}, no warning is printed (100 <= 107.5) but LPT packing yields spread 100s and verification CI still fails. After pack(), also warn when estimated spread on new_shards from baseline medians exceeds balance_threshold; keep warning-only behavior.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** dismissed (0 YES)

### FINDING_2: correctness: .claude/skills/rebalance-test-harnesses/scripts/rebalance.py:454
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] PR body label "Before spread (estimated)" is ambiguous even though the value now uses new_shards. Operators may read it as old-layout spread and misjudge the PR. Rename to "Proposed layout spread (estimated)" or explicitly label it as the new assignment estimate.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** dismissed (0 YES)

### FINDING_3: correctness: .claude/skills/rebalance-test-harnesses/SKILL.md:14
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] SKILL references scripts/rebalance.md but the sibling doc is under .claude/skills/rebalance-test-harnesses/scripts/. Maintainers may edit or look for the wrong file. Update the path to the actual sibling doc location.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** dismissed (0 YES)

### FINDING_5: correctness: .claude/skills/rebalance-test-harnesses/scripts/rebalance.py:278-283
- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: [latent] Feasibility preflight uses ideal plus threshold/2, which can produce false infeasible warnings. With n_shards=3, balance_threshold=10, and measured targets slow=40, a=30, b=30, pack can produce 40,30,30 and pass with spread 10, but the preflight warns because 40 > 33.3 + 5. Use the heaviest-target lower bound, such as max_target_time > ideal_shard + ((n_shards - 1) / n_shards) * balance_threshold, or compute the equivalent minimum possible spread.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

