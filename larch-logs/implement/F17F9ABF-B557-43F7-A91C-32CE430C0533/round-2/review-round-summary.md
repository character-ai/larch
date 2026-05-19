# Review Round 2

- Mode: `diff`
- Accepted findings: 9
- Rejected findings: 7
- Exonerated findings: 4
- Neutral findings: 0

## Accepted Findings

### FINDING_1: **Important** `correctness` [skills/review-and-fix/scripts/review-and-fix.sh:89](<OPERATOR_REPO_PATH>/skills/review-and-fix/scripts/review-and-fix.sh:89) Important detection misses structured reviewer findings. `collect-findings.sh` formats inline TSV severities as `- **Concern**: [important] ...`, but the new regex only recognizes `**Important**` in headings or standalone lines. Concrete scenario: round 2 has `ACCEPTED_COUNT=1` from a structured `important` finding, round 3 has `ACCEPTED_COUNT=0`; convergence incorrectly emits `converged-small-changes` despite an Important finding in the previous round. Extend the scan to cover the collected structured form, for example `\[important\]`, ideally anchored to `- **Concern**:` or by parsing the collected finding shape.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `correctness` [skills/review-and-fix/scripts/review-and-fix.sh:89](<OPERATOR_REPO_PATH>/skills/review-and-fix/scripts/review-and-fix.sh:89) Important detection misses structured reviewer findings. `collect-findings.sh` formats inline TSV severities as `- **Concern**: [important] ...`, but the new regex only recognizes `**Important**` in headings or standalone lines. Concrete scenario: round 2 has `ACCEPTED_COUNT=1` from a structured `important` finding, round 3 has `ACCEPTED_COUNT=0`; convergence incorrectly emits `converged-small-changes` despite an Important finding in the previous round. Extend the scan to cover the collected structured form, for example `\[important\]`, ideally anchored to `- **Concern**:` or by parsing the collected finding shape.
- **Suggested revision**: Address the concern above.


### FINDING_11: correctness: skills/review-and-fix/scripts/review-and-fix.sh:87-105
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Important detection is regex-limited vs canonical severity formats. Important severity only appears in findings prose in a form that does not match (^### FINDING_[0-9]+:[[:space:]]*\\*\\*Important\\*\\*|^\\*\\*Important\\*\\*); grep returns no match; two low-accept rounds still converge to converged-small-changes. Reuse tally/findings canonical severity parsing or broaden patterns in lockstep with how findings are emitted.
- **Suggested revision**: Address the concern above.


### FINDING_12: correctness: skills/review-and-fix/scripts/review-and-fix.sh:956-998
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Degraded retry runs second review-core before OOS merge; first attempt OOS can be dropped if round artifacts are overwritten. Accepted OOS from first degraded attempt never reaches accumulated-oos.md when retry replaces round_dir. Merge or append round_oos after first core run before retry, or merge OOS from both attempts.
- **Suggested revision**: Address the concern above.


### FINDING_13: correctness: skills/review-and-fix/scripts/review-and-fix.sh:964-987
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Existing degraded-retry.flag skips retry even if tally still degraded. Partial run can strand the flag and forfeit the single retry on a later invocation. Couple retry eligibility to banner state or clear stale flags when tally is clean.
- **Suggested revision**: Address the concern above.


### FINDING_14: risk-integration: skills/implement/SKILL.md:1360-1398 vs scripts/run-step5-review.sh:130-134
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Local Step 5 round_cap stays 5/7 while run-step5-review inflates --round-cap for prior degraded rounds; gate comparisons use base cap. Orchestrator stops Step 5 or hits cap logic while launcher still passes a higher --round-cap. Recompute effective_round_cap to match count_prior_degraded_rounds (or surface argv cap to the parent) and use it in all round_num vs cap checks.
- **Suggested revision**: Address the concern above.


### FINDING_15: risk-integration: skills/implement/SKILL.md:1378-1383
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Step 5 exit-0 parsing never names converged-small-changes while review-and-fix.md requires stopping the loop Orchestrator may treat the new terminal status as unknown and schedule another review round despite script contract Add converged-small-changes to the explicit exit-0 status list with stop-loop semantics aligned to review-and-fix.md
- **Suggested revision**: Address the concern above.


### FINDING_2: **Important** `risk-integration` [skills/implement/SKILL.md:1396](<OPERATOR_REPO_PATH>/skills/implement/SKILL.md:1396) A degraded round can still consume the final review slot. The launcher only adds prior degraded rounds to `--round-cap`, and the Step 5 gate still compares the current `round_num` against `round_cap`; if round 5 of a SIMPLE run is degraded and substantial, `DEGRADED_ROUND=true` is written too late for that same cap decision, so the parent takes the cap branch instead of running round 6. Make the prompt-side gate include the current degraded round in the effective cap, or explicitly bypass cap termination when the latest output has `DEGRADED_ROUND=true`.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Important** `risk-integration` [skills/implement/SKILL.md:1396](<OPERATOR_REPO_PATH>/skills/implement/SKILL.md:1396) A degraded round can still consume the final review slot. The launcher only adds prior degraded rounds to `--round-cap`, and the Step 5 gate still compares the current `round_num` against `round_cap`; if round 5 of a SIMPLE run is degraded and substantial, `DEGRADED_ROUND=true` is written too late for that same cap decision, so the parent takes the cap branch instead of running round 6. Make the prompt-side gate include the current degraded round in the effective cap, or explicitly bypass cap termination when the latest output has `DEGRADED_ROUND=true`.
- **Suggested revision**: Address the concern above.


### FINDING_21: security: skills/review-and-fix/scripts/review-and-fix.sh:1210-1214
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Unquoted heredoc when writing round review-and-fix.env expands REVIEW_CORE_STATUS and REVIEW_AND_FIX_STATUS as shell words; core_status comes from review-core KV and can be assigned into status for unknown statuses Values containing command substitution (e.g. $(...)) from a malicious or compromised review-core / tampered core_out could run shell code during heredoc expansion Use a quoted heredoc (no expansion) or printf-safe line writes per key so KV values cannot be interpreted as shell code
- **Suggested revision**: Address the concern above.


### FINDING_4: architecture: skills/review-and-fix/scripts/review-and-fix.sh:963-986
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Presence of degraded-retry.flag skips retry entirely. Crash leaves flag; resumed run never retries degraded panel. Make retry idempotent with completion marker or clear stale flags with documented recovery.
- **Suggested revision**: Address the concern above.


