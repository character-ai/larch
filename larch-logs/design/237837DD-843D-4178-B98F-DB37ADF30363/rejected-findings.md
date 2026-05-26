### [Plan Review] FINDING_10

### FINDING_10:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/dispatch-with-waterfall.sh:275-278
- **Concern**: `STATUS=cap_hit` bypasses pattern gate. Scenario: Under `--require-result-pattern`, only `STATUS=OK` is content-checked; `cap_hit` is terminal (dispatch-with-waterfall.sh:275-278). Aggregator `cap_hit` output without a FINDING heading can become the candidate and fail python validation as `validation-failed`, not `validation-exhausted`.
- **Proposed resolution**: Step 5 continues with unmerged findings (same as today for `validation-failed`) but without the stall path operators may expect after “all tools degraded.” Document in plan Edge cases; optional follow-up: treat aggregator `cap_hit` without pattern match like a pattern failure at the dispatcher.


### [Plan Review] FINDING_32

### FINDING_32:
- **Reviewer(s)**: Codex-dyn-pattern-gate-parity
- **Severity**: latent
- **Focus area**: correctness
- **Location**: plan.txt:16,88; agents/orchestrator-aggregator.md:27-29; skills/review/scripts/aggregate-findings.sh:96-100,182-189,292-295; scripts/dispatch-with-waterfall.sh:278-286
- **Concern**: Pattern gate permits leading whitespace before ### but the aggregator template and existing FINDING counters/parsers do not. Scenario: The dispatcher uses grep -E, so ^[[:space:]]*### FINDING_[0-9] will accept an indented heading; aggregate-findings then treats that same candidate as zero structured output because count_finding_blocks and output_blocks require ^### FINDING_, producing validation-exhausted instead of dispatcher fallback. The [0-9] piece is not single-digit-only for FINDING_10 because it matches the first digit prefix, and BRE vs ERE does not change that part.
- **Proposed resolution**: Align the gate with the actual aggregator contract by using ^### FINDING_[0-9], or deliberately broaden count_finding_blocks and the Python block parser to accept the same leading whitespace; add a parity regression for an indented ### FINDING_1: candidate.


