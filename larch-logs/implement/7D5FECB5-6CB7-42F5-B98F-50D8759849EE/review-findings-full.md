### FINDING_1: panel [code-review/accepted]

## **Important** `correctness` `skills/implement/scripts/commit-implementation.sh:41-52`, `skills/implement/scripts/commit-review-fixes.sh:41-52`, `skills/implement/scripts/cleanup.sh:33-41`  

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `correctness` `skills/implement/scripts/commit-implementation.sh:41-52`, `skills/implement/scripts/commit-review-fixes.sh:41-52`, `skills/implement/scripts/cleanup.sh:33-41`      These wrappers lose the child command’s failing exit code because `rc=$?` is read after an `if ...; then ...; fi` compound with no `else`, which returns `0` when the condition fails. Concrete scenario: `git-commit.sh` exits non-zero because a hook rejects the commit; the wrapper emits `COMMITTED=false` but exits `0`, so Step 4/7 can continue as if the commit wrapper succeeded. Move failure handling into an `else` branch and capture `$?` there, or run the helper first, store `rc`, then branch on it; add tests where the stubbed helper exits non-zero.
- **Suggested revision**: Address the concern above.

### FINDING_11: panel [code-review/accepted]

## architecture: skills/implement/SKILL.md:30

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Invariant #4 ordering still names tracking-issue-summary.sh for metadata. Doc SSOT diverges from post-tracking-issue.sh entry point. Update invariant text to post-tracking-issue.sh.
- **Suggested revision**: Address the concern above.

### FINDING_16: panel [code-review/accepted]

## code-quality: skills/implement/SKILL.md:1764

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Step 16 prose ties STATUS=ok to code-review-tally batch, not write-rejected-findings.sh behavior. Orchestrator looks for the wrong artifact when STATUS=ok. Reword to rejected-findings.md and optional tmp log copy.
- **Suggested revision**: Address the concern above.

### FINDING_19: panel [code-review/accepted]

## code-quality: skills/implement/SKILL.md:1899

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Step 18 prose still names tracking-issue-summary for final upsert path references old direct helper Update to write-final-report.sh
- **Suggested revision**: Address the concern above.

### FINDING_20: panel [code-review/accepted]

## correctness: skills/implement/SKILL.md:1724-1730 skills/implement/scripts/refresh-execution-issues.sh:48-72

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Step 11 passes ISSUE_NUMBER default 0; refresh script treats 0 as valid and calls gh for issue #0 refresh fails; SKILL uses || true so metadata refresh silently skipped; stale execution-issues count on tracking issue Skip refresh when issue missing or reject issue 0 in script
- **Suggested revision**: Address the concern above.

### FINDING_21: panel [code-review/accepted]

## correctness: skills/implement/SKILL.md:1764

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Step 16 prose ties write-rejected-findings STATUS=ok to code-review-tally batch write-rejected-findings.sh only logs and optional copy Reword Step 16 helper description
- **Suggested revision**: Address the concern above.

### FINDING_22: panel [code-review/accepted]

## correctness: skills/implement/SKILL.md:569-570,629-630,710-710

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Step 0.5 still keys abort/deferred branches on FAILED=true from tracking-issue-summary.sh after switching to post-tracking-issue.sh post-tracking-issue.sh wraps tracking-issue-summary and never emits FAILED=true on stdout; gh metadata failure exits 1 with POSTED=false only; orchestrator following SKILL misses Branch 2/3 abort and Branch 4 deferred/clear-ISSUE_NUMBER wiring Update SKILL to use POSTED=false / ERROR= / exit status from post-tracking-issue.sh
- **Suggested revision**: Address the concern above.

### FINDING_23: panel [code-review/accepted]

## correctness: skills/implement/SKILL.md:569-629-710

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Step 0.5 still instructs parsing FAILED=true from tracking-issue-summary.sh after switching to post-tracking-issue.sh. Orchestrator may not abort or defer when metadata upsert fails because post-tracking-issue.sh emits POSTED=false and exits non-zero instead of FAILED=true on outer stdout. Update SKILL to post-tracking-issue envelope (POSTED=false, non-zero exit, ERROR=) per post-tracking-issue.md.
- **Suggested revision**: Address the concern above.

### FINDING_25: panel [code-review/accepted]

## correctness: skills/implement/scripts/cleanup.sh:33-41

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] After failed if test rc=$? reads compound if status 0 not cleanup-tmpdir exit code Cleanup failure yields exit 0 so callers think step succeeded while tmpdir may remain Capture cleanup-tmpdir exit without relying on $? after if or use else branch with explicit rc
- **Suggested revision**: Address the concern above.

### FINDING_26: panel [code-review/accepted]

## correctness: skills/implement/scripts/cleanup.sh:851-859

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] On cleanup-tmpdir failure rc=$? after if can be 0 so script exits success CLEANED=false but exit 0 masks cleanup failure Capture cleanup-tmpdir exit code outside if semantics
- **Suggested revision**: Address the concern above.

### FINDING_27: panel [code-review/accepted]

## correctness: skills/implement/scripts/commit-implementation.sh:41-52

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] skills/implement/scripts/commit-review-fixes.sh:41-52 rc captured after if test is wrong when git-commit.sh fails bash if-without-else yields exit status 0 on failed condition; wrapper exits 0 with COMMITTED=false; orchestrator treats failed commit as success Capture git-commit exit in else branch or assign rc immediately after git-commit
- **Suggested revision**: Address the concern above.

### FINDING_3: panel [code-review/accepted]

## **Important** `correctness` `skills/implement/scripts/write-final-report.sh:90-101`  

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 4. **Important** `correctness` `skills/implement/scripts/write-final-report.sh:90-101`      A failed `tracking-issue-summary.sh` upsert is reported as `STATUS=skipped` with exit `0`, even though the contract has `STATUS=failed` for failures. Concrete scenario: GitHub auth or network fails during Step 17; no `larch:final-summary` comment is posted, but the helper exits successfully and the orchestrator has no failure signal beyond a misleading skipped status. Emit `STATUS=failed` for upsert failures and either return non-zero or update the SKILL.md call site to explicitly treat final-summary posting as best-effort while logging the failure.
- **Suggested revision**: Address the concern above.

### FINDING_32: panel [code-review/accepted]

## correctness: skills/implement/scripts/refresh-execution-issues.sh:1360-1379

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] refresh overwrites larch:metadata body with a 3-line summary using the same marker as Step 0.5 After Step 11 the tracking-issue metadata comment loses agent/coder/Larch version and other fields published at 0.5 Merge fields with post-tracking-issue content or use a distinct marker for execution-issue refresh only
- **Suggested revision**: Address the concern above.

### FINDING_33: panel [code-review/accepted]

## correctness: skills/implement/scripts/write-final-report.md vs write-final-report.sh

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] STATUS failed vs skipped semantics for upsert errors Hard to classify GitHub-side failures Align contract and STATUS values or document mapping
- **Suggested revision**: Address the concern above.

### FINDING_34: panel [code-review/accepted]

## correctness: skills/implement/scripts/write-final-report.sh:92-101

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Upsert failure maps to STATUS=skipped and exit 0, overloading skipped vs real skip; contradicts contract STATUS=failed. Step 17 thinks final-summary posted when GitHub upsert failed; STATUS=skipped matches issue-not-set path. Use STATUS=failed and non-zero exit on upsert failure; reserve skipped for ISSUE=0; extend tests.
- **Suggested revision**: Address the concern above.

### FINDING_35: panel [code-review/accepted]

## correctness: skills/implement/scripts/write-final-report.sh:92-101 skills/implement/SKILL.md:1894-1899

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] tracking-issue-summary failure maps to STATUS=skipped with exit 0; Step 18 uses || true. GitHub final-summary comment can fail without non-zero shell status; failure logging guidance in SKILL does not match behavior. Use non-zero exit or STATUS=failed for real failures; align Step 18 prose and || true usage.
- **Suggested revision**: Address the concern above.

### FINDING_4: panel [code-review/accepted]

## **Important** `risk-integration` `skills/implement/scripts/refresh-execution-issues.sh:61-73`, `skills/implement/scripts/post-tracking-issue.sh:68-86`  

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 3. **Important** `risk-integration` `skills/implement/scripts/refresh-execution-issues.sh:61-73`, `skills/implement/scripts/post-tracking-issue.sh:68-86`      `refresh-execution-issues.sh` upserts the same `larch:metadata` marker used by Step 0.5 but rewrites the body to only `Run ID`, `Logs`, and `Execution issues pending flush`, dropping the original tracking issue, agent, coder, and Larch version fields. Concrete scenario: Step 0.5 publishes metadata, Step 11 refreshes execution issues, and the tracking issue’s metadata comment no longer contains the run metadata consumers expect. Preserve the existing metadata fields and append/update an execution-issues section, or use a separate marker for execution-issue projection.
- **Suggested revision**: Address the concern above.

### FINDING_42: panel [code-review/accepted]

## risk-integration: skills/implement/SKILL.md:1899

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Stale reference to tracking-issue-summary in Step 18 prose. Confuses maintainers reading Step 18 cleanup. Reword to write-final-report.sh.
- **Suggested revision**: Address the concern above.

### FINDING_43: panel [code-review/accepted]

## risk-integration: skills/implement/SKILL.md:1899

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Step 18 failure-capture prose still names tracking-issue-summary.sh while upsert moved inside write-final-report.sh. Step 18 tool-failure logs may omit final-summary post failures. Update prose to write-final-report.sh or add internal failure logging in the script.
- **Suggested revision**: Address the concern above.

### FINDING_44: panel [code-review/accepted]

## risk-integration: skills/implement/SKILL.md:301-302,355-356,776

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Stale tracking-issue-summary.sh failure text after extraction Mis-triage and wrong failure log naming when new scripts fail Update prose to post-tracking-issue / refresh-execution-issues / write-final-report and their errors
- **Suggested revision**: Address the concern above.

### FINDING_45: panel [code-review/accepted]

## risk-integration: skills/implement/SKILL.md:569-629-710

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Step 0.5 still documents FAILED=true from tracking-issue-summary while post-tracking-issue.sh emits POSTED/ERROR and hides child output in tmp files. Orchestrator may not abort on metadata failure because FAILED=true never appears on the tool transcript. Update prose to POSTED=false / ERROR / exit code for post-tracking-issue.sh on all branches.
- **Suggested revision**: Address the concern above.

### FINDING_47: panel [code-review/accepted]

## risk-integration: skills/implement/scripts/refresh-execution-issues.sh:61-73

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Refresh upserts larch:metadata with a minimal body, replacing richer Step 0.5 metadata. Operators lose agent/coder/larch version from the live GitHub metadata comment after refresh. Merge full metadata with execution-issue count or use a separate marker.
- **Suggested revision**: Address the concern above.

### FINDING_48: panel [code-review/accepted]

## risk-integration: skills/implement/scripts/test-commit-implementation.sh

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No git-commit failure path. COMMITTED=false and ERROR emission can break unnoticed. Run stub with GIT_COMMIT_RC=1 and assert output.
- **Suggested revision**: Address the concern above.

