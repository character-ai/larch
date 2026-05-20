### FINDING_1: **Important** `correctness` [skills/review-and-fix/scripts/review-and-fix.sh:89](<OPERATOR_REPO_PATH>/skills/review-and-fix/scripts/review-and-fix.sh:89) Important detection misses structured reviewer findings. `collect-findings.sh` formats inline TSV severities as `- **Concern**: [important] ...`, but the new regex only recognizes `**Important**` in headings or standalone lines. Concrete scenario: round 2 has `ACCEPTED_COUNT=1` from a structured `important` finding, round 3 has `ACCEPTED_COUNT=0`; convergence incorrectly emits `converged-small-changes` despite an Important finding in the previous round. Extend the scan to cover the collected structured form, for example `\[important\]`, ideally anchored to `- **Concern**:` or by parsing the collected finding shape.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `correctness` [skills/review-and-fix/scripts/review-and-fix.sh:89](<OPERATOR_REPO_PATH>/skills/review-and-fix/scripts/review-and-fix.sh:89) Important detection misses structured reviewer findings. `collect-findings.sh` formats inline TSV severities as `- **Concern**: [important] ...`, but the new regex only recognizes `**Important**` in headings or standalone lines. Concrete scenario: round 2 has `ACCEPTED_COUNT=1` from a structured `important` finding, round 3 has `ACCEPTED_COUNT=0`; convergence incorrectly emits `converged-small-changes` despite an Important finding in the previous round. Extend the scan to cover the collected structured form, for example `\[important\]`, ideally anchored to `- **Concern**:` or by parsing the collected finding shape.
- **Suggested revision**: Address the concern above.

### FINDING_2: **Important** `risk-integration` [skills/implement/SKILL.md:1396](<OPERATOR_REPO_PATH>/skills/implement/SKILL.md:1396) A degraded round can still consume the final review slot. The launcher only adds prior degraded rounds to `--round-cap`, and the Step 5 gate still compares the current `round_num` against `round_cap`; if round 5 of a SIMPLE run is degraded and substantial, `DEGRADED_ROUND=true` is written too late for that same cap decision, so the parent takes the cap branch instead of running round 6. Make the prompt-side gate include the current degraded round in the effective cap, or explicitly bypass cap termination when the latest output has `DEGRADED_ROUND=true`.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Important** `risk-integration` [skills/implement/SKILL.md:1396](<OPERATOR_REPO_PATH>/skills/implement/SKILL.md:1396) A degraded round can still consume the final review slot. The launcher only adds prior degraded rounds to `--round-cap`, and the Step 5 gate still compares the current `round_num` against `round_cap`; if round 5 of a SIMPLE run is degraded and substantial, `DEGRADED_ROUND=true` is written too late for that same cap decision, so the parent takes the cap branch instead of running round 6. Make the prompt-side gate include the current degraded round in the effective cap, or explicitly bypass cap termination when the latest output has `DEGRADED_ROUND=true`.
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] code-quality: git log on branch
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Extra commit message style noise from round-1 feedback commit. Reviewer confusion only; not introduced as a logic bug in a single hunk. Keep branch history tidy before merge if policy cares.
- **Suggested revision**: Address the concern above.

### FINDING_4: architecture: skills/review-and-fix/scripts/review-and-fix.sh:963-986
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Presence of degraded-retry.flag skips retry entirely. Crash leaves flag; resumed run never retries degraded panel. Make retry idempotent with completion marker or clear stale flags with documented recovery.
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: skills/review-and-fix/scripts/review-and-fix.sh:1167-1176
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Inverted Important check uses empty then branch and depends on $? in else. A later edit to the then branch can accidentally change $? semantics and break convergence gating. Rewrite as negated test or capture exit code immediately after important_findings_present.
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: skills/review-and-fix/scripts/review-and-fix.sh:941-980
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicate parsing of review-core.env after initial run and after degraded retry. Future edits to core output parsing can diverge between the two copies and regress one path only. Extract a helper and call it from both sites.
- **Suggested revision**: Address the concern above.

### FINDING_7: code-quality: skills/review-and-fix/scripts/test-review-and-fix.sh:807-1262
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Test matrix exceeds the stated eight regression tests. Higher long-term harness cost versus the written plan. Trim or document expanded coverage.
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: skills/review-and-fix/scripts/review-and-fix.sh:108-114
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Degraded exclusion relies on new per-round review-and-fix.env records. Older tmpdirs without those files cannot exclude historical degraded rounds from convergence. Fallback signal source or document non-retroactivity.
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: skills/review-and-fix/scripts/review-and-fix.sh:1181-1190
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Churn warning compares only to immediate predecessor not last non-degraded round. Misleading warning or silence when N-1 was degraded. Align Part C predecessor selection with Part A or document sequential-only semantics.
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: skills/review-and-fix/scripts/review-and-fix.sh:1181-1190
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Churn warning compares only to immediate prior round, unlike convergence’s degraded walk-back. Adjacent degraded round yields misleading churn signal relative to convergence logic. Align comparator rounds or document the asymmetry.
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

### FINDING_16: risk-integration: skills/implement/SKILL.md:1380-1382
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Exit 0 status examples omit converged-small-changes. Human/agent reads SKILL only; may not recognize new status as normal exit-0 terminal handling alongside complete/no-changes. Add converged-small-changes to the Exit 0 example list and any loop-stop guidance.
- **Suggested revision**: Address the concern above.

### FINDING_17: risk-integration: skills/implement/SKILL.md:1382
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] converged-small-changes not listed among example terminal statuses. Orchestrators skimming bullets may not treat the new status as explicitly loop-terminal like complete. Add to the parenthetical and state same handling as complete for loop/tally.
- **Suggested revision**: Address the concern above.

### FINDING_18: risk-integration: skills/implement/SKILL.md:1394-1398 and scripts/run-step5-review.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Launcher raises --round-cap for prior degraded rounds (tested) but re-review gate remains prompt-only math on round_cap Physical rounds can stop early while review-and-fix receives a higher argv cap if the agent never adds prior_degraded_rounds to its local cap comparison Materialize effective cap in testable shell or add harness asserting gate matches argv extension
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: skills/review-and-fix/scripts/review-and-fix.sh:1145-1190
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Churn warning uses strict round N-1 while convergence uses last non-degraded predecessor. After a degraded round N-1, ACCEPTED_COUNT in review-core.env can be unrepresentative; round N triggers a churn warning without reflecting that N-1 was degraded. Skip or retarget Part C when N-1 is degraded, or compare to the same predecessor chosen in Part A.
- **Suggested revision**: Address the concern above.

### FINDING_20: risk-integration: skills/review-and-fix/scripts/review-and-fix.sh:1181-1190
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Churn warning compares to immediate prior round only; convergence skips degraded predecessors Misleading churn stderr after a degraded N-1 panel with odd ACCEPTED_COUNT Document asymmetry or align predecessor selection with Part A
- **Suggested revision**: Address the concern above.

### FINDING_21: security: skills/review-and-fix/scripts/review-and-fix.sh:1210-1214
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Unquoted heredoc when writing round review-and-fix.env expands REVIEW_CORE_STATUS and REVIEW_AND_FIX_STATUS as shell words; core_status comes from review-core KV and can be assigned into status for unknown statuses Values containing command substitution (e.g. $(...)) from a malicious or compromised review-core / tampered core_out could run shell code during heredoc expansion Use a quoted heredoc (no expansion) or printf-safe line writes per key so KV values cannot be interpreted as shell code
- **Suggested revision**: Address the concern above.

