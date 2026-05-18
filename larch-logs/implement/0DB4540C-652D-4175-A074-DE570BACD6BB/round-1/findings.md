### FINDING_1: **Important** `risk-integration` `scripts/merge-pr.sh:173-175`, `scripts/git-force-push.sh:43-48`: the new caller classifies local commits against `PR_HEAD_OID`, but `git-force-push.sh` refreshes `origin/$BRANCH` immediately before `--force-with-lease`, so a remote commit pushed after the PR view can be overwritten. Concrete failing scenario: `gh pr view` returns `aaaa1111`, local HEAD is `aaaa1111 + flush`, another process pushes `dddd4444`, then the helper fetches `dddd4444` and the lease permits replacing it with the local flush-only head. Fix by using an explicit expected lease for this recovery path, e.g. a helper option that pushes with `--force-with-lease=refs/heads/$BRANCH:$PR_HEAD_OID`, and bail if the remote no longer equals the PR OID.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Important** `risk-integration` `scripts/merge-pr.sh:173-175`, `scripts/git-force-push.sh:43-48`: the new caller classifies local commits against `PR_HEAD_OID`, but `git-force-push.sh` refreshes `origin/$BRANCH` immediately before `--force-with-lease`, so a remote commit pushed after the PR view can be overwritten. Concrete failing scenario: `gh pr view` returns `aaaa1111`, local HEAD is `aaaa1111 + flush`, another process pushes `dddd4444`, then the helper fetches `dddd4444` and the lease permits replacing it with the local flush-only head. Fix by using an explicit expected lease for this recovery path, e.g. a helper option that pushes with `--force-with-lease=refs/heads/$BRANCH:$PR_HEAD_OID`, and bail if the remote no longer equals the PR OID.
- **Suggested revision**: Address the concern above.

### FINDING_2: **Important** `risk-integration` `scripts/merge-pr.sh:173-184`, `scripts/merge-pr.sh:247-265`: after force-pushing the flush commits, the script continues using the CI and merge-state result collected for the old PR head. Concrete failing scenario: PR head `aaaa1111` has passing checks, local `cccc3333` is force-pushed by the recovery path, GitHub checks for `cccc3333` are still pending, and line 264 can still run `gh pr merge --squash --admin` based on stale `CI_GOOD=true`. Fix by making recovery restart or re-run the PR metadata and `gh pr checks` gates for the updated `headRefOid` before any merge attempt.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `risk-integration` `scripts/merge-pr.sh:173-184`, `scripts/merge-pr.sh:247-265`: after force-pushing the flush commits, the script continues using the CI and merge-state result collected for the old PR head. Concrete failing scenario: PR head `aaaa1111` has passing checks, local `cccc3333` is force-pushed by the recovery path, GitHub checks for `cccc3333` are still pending, and line 264 can still run `gh pr merge --squash --admin` based on stale `CI_GOOD=true`. Fix by making recovery restart or re-run the PR metadata and `gh pr checks` gates for the updated `headRefOid` before any merge attempt.
- **Suggested revision**: Address the concern above.

### FINDING_3: **Nit** `code-quality` `scripts/merge-pr.sh:167`: when the ahead range is empty, `grep -c .` prints `0` and exits 1, then `|| echo "0"` appends a second zero, producing `FLUSH_COUNT=$'0\n0'` and a Bash arithmetic warning. Replace the count pipeline with `grep -c . || true` without the extra echo, or use `awk 'NF { c++ } END { print c + 0 }'`.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 3. **Nit** `code-quality` `scripts/merge-pr.sh:167`: when the ahead range is empty, `grep -c .` prints `0` and exits 1, then `|| echo "0"` appends a second zero, producing `FLUSH_COUNT=$'0\n0'` and a Bash arithmetic warning. Replace the count pipeline with `grep -c . || true` without the extra echo, or use `awk 'NF { c++ } END { print c + 0 }'`.
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] code-quality: docs/linting.md
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] make test-merge-pr row omits flush recovery coverage File not modified by this branch diff Update linting doc in a follow-up if desired
- **Suggested revision**: Address the concern above.

### FINDING_5: architecture: scripts/merge-pr.md:26-30
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Doc says recovery runs before the OID precondition; code runs it on OID mismatch. Misleading reading order for operators maintaining the gate. Reword to describe recovery as part of OID mismatch handling and post-push re-read.
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: scripts/merge-pr.md:26-30
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Doc says recovery runs before OID step 1 precondition Readers expect a pre-check before rev-parse equality; code runs only after mismatch Match wording to actual control flow when OID differs
- **Suggested revision**: Address the concern above.

### FINDING_7: code-quality: scripts/merge-pr.md:26-30
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Doc says flush recovery runs before OID step 1 Read literally it implies ordering that differs from when the branch actually runs Rephrase to describe OID mismatch trigger and recovery role in the gate
- **Suggested revision**: Address the concern above.

### FINDING_8: code-quality: scripts/merge-pr.md:26-31
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Doc says recovery runs before step 1 OID check Reader may expect a separate pre-check; code runs on OID mismatch Rephrase to match branch inside OID failure handling
- **Suggested revision**: Address the concern above.

### FINDING_9: code-quality: scripts/merge-pr.md:48
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Step 4 still states OID mismatch always fails closed; flush path can recover some OID mismatches. Operators treat step 4 as exhaustive hard-fail list and miss flush exception. Qualify OID mismatch or cross-reference flush subsection.
- **Suggested revision**: Address the concern above.

### FINDING_10: code-quality: scripts/merge-pr.md:54
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Doc says flush recovery runs before OID step 1; code runs on OID mismatch after the check. Readers mis-locate the recovery branch when tracing merge-pr.sh. Reword to when step 1 fails (HEAD ≠ headRefOid) / on OID mismatch.
- **Suggested revision**: Address the concern above.

### FINDING_11: code-quality: scripts/merge-pr.md:60-62
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Batched discovery implies a single gh pr view for OID precondition; flush recovery adds another pr view. API-count or audit assumptions omit the extra round-trip. Note optional second gh pr view on flush recovery.
- **Suggested revision**: Address the concern above.

### FINDING_12: code-quality: scripts/test-merge-pr.sh:121-124
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Fake git fetch accepts any origin fetch not just origin main. Future unintended fetch could pass tests unnoticed. Narrow stub to expected ref arguments.
- **Suggested revision**: Address the concern above.

### FINDING_13: correctness: scripts/merge-pr.sh:158-171
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Flush recovery does not verify PR head OID is an ancestor of local HEAD before force-push Rare non-ancestor OID mismatch with 1-5 local-only subjects matching the flush pattern could still classify as recoverable and overwrite remote-only PR history Require git merge-base --is-ancestor "$PR_HEAD_OID" HEAD before _flush_recoverable=true
- **Suggested revision**: Address the concern above.

### FINDING_14: correctness: scripts/merge-pr.sh:159-171
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Flush recovery does not require PR_HEAD_OID to be an ancestor of HEAD. Non-ancestor OID mismatch with 1-5 commits whose subjects all match the flush prefix could be treated as recoverable and force-push. Add an explicit ancestor check (e.g. git merge-base --is-ancestor) before classifying as recoverable.
- **Suggested revision**: Address the concern above.

### FINDING_15: correctness: scripts/merge-pr.sh:166-170
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] FLUSH_COUNT uses grep -c . with || echo 0 When pr_head..HEAD log is empty grep -c exits 1 so FLUSH_COUNT becomes multiline; [[ -gt 0 ]] causes bash stderr syntax error on every empty-range OID mismatch while still refusing merge Remove || echo 0 or count lines without treating zero matches as failure
- **Suggested revision**: Address the concern above.

### FINDING_16: correctness: scripts/test-merge-pr.sh:334-347
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Success-path test only exercises one flush commit, not N in 2-5. Regression gap for multi-commit flush-only ahead ranges that the feature text calls out. Add or extend a test with 2-5 flush-only subjects and recovery stubs.
- **Suggested revision**: Address the concern above.

### FINDING_17: risk-integration: scripts/merge-pr.sh:174
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] git-force-push stderr is silenced Operators see only MERGE_RESULT=error without the underlying push/fetch reason Stop discarding stderr or capture and append a short failure snippet to ERROR
- **Suggested revision**: Address the concern above.

### FINDING_18: risk-integration: scripts/merge-pr.sh:174
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] git-force-push stderr discarded on recovery path Operators only see generic force-push failed ERROR without underlying git/gh reason Remove 2>/dev/null on git-force-push.sh invocation or log stderr to a controlled sink
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: scripts/merge-pr.sh:174
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] git-force-push stderr discarded while diagnosing push failures is harder. Operators only see generic force-push failed without lease/denial details. Preserve or surface stderr via larch_err or targeted logging.
- **Suggested revision**: Address the concern above.

### FINDING_20: risk-integration: scripts/test-merge-pr.sh:334-347
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Sub-test K only covers one flush commit ahead Multi-flush 2-5 subject success path from the feature text is untested Add a passing case with multiple flush-only subjects within the cap
- **Suggested revision**: Address the concern above.

### FINDING_21: risk-integration: scripts/test-merge-pr.sh:334-392
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Success path only tests one flush-ahead commit Plan asked for 1-5 flush-only recovery; boundaries 2-5 (especially 5) success untested Add sub-test with five valid flush subjects expecting merge success
- **Suggested revision**: Address the concern above.

