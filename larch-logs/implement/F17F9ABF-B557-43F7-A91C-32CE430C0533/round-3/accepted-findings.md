### FINDING_1: **Important** `correctness` `skills/review-and-fix/scripts/review-and-fix.sh:1159`  
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `correctness` `skills/review-and-fix/scripts/review-and-fix.sh:1159`      The convergence check only runs when `status == "complete"`, but real `review-core.sh` sets `REVIEW_CORE_STATUS=fix-required` whenever `ACCEPTED_COUNT > 0`, so low nonzero accepted counts never reach this branch. Concrete failing scenario: two non-degraded rounds with `ACCEPTED_COUNT=2` then `ACCEPTED_COUNT=1`, no Important findings, and successful coder handling produce `fix-applied`/`no-changes` instead of `converged-small-changes`, so the new threshold does not govern the intended low-accept path. Suggested fix: base convergence on the current/previous accepted counts for all successful terminal statuses that should stop the loop, or emit a separate post-fix convergence signal that the parent honors after checks.
- **Suggested revision**: Address the concern above.


### FINDING_11: correctness: skills/review-and-fix/scripts/review-and-fix.sh:969-1009
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Degraded retry runs append_round_oos_artifact before re-invoking review-core and again unconditionally after the degraded block. If round-N/oos-accepted-review.md is non-empty and identical across both attempts duplicate OOS paragraphs/lines can land in accumulated-oos.md and accumulated-oos.jsonl. Append once per logical attempt or gate the second append on changed OOS content or drop the pre-retry append when content is stable.
- **Suggested revision**: Address the concern above.


### FINDING_12: correctness: skills/review-and-fix/scripts/review-and-fix.sh:982-983,1009
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Double append of round OOS into accumulated OOS on degraded-panel retry path. Non-empty round oos-accepted-review.md plus degraded banner causes append_round_oos_artifact before retry and again after retry, duplicating JSONL/markdown/mirror entries for one round. Append OOS once per final panel outcome or skip second append when pre-retry append already ran for the same round_oos.
- **Suggested revision**: Address the concern above.


### FINDING_13: correctness: skills/review-and-fix/scripts/review-and-fix.sh:982-986
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] append_round_oos_artifact runs before degraded-retry.flag is durable; stale path deletes flag Process crash or stale recovery re-enters retry branch and re-appends the same round_oos into accumulated-oos.md/jsonl, duplicating OOS payloads. Gate append with idempotency (sentinel), move append after atomic retry claim, or dedupe JSONL entries.
- **Suggested revision**: Address the concern above.


### FINDING_15: risk-integration: skills/implement/SKILL.md:1362-1364
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Step 5 banners still print fixed 5/7 round ceilings after introducing effective degraded-aware caps. Human operators can underestimate how many Step 5 iterations remain when degraded rounds inflate the argv cap. Update the print templates to reference effective_round_cap or an equivalent explicit formula.
- **Suggested revision**: Address the concern above.


### FINDING_16: risk-integration: skills/review-and-fix/scripts/review-and-fix.sh:1192-1201
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Part C churn warning compares current ACCEPTED_COUNT only to round N-1, not the last non-degraded round like Part A. When round N-1 is degraded with a low ACCEPTED_COUNT and round N is healthy with a higher count, larch_err can warn about a spike versus a degraded baseline that is not comparable to the convergence logic, producing false churn signals. Align Part C baseline with Part A by walking back to the latest prior non-degraded round (or skip churn when round N-1 is degraded).
- **Suggested revision**: Address the concern above.


### FINDING_2: **Important** `risk-integration` `skills/review-and-fix/scripts/review-and-fix.sh:983`  
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Important** `risk-integration` `skills/review-and-fix/scripts/review-and-fix.sh:983`      On a degraded panel, the script appends accepted OOS artifacts from the first degraded attempt before retrying, so a clean retry cannot retract public-boundary OOS from the discarded attempt. Concrete failing scenario: attempt 1 has a 1-judge degraded tally accepting an OOS item, attempt 2 is clean and rejects or omits it, but `accumulated-oos.md` still contains the attempt-1 item and Step 9a.1 can file it publicly. Suggested fix: do not append round OOS until after the final retry result is known; keep first-attempt artifacts only in a local diagnostic/audit file if needed.
- **Suggested revision**: Address the concern above.


### FINDING_3: code-quality: skills/review-and-fix/scripts/review-and-fix.sh:1192-1201
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Churn warning (Part C) still runs after status may be set to converged-small-changes. Operator sees convergence breadcrumb plus a churn warning in the same successful exit. Gate Part C on status != converged-small-changes (or equivalent).
- **Suggested revision**: Address the concern above.


### FINDING_4: code-quality: skills/review-and-fix/scripts/review-and-fix.sh:1192-1201 vs :1156-1189
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Churn warning uses immediate predecessor accepts while convergence skips degraded rounds. After a degraded round N-1 the warning can fire against counts the convergence heuristic deliberately ignores misleading polish-or-churn signal. Reuse the same non-degraded predecessor index as Part A or suppress Part C when round N-1 is degraded.
- **Suggested revision**: Address the concern above.


### FINDING_7: correctness: skills/review-and-fix/scripts/review-and-fix.sh:1164-1187
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Important-scan omits intermediate degraded rounds when pairing for convergence Early REVIEW_AND_FIX_STATUS=converged-small-changes can trigger while a skipped degraded round still has Important content in findings.md that is never passed to important_findings_present Also scan findings.md for each skipped degraded round between the comparator rounds (or scan all rounds in the window) before allowing converged-small-changes
- **Suggested revision**: Address the concern above.


### FINDING_8: correctness: skills/review-and-fix/scripts/review-and-fix.sh:1192-1201
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Churn warning always compares to immediate prior round Degraded round N-1 with low ACCEPTED_COUNT vs healthy round N triggers misleading polishing warning. Use last non-degraded prior round or skip when prior round was degraded.
- **Suggested revision**: Address the concern above.


### FINDING_9: correctness: skills/review-and-fix/scripts/review-and-fix.sh:1192-1201
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Churn warning always compares to immediate prior round After a degraded round N-1 Part C still uses N-1 review-core.env counts which Part A treats as excluded from convergence logic Mirror Part A by comparing against the last non-degraded predecessor or skip the warning when N-1 was degraded
- **Suggested revision**: Address the concern above.


