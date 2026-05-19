# Review Round 1

- Mode: `diff`
- Accepted findings: 10
- Rejected findings: 1
- Exonerated findings: 1
- Neutral findings: 11

## Accepted Findings

### FINDING_1: **Important** `correctness` [skills/review-and-fix/scripts/review-and-fix.sh:1117](<OPERATOR_REPO_PATH>/skills/review-and-fix/scripts/review-and-fix.sh:1117) Previous degraded rounds are still counted toward convergence. Scenario: round 2 is degraded after retry and writes `ACCEPTED_COUNT=2`; round 3 is clean with `ACCEPTED_COUNT=1`; line 1123 compares against round 2 and converges even though the contract says degraded rounds are excluded from the consecutive-round calculation. Persist a per-round degraded marker or metadata key and require both current and previous counted rounds to be non-degraded, or compare against the previous non-degraded round only.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Important** `correctness` [skills/review-and-fix/scripts/review-and-fix.sh:1117](<OPERATOR_REPO_PATH>/skills/review-and-fix/scripts/review-and-fix.sh:1117) Previous degraded rounds are still counted toward convergence. Scenario: round 2 is degraded after retry and writes `ACCEPTED_COUNT=2`; round 3 is clean with `ACCEPTED_COUNT=1`; line 1123 compares against round 2 and converges even though the contract says degraded rounds are excluded from the consecutive-round calculation. Persist a per-round degraded marker or metadata key and require both current and previous counted rounds to be non-degraded, or compare against the previous non-degraded round only.
- **Suggested revision**: Address the concern above.


### FINDING_10: code-quality: skills/review-and-fix/scripts/test-review-and-fix.sh:1004-1297
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] No regression covers a non-default --convergence-threshold. Threshold flag could regress without test signal. Add one test with --convergence-threshold 1 and adjusted stub counts.
- **Suggested revision**: Address the concern above.


### FINDING_13: correctness: skills/review-and-fix/scripts/review-and-fix.sh:1112-1131
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Part A convergence can overwrite fix-applied, main-agent-vote-required, no-changes, etc. Low accept counts after fix-applied can rewrite status to converged-small-changes; Implement Step 5 then skips the fix-applied run-relevant-checks path. Vote-required can be overwritten before adjudication. Only run Part A for intended terminal statuses (e.g. complete); never after fix-applied or main-agent-vote-required.
- **Suggested revision**: Address the concern above.


### FINDING_16: correctness: skills/review-and-fix/scripts/review-and-fix.sh:1114
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] --convergence-threshold is not validated as numeric. Non-numeric values make bash arithmetic comparisons unreliable. Validate digits-only or exit 2 with a clear error.
- **Suggested revision**: Address the concern above.


### FINDING_19: correctness: skills/review-and-fix/scripts/review-and-fix.sh:1124-1127
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Important guard treats grep file errors like no match via if ! grep. Missing unreadable findings.md yields BSD grep exit 2; condition succeeds and convergence can run without scanning Important markers. Require grep exit 1 only for the no-match path or preflight that both files exist and are readable before treating as no Important.
- **Suggested revision**: Address the concern above.


### FINDING_2: **Important** `correctness` [skills/review-and-fix/scripts/review-and-fix.sh:1125](<OPERATOR_REPO_PATH>/skills/review-and-fix/scripts/review-and-fix.sh:1125) Important findings do not reliably block convergence because the grep only matches bare lines like `**Important**`, while normal findings are headed like `### FINDING_1: **Important** — ...`. Scenario: rounds 2 and 3 both have `ACCEPTED_COUNT <= 3` and `findings.md` contains standard Important headings, but the grep misses them and emits `REVIEW_AND_FIX_STATUS=converged-small-changes`. Match the actual review format, for example `(^|: )[[:space:]]*\*\*Important\*\*`, or parse the structured finding records if available.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `correctness` [skills/review-and-fix/scripts/review-and-fix.sh:1125](<OPERATOR_REPO_PATH>/skills/review-and-fix/scripts/review-and-fix.sh:1125) Important findings do not reliably block convergence because the grep only matches bare lines like `**Important**`, while normal findings are headed like `### FINDING_1: **Important** — ...`. Scenario: rounds 2 and 3 both have `ACCEPTED_COUNT <= 3` and `findings.md` contains standard Important headings, but the grep misses them and emits `REVIEW_AND_FIX_STATUS=converged-small-changes`. Match the actual review format, for example `(^|: )[[:space:]]*\*\*Important\*\*`, or parse the structured finding records if available.
- **Suggested revision**: Address the concern above.


### FINDING_23: risk-integration: skills/review-and-fix/scripts/review-and-fix.md:102-105; skills/implement/SKILL.md:1366-1397; scripts/run-step5-review.sh
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Feature and new doc require degraded rounds not to count toward the implement review round cap, but no consumer reads DEGRADED_ROUND or adjusts round_num toward ROUND_CAP. Degraded panels still advance round_num under Step 5 re-review / bulk-skip gates until round_cap, so cap exhaustion can happen without a valid panel tally—contrary to don't burn round cap. Update Step 5 loop (SKILL and/or run-step5-review.sh) to treat DEGRADED_ROUND=true as not consuming cap (document exact semantics if partial burns are intended).
- **Suggested revision**: Address the concern above.


### FINDING_26: risk-integration: skills/review-and-fix/scripts/test-review-and-fix.sh:492-496
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Important-blocking test uses non-canonical findings.md line format Tests pass even if real Important headings are undetected Add fixture using ### FINDING_1: **Important** … heading
- **Suggested revision**: Address the concern above.


### FINDING_4: **Important** `risk-integration` [skills/review-and-fix/scripts/review-and-fix.sh:1129](<OPERATOR_REPO_PATH>/skills/review-and-fix/scripts/review-and-fix.sh:1129) Convergence can overwrite `fix-applied`, which makes `/implement` skip post-fix checks. Scenario: round 3 has one accepted in-scope finding, the coder edits and commits it, then convergence changes the status from `fix-applied` to `converged-small-changes`; `skills/implement/SKILL.md:1381-1382` only runs `run-relevant-checks-captured.sh` for `fix-applied`, so the new commit can proceed without Step 5 checks. Keep `fix-applied` as the status and emit convergence as a separate key, or update the parent to run checks whenever `CODER_STATUS=applied` / `CODER_COMMIT_SHA` is present before stopping the loop.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 3. **Important** `risk-integration` [skills/review-and-fix/scripts/review-and-fix.sh:1129](<OPERATOR_REPO_PATH>/skills/review-and-fix/scripts/review-and-fix.sh:1129) Convergence can overwrite `fix-applied`, which makes `/implement` skip post-fix checks. Scenario: round 3 has one accepted in-scope finding, the coder edits and commits it, then convergence changes the status from `fix-applied` to `converged-small-changes`; `skills/implement/SKILL.md:1381-1382` only runs `run-relevant-checks-captured.sh` for `fix-applied`, so the new commit can proceed without Step 5 checks. Keep `fix-applied` as the status and emit convergence as a separate key, or update the parent to run checks whenever `CODER_STATUS=applied` / `CODER_COMMIT_SHA` is present before stopping the loop.
- **Suggested revision**: Address the concern above.


### FINDING_6: architecture: skills/review-and-fix/scripts/review-and-fix.sh:18-22
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] usage() omits --convergence-threshold. Operators relying on --help miss the new flag though review-and-fix.md documents it. Add the flag to usage text for implement mode argv.
- **Suggested revision**: Address the concern above.


