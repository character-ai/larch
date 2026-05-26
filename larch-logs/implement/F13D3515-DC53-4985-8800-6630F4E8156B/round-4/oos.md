### FINDING_12: [OUT_OF_SCOPE] risk-integration: docs/linting.md:238
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] make test-implement-bootstrap docs still describe calls 1-5 only Maintainers may under-run or mis-scope harness expectations Update the linting.md table row to calls 1-9 and the expanded case list
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_19: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **security** `scripts/write-session-env.sh:155-157` — `REPO=` is still written without the same charset/length validation applied to `--token-session-id` and path args. That predates this branch; `phase_infra` continues to forward session-setup’s `REPO` unchanged. **Suggested fix:** (separate change) add `OWNER/REPO` validation mirroring `implement-bootstrap.sh` / `get-issue-context.sh`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_20: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **risk-integration** `scripts/get-issue-context.sh:60-63` — upstream issue title/body land in `upstream-issue-*.txt` without the data-not-instructions envelope used by `tracking-issue-read.sh` for GitHub content. Fork-mode fetch is now centralized in `phase_tracking` but uses the same helper semantics as before (F4 best-effort binding). **Suggested fix:** wrap upstream files at write time or document mandatory sanitization before any model reads them.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_21: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 3. **security** `scripts/implement-bootstrap.sh:248-250` — `--caller-env` is forwarded/read without path confinement (Phase 1 surface). Not introduced here. **Suggested fix:** require absolute paths under an allowlisted session-cache prefix before `read-session-env-key.sh`. --- **Summary:** Phase 2/4 tracking adoption is security-sound for the stated trust model (session tmpdir from `session-setup.sh`, validated argv, quoted subprocess args). Prior review rounds already closed the main gaps (sentinel numeric/`RUN_ID` validation, resume `--issue-number` requirement, fork `--upstream-repo` + `--issue-number` coupling, redacted fork-context failures). No blocking or important security regressions remain in the diff.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_25: [OUT_OF_SCOPE] architecture: skills/implement/scripts/step2-implement.md:62-63
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] session-env presence alone marks issue-anchored without parent-issue ISSUE_NUMBER Deferred post failure leaves no sentinel; step2 anchoring still follows session-env file Pre-existing; not introduced by this branch
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_5: [OUT_OF_SCOPE] code-quality: scripts/write-session-env.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] [[ bashisms predate this branch Unrelated to phase_tracking tracking adoption No change required for this PR
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_6: [OUT_OF_SCOPE] correctness: scripts/implement-bootstrap.md
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 1. **correctness** `skills/implement/scripts/test-implement-bootstrap.sh` — No harness case drives `get-issue-state.sh` to return a non-`OPEN`/non-`CLOSED` `STATE` (e.g. unexpected enum) to assert the `STEP_FAILED=get-issue-state` exit-2 path documented in [`scripts/implement-bootstrap.md`](scripts/implement-bootstrap.md) and SKILL.md. **Why out of scope:** the production branch at `implement-bootstrap.sh:469-471` matches the plan; this is a test-completeness gap, not a demonstrated runtime defect in the shipped script.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_7: [OUT_OF_SCOPE] architecture
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 2. **architecture** `scripts/lint-foreground-markers.sh` — `implement-bootstrap.sh` is not on the Family B denylist yet; SKILL already marks the call foreground. **Why out of scope:** plan lists denylist enrollment as conditional on lint policy, not part of this phase’s required behavior.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_8: risk-integration: skills/implement/scripts/test-post-tracking-issue.sh:41-63
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] post-tracking-issue.sh gained --run-id and new RUN_ID precedence but its harness was not updated A regression in --run-id validation or precedence could ship while make test-post-tracking-issue and make lint still pass Extend test-post-tracking-issue.sh with override invalid-flag and fallback-chain cases per post-tracking-issue.md
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

