### FINDING_1: **Important** `correctness` [skills/review-and-fix/scripts/review-and-fix.sh:1117](<OPERATOR_REPO_PATH>/skills/review-and-fix/scripts/review-and-fix.sh:1117) Previous degraded rounds are still counted toward convergence. Scenario: round 2 is degraded after retry and writes `ACCEPTED_COUNT=2`; round 3 is clean with `ACCEPTED_COUNT=1`; line 1123 compares against round 2 and converges even though the contract says degraded rounds are excluded from the consecutive-round calculation. Persist a per-round degraded marker or metadata key and require both current and previous counted rounds to be non-degraded, or compare against the previous non-degraded round only.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Important** `correctness` [skills/review-and-fix/scripts/review-and-fix.sh:1117](<OPERATOR_REPO_PATH>/skills/review-and-fix/scripts/review-and-fix.sh:1117) Previous degraded rounds are still counted toward convergence. Scenario: round 2 is degraded after retry and writes `ACCEPTED_COUNT=2`; round 3 is clean with `ACCEPTED_COUNT=1`; line 1123 compares against round 2 and converges even though the contract says degraded rounds are excluded from the consecutive-round calculation. Persist a per-round degraded marker or metadata key and require both current and previous counted rounds to be non-degraded, or compare against the previous non-degraded round only.
- **Suggested revision**: Address the concern above.

### FINDING_2: **Important** `correctness` [skills/review-and-fix/scripts/review-and-fix.sh:1125](<OPERATOR_REPO_PATH>/skills/review-and-fix/scripts/review-and-fix.sh:1125) Important findings do not reliably block convergence because the grep only matches bare lines like `**Important**`, while normal findings are headed like `### FINDING_1: **Important** — ...`. Scenario: rounds 2 and 3 both have `ACCEPTED_COUNT <= 3` and `findings.md` contains standard Important headings, but the grep misses them and emits `REVIEW_AND_FIX_STATUS=converged-small-changes`. Match the actual review format, for example `(^|: )[[:space:]]*\*\*Important\*\*`, or parse the structured finding records if available.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `correctness` [skills/review-and-fix/scripts/review-and-fix.sh:1125](<OPERATOR_REPO_PATH>/skills/review-and-fix/scripts/review-and-fix.sh:1125) Important findings do not reliably block convergence because the grep only matches bare lines like `**Important**`, while normal findings are headed like `### FINDING_1: **Important** — ...`. Scenario: rounds 2 and 3 both have `ACCEPTED_COUNT <= 3` and `findings.md` contains standard Important headings, but the grep misses them and emits `REVIEW_AND_FIX_STATUS=converged-small-changes`. Match the actual review format, for example `(^|: )[[:space:]]*\*\*Important\*\*`, or parse the structured finding records if available.
- **Suggested revision**: Address the concern above.

### FINDING_3: **Important** `risk-integration` [skills/implement/SKILL.md:1382](<OPERATOR_REPO_PATH>/skills/implement/SKILL.md:1382) The new `DEGRADED_ROUND=true` output is not consumed by the caller, so degraded rounds still burn the review cap. Scenario: a simple workflow reaches round 5 with `DEGRADED_ROUND=true`; `skills/implement/SKILL.md:1396` still treats `round_num == round_cap` as cap reached, and `scripts/run-step5-review.sh:147-159` passes only the numeric round through. Add parent handling for `DEGRADED_ROUND=true` to retry without incrementing the effective cap/round counter, and add an integration regression covering cap behavior.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 4. **Important** `risk-integration` [skills/implement/SKILL.md:1382](<OPERATOR_REPO_PATH>/skills/implement/SKILL.md:1382) The new `DEGRADED_ROUND=true` output is not consumed by the caller, so degraded rounds still burn the review cap. Scenario: a simple workflow reaches round 5 with `DEGRADED_ROUND=true`; `skills/implement/SKILL.md:1396` still treats `round_num == round_cap` as cap reached, and `scripts/run-step5-review.sh:147-159` passes only the numeric round through. Add parent handling for `DEGRADED_ROUND=true` to retry without incrementing the effective cap/round counter, and add an integration regression covering cap behavior.
- **Suggested revision**: Address the concern above.

### FINDING_4: **Important** `risk-integration` [skills/review-and-fix/scripts/review-and-fix.sh:1129](<OPERATOR_REPO_PATH>/skills/review-and-fix/scripts/review-and-fix.sh:1129) Convergence can overwrite `fix-applied`, which makes `/implement` skip post-fix checks. Scenario: round 3 has one accepted in-scope finding, the coder edits and commits it, then convergence changes the status from `fix-applied` to `converged-small-changes`; `skills/implement/SKILL.md:1381-1382` only runs `run-relevant-checks-captured.sh` for `fix-applied`, so the new commit can proceed without Step 5 checks. Keep `fix-applied` as the status and emit convergence as a separate key, or update the parent to run checks whenever `CODER_STATUS=applied` / `CODER_COMMIT_SHA` is present before stopping the loop.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 3. **Important** `risk-integration` [skills/review-and-fix/scripts/review-and-fix.sh:1129](<OPERATOR_REPO_PATH>/skills/review-and-fix/scripts/review-and-fix.sh:1129) Convergence can overwrite `fix-applied`, which makes `/implement` skip post-fix checks. Scenario: round 3 has one accepted in-scope finding, the coder edits and commits it, then convergence changes the status from `fix-applied` to `converged-small-changes`; `skills/implement/SKILL.md:1381-1382` only runs `run-relevant-checks-captured.sh` for `fix-applied`, so the new commit can proceed without Step 5 checks. Keep `fix-applied` as the status and emit convergence as a separate key, or update the parent to run checks whenever `CODER_STATUS=applied` / `CODER_COMMIT_SHA` is present before stopping the loop.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] risk-integration: skills/implement/SKILL.md:1354-1396
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Step 5 orchestration text does not consume DEGRADED_ROUND or converged-small-changes semantics DEGRADED_ROUND contract claims cap should not decrement; SKILL loop never references it File not modified on this branch; update SKILL separately if cap semantics are load-bearing
- **Suggested revision**: Address the concern above.

### FINDING_6: architecture: skills/review-and-fix/scripts/review-and-fix.sh:18-22
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] usage() omits --convergence-threshold. Operators relying on --help miss the new flag though review-and-fix.md documents it. Add the flag to usage text for implement mode argv.
- **Suggested revision**: Address the concern above.

### FINDING_7: architecture: skills/review-and-fix/scripts/review-and-fix.sh:930-953
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] degraded-retry.flag suppresses retries whenever it pre-exists Crash after touch or reused tmpdir: banner remains but no second panel attempt is made Make retry idempotent: clear flag on success or key retries off banner + attempt metadata
- **Suggested revision**: Address the concern above.

### FINDING_8: architecture: skills/review-and-fix/scripts/test-review-and-fix.sh:404+
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Tests use bespoke stub scripts instead of the plan's TEST_CORE_STATUS degraded-panel stubs. Low risk; plan-to-test naming traceability is weaker. Optional: refactor toward centralized TEST_CORE_STATUS stubs if the suite standardizes on that pattern.
- **Suggested revision**: Address the concern above.

### FINDING_9: code-quality: skills/review-and-fix/scripts/review-and-fix.sh:18-22
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] usage() omits --convergence-threshold Operators using --help do not see new flag Update usage text for new orchestrator flags
- **Suggested revision**: Address the concern above.

### FINDING_10: code-quality: skills/review-and-fix/scripts/test-review-and-fix.sh:1004-1297
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] No regression covers a non-default --convergence-threshold. Threshold flag could regress without test signal. Add one test with --convergence-threshold 1 and adjusted stub counts.
- **Suggested revision**: Address the concern above.

### FINDING_11: correctness: skills/review-and-fix/scripts/review-and-fix.sh:1112-1129
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Convergence ignores whether the prior compared round was degraded Degraded round N-1 yields unreliable small ACCEPTED_COUNT; clean round N pairs into a false two-round low streak Track or read prior-round degraded state and exclude it from streak math
- **Suggested revision**: Address the concern above.

### FINDING_12: correctness: skills/review-and-fix/scripts/review-and-fix.sh:1112-1131
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Convergence uses prior round ACCEPTED_COUNT but does not exclude a prior degraded round (no persisted DEGRADED_ROUND on prior rounds). Degraded round 2 with low accepts plus healthy round 3 with low accepts can incorrectly converge. Persist per-round degraded flag and require both compared rounds to be non-degraded (or skip degraded rounds in the streak).
- **Suggested revision**: Address the concern above.

### FINDING_13: correctness: skills/review-and-fix/scripts/review-and-fix.sh:1112-1131
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Part A convergence can overwrite fix-applied, main-agent-vote-required, no-changes, etc. Low accept counts after fix-applied can rewrite status to converged-small-changes; Implement Step 5 then skips the fix-applied run-relevant-checks path. Vote-required can be overwritten before adjudication. Only run Part A for intended terminal statuses (e.g. complete); never after fix-applied or main-agent-vote-required.
- **Suggested revision**: Address the concern above.

### FINDING_14: correctness: skills/review-and-fix/scripts/review-and-fix.sh:1112-1131
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Convergence pairs current round only against round N-1 ACCEPTED_COUNT and skips only when the current round is degraded; it does not verify round N-1 was non-degraded despite review-and-fix.md requiring two consecutive non-degraded low-accept rounds. Round 2 is degraded but writes small ACCEPTED_COUNT to round-2/review-core.env; round 3 is clean and small; script can emit converged-small-changes using (3,2), violating the documented non-degraded pairing rule. Persist per-round degraded flag (e.g. in review-core.env or summary JSON) and require both rounds in the pair to be non-degraded before setting converged-small-changes.
- **Suggested revision**: Address the concern above.

### FINDING_15: correctness: skills/review-and-fix/scripts/review-and-fix.sh:1112-1131
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Convergence ignores whether the prior round was degraded while docs require two consecutive non-degraded low-accept rounds. A degraded round N-1 can still contribute a low ACCEPTED_COUNT; round N can be clean and small, yet the script sets converged-small-changes as if both rounds were valid low-accept signal. Read prior round degradation (e.g. prior voting-tally banner or stored DEGRADED_ROUND) and skip or reset the consecutive-low-accept chain unless both rounds are non-degraded.
- **Suggested revision**: Address the concern above.

### FINDING_16: correctness: skills/review-and-fix/scripts/review-and-fix.sh:1114
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] --convergence-threshold is not validated as numeric. Non-numeric values make bash arithmetic comparisons unreliable. Validate digits-only or exit 2 with a clear error.
- **Suggested revision**: Address the concern above.

### FINDING_17: correctness: skills/review-and-fix/scripts/review-and-fix.sh:1114-1123
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] CONVERGENCE_THRESHOLD not validated before arithmetic Non-numeric threshold can abort script under set -e or yield confusing comparisons Validate non-negative integer like other numeric flags
- **Suggested revision**: Address the concern above.

### FINDING_18: correctness: skills/review-and-fix/scripts/review-and-fix.sh:1124-1127
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Important-findings guard uses a narrow line-anchored grep pattern. Important severity encoded outside ^**Important** or **Important ` may not block convergence, allowing converged-small-changes when Important-class content exists. Match real findings.md severity patterns or share parsing with review-core output.
- **Suggested revision**: Address the concern above.

### FINDING_19: correctness: skills/review-and-fix/scripts/review-and-fix.sh:1124-1127
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Important guard treats grep file errors like no match via if ! grep. Missing unreadable findings.md yields BSD grep exit 2; condition succeeds and convergence can run without scanning Important markers. Require grep exit 1 only for the no-match path or preflight that both files exist and are readable before treating as no Important.
- **Suggested revision**: Address the concern above.

### FINDING_20: correctness: skills/review-and-fix/scripts/review-and-fix.sh:1125-1127
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Important-finding guard uses line-anchored grep that misses canonical ### FINDING_N: **Important** headings Two low-accept rounds still contain Important findings in normal findings.md format; convergence still returns converged-small-changes Match canonical finding headers (e.g. ### FINDING_[0-9]+: **Important**) or equivalent structured marker
- **Suggested revision**: Address the concern above.

### FINDING_21: correctness: skills/review-and-fix/scripts/review-and-fix.sh:1125-1129
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Important-finding guard regex does not match canonical findings.md headers (e.g. ### FINDING_1: **Important** …). Two rounds with only **Important** findings in standard header form can still get REVIEW_AND_FIX_STATUS=converged-small-changes because grep finds no match. Match real severity markup (e.g. \\*\\*Important\\*\\* or FINDING headers); add tests using real header shape.
- **Suggested revision**: Address the concern above.

### FINDING_22: risk-integration: skills/implement/SKILL.md:1366-1398; scripts/run-step5-review.sh
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] New statuses/keys are not wired into /implement Step 5 loop or launcher. Orchestrator may not stop the loop on converged-small-changes or skip cap accounting for DEGRADED_ROUND as documented. Update Step 5 scripted review loop and launcher/docs to parse and act on these outputs.
- **Suggested revision**: Address the concern above.

### FINDING_23: risk-integration: skills/review-and-fix/scripts/review-and-fix.md:102-105; skills/implement/SKILL.md:1366-1397; scripts/run-step5-review.sh
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Feature and new doc require degraded rounds not to count toward the implement review round cap, but no consumer reads DEGRADED_ROUND or adjusts round_num toward ROUND_CAP. Degraded panels still advance round_num under Step 5 re-review / bulk-skip gates until round_cap, so cap exhaustion can happen without a valid panel tally—contrary to don't burn round cap. Update Step 5 loop (SKILL and/or run-step5-review.sh) to treat DEGRADED_ROUND=true as not consuming cap (document exact semantics if partial burns are intended).
- **Suggested revision**: Address the concern above.

### FINDING_24: risk-integration: skills/review-and-fix/scripts/review-and-fix.sh:1092-1129
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Convergence can overwrite fix-applied status after coder commit Low accept counts plus fix-applied commit emit REVIEW_AND_FIX_STATUS=converged-small-changes; Step 5 may skip fix-applied checks path despite repo-changing commit Do not let convergence supersede fix-applied or define explicit combined status + orchestrator handling
- **Suggested revision**: Address the concern above.

### FINDING_25: risk-integration: skills/review-and-fix/scripts/review-and-fix.sh:1189-1190 skills/review-and-fix/scripts/review-and-fix.md:95-105
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] DEGRADED_ROUND is documented for cap and convergence accounting but no orchestrator consumes it in this branch. Degraded rounds still consume the review round cap; behavior diverges from the published contract. Update Step 5 loop or equivalent to read DEGRADED_ROUND and adjust cap or round accounting accordingly.
- **Suggested revision**: Address the concern above.

### FINDING_26: risk-integration: skills/review-and-fix/scripts/test-review-and-fix.sh:492-496
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Important-blocking test uses non-canonical findings.md line format Tests pass even if real Important headings are undetected Add fixture using ### FINDING_1: **Important** … heading
- **Suggested revision**: Address the concern above.

