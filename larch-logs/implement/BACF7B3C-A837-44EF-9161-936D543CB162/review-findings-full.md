### FINDING_1: panel [code-review/accepted]

## **Important** `risk-integration` `scripts/ship-pr.md:37`, `scripts/ship-pr.md:66`  

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `risk-integration` `scripts/ship-pr.md:37`, `scripts/ship-pr.md:66`      `scripts/ship-pr.md` still documents exit 0 as a `CI_PASSED=true` prompt-side checkpoint and says `ci-initial` exits after `ACTION=merge`. That contradicts the new `scripts/ship-pr.sh:990-993` behavior, where `ci-initial` advances to `ci-merge` and returns to the internal loop. A maintainer following this contract could reintroduce the removed orchestrator re-entry or mis-handle `CI_PASSED=true` after a completed run. Update the helper contract to say `ci-initial` continues into `ci-merge` in the same invocation, and remove `CI_PASSED=true` as an exit-0 checkpoint.
- **Suggested revision**: Address the concern above.

### FINDING_12: panel [code-review/accepted]

## correctness: scripts/ship-pr.md:35-37,scripts/ship-pr.md:61-67

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] ship-pr contract doc still claims CI_PASSED=true mid-run checkpoint and ci-initial merge exits process before ci-merge Reader expects second ship-pr invocation at ci-merge after ci-initial merge; implementation continues in-loop and may merge same invocation Update exit-0 semantics and ci-initial/merge invariant lines to match return-based loop continuation
- **Suggested revision**: Address the concern above.

### FINDING_14: panel [code-review/accepted]

## risk-integration: external/out-of-tree review-and-fix callers

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Exit-3-only detection for applied fixes External automation never sees rc 3 again Parse REVIEW_AND_FIX_STATUS=fix-applied on rc 0
- **Suggested revision**: Address the concern above.

### FINDING_19: panel [code-review/accepted]

## risk-integration: scripts/ship-pr.sh:990-993 scripts/ship-pr.sh:1166-1173

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Part 4a collapse has no new regression test in diff; Makefile still runs test-ship-pr separately. Future regression in phase advance or ci-merge continuation could ship while test-review-and-fix and pre-commit stay green. Add extend test-ship-pr.sh or focused harness asserting ci-initial merge leads into ci-merge in one process without outer re-entry.
- **Suggested revision**: Address the concern above.

### FINDING_2: panel [code-review/accepted]

## **Nit** `code-quality` `scripts/test-ship-pr.sh:357`  

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Nit** `code-quality` `scripts/test-ship-pr.sh:357`      The existing `ci_initial` harness assertion still describes the old “merge checkpoint” behavior and would pass both before and after the `exit 0` -> `return 0` change. Add a regression assertion that proves same-invocation collapse happened, such as `PHASE=done`, a post-merge sentinel, or a merge/postmerge stub call count.
- **Suggested revision**: Address the concern above.

### FINDING_20: panel [code-review/accepted]

## risk-integration: scripts/test-ship-pr.md:13

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Harness doc still calls ci-initial ACTION=merge an exit-0 checkpoint Contributors mis-model PHASE at first return and add wrong assertions Update bullet to continuous ci-initial to ci-merge behavior optional PHASE assertions
- **Suggested revision**: Address the concern above.

### FINDING_22: panel [code-review/accepted]

## risk-integration: skills/review-and-fix/scripts/review-and-fix.sh orchestrator exit

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Exit 3 success signal removed External scripts keyed on exit 3 break silently Document in CHANGELOG or consumer docs branch on REVIEW_AND_FIX_STATUS=fix-applied
- **Suggested revision**: Address the concern above.

### FINDING_23: panel [code-review/accepted]

## risk-integration: skills/review-and-fix/scripts/review-and-fix.sh:363-410 skills/review-and-fix/scripts/review-and-fix.md:16-90 skills/implement/SKILL.md:1358-1365

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Orchestrator fix-applied path now exits 0 with REVIEW_AND_FIX_STATUS=fix-applied instead of exit 3 External wrappers that only keyed on exit code 3 may skip post-fix checks or mis-handle the review loop Parse REVIEW_AND_FIX_STATUS (and document breaking contract for downstreams)
- **Suggested revision**: Address the concern above.

### FINDING_8: panel [code-review/accepted]

## code-quality: scripts/test-ship-pr.sh:353-357

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Test label still says ci-initial merge checkpoint though flow is usually single-invocation Misleading PASS diagnostics only Rename assertion label optional PHASE assert
- **Suggested revision**: Address the concern above.

