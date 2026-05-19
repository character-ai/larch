# Review Round 4

- Mode: `diff`
- Accepted findings: 9
- Rejected findings: 12
- Exonerated findings: 1
- Neutral findings: 0

## Accepted Findings

### FINDING_1: **Important** `correctness` `skills/review-and-fix/scripts/review-and-fix.sh:1005` / `skills/review-and-fix/scripts/review-and-fix.sh:1029`  
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Important** `correctness` `skills/review-and-fix/scripts/review-and-fix.sh:1005` / `skills/review-and-fix/scripts/review-and-fix.sh:1029`      The degraded-panel retry reruns `review-core.sh` into the same `round_dir`, but OOS accumulation only happens once after the retry, so first-attempt OOS artifacts are lost when the retry overwrites `oos-accepted-review.md`. Concrete scenario covered by the new test stub at `skills/review-and-fix/scripts/test-review-and-fix.sh:1345-1375`: the first degraded attempt writes `OOS_1`, the clean retry writes `OOS_2`, and `accumulated-oos.md` will only contain `OOS_2`, failing the asserted preservation of both JSONL records. Append or snapshot the first attempt’s OOS artifact before rerunning the core, or change the test/contract if degraded-attempt OOS is intentionally discarded. I could not run the regression script in this environment because `mktemp` cannot create its temp directory under the read-only sandbox: `Operation not permitted`.
- **Suggested revision**: Address the concern above.


### FINDING_11: correctness: skills/review-and-fix/scripts/review-and-fix.sh:1176-1206
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Part A convergence can overwrite fix-applied with converged-small-changes because fix-applied is listed in convergence_candidate_status. Default review-core stub emits ACCEPTED_COUNT=1; write_prior_round seeds round 1 with 1; both rounds are below default threshold 3 and findings scan finds no Important markers, so status becomes converged-small-changes after coder success—contradicts test-review-and-fix.sh:1377-1390 which requires fix-applied to survive. Remove fix-applied (and likely in-scope-filtered-out) from convergence_candidate_status or gate Part A so it never runs after a successful coder apply path.
- **Suggested revision**: Address the concern above.


### FINDING_14: correctness: skills/review-and-fix/scripts/review-and-fix.sh:986-1029
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] After degraded panel retry, OOS is only appended once from the final round_oos file; first-attempt OOS is overwritten by the second review-core run. accumulated-oos.md / accumulated-oos.jsonl lose OOS emitted only before retry; test-review-and-fix.sh degraded-retry-oos-preserved expects both first and second bodies and two JSONL records. Append OOS after the first core pass and/or before retry overwrites round artifacts; optionally append again if the retry changes round_oos.
- **Suggested revision**: Address the concern above.


### FINDING_15: correctness: skills/review-and-fix/scripts/review-and-fix.sh:986-1030
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] OOS append moved after degraded retry without preserving first-pass round OOS First review-core run can write non-empty round-N/oos-accepted-review.md; retry truncates/regenerates that file via review-core; append_round_oos_artifact runs only once so accumulated-oos.jsonl/md never receive the first-pass OOS if the final file is empty or smaller. Append OOS after the first core pass when non-empty and again after retry (or snapshot/merge first-pass OOS before retry).
- **Suggested revision**: Address the concern above.


### FINDING_16: correctness: skills/review-and-fix/scripts/review-and-fix.sh:990-1029
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Degraded panel retry re-runs review-core before OOS from the first attempt is accumulated; append_round_oos_artifact runs only once after the retry. Stub in test-review-and-fix.sh:1325-1351 writes different OOS on attempt 1 vs 2; only the post-retry file remains so accumulated-oos.md/jsonl cannot contain both bodies as asserted in test-review-and-fix.sh:1373-1375. Append or merge round OOS after the first degraded attempt (before overwrite) or teach the retry path to accumulate without dropping the first body.
- **Suggested revision**: Address the concern above.


### FINDING_18: correctness: skills/review-and-fix/scripts/review-and-fix.sh:convergence_candidate_status+PartA
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] convergence_candidate_status treats fix-applied as eligible for Part A early-termination Two consecutive low-accept rounds can overwrite REVIEW_AND_FIX_STATUS=fix-applied with converged-small-changes; breaks test 5b intent and may confuse Step 5 consumers that branch on fix-applied. Remove fix-applied from convergence_candidate_status or skip Part A when status is fix-applied.
- **Suggested revision**: Address the concern above.


### FINDING_19: risk-integration: skills/implement/SKILL.md:1382
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Exit-0 prose lumps converged-small-changes with no accepted findings remaining Orchestrator mis-reads convergence as an empty-accept round and may apply wrong follow-up reasoning Split converged-small-changes into its own bullet: stop re-review loop; do not equate with zero accepted findings
- **Suggested revision**: Address the concern above.


### FINDING_2: **Important** `correctness` `skills/review-and-fix/scripts/review-and-fix.sh:142` / `skills/review-and-fix/scripts/review-and-fix.sh:1205`  
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `correctness` `skills/review-and-fix/scripts/review-and-fix.sh:142` / `skills/review-and-fix/scripts/review-and-fix.sh:1205`      `convergence_candidate_status` includes `fix-applied`, so a round that actually applied and committed review fixes can be overwritten to `REVIEW_AND_FIX_STATUS=converged-small-changes`. Concrete scenario: round 1 has 1 accepted finding, round 2 has 1 accepted finding, the coder applies round 2 successfully, and no Important findings exist; line 1205 changes the status from `fix-applied` to `converged-small-changes`. The `/implement` Step 5 contract only runs post-fix relevant checks for `fix-applied`, while `converged-small-changes` is treated as terminal, so the just-committed review-fix code can skip checks. Remove `fix-applied` from the convergence candidate statuses, or only run convergence before coder dispatch / when no edits were applied.
- **Suggested revision**: Address the concern above.


### FINDING_4: architecture: skills/review-and-fix/scripts/review-and-fix.sh:990-1030
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] append_round_oos_artifact runs only after degraded retry so first-attempt OOS can be overwritten before accumulation Degraded first core writes oos-accepted-review.md then retry overwrites it; accumulated-oos.md/jsonl lose first-attempt OOS (regression test 5a expectation) Append or snapshot-merge round OOS before re-invoking review-core.sh or merge both attempts into accumulated files
- **Suggested revision**: Address the concern above.


