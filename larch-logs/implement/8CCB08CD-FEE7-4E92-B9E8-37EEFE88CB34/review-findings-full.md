### FINDING_11: panel [code-review/accepted]

## risk-integration: implementation_plan Files to Modify vs diff:scripts/merge-pr.sh scripts/merge-pr.md scripts/test-merge-pr.sh

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Branch diff changes merge-pr and its offline harness extensively but those paths are not listed in the supplied four-file implementation plan. A reviewer or release note author who trusts only the sessionstart plan misses new merge/flush-recovery and CI re-check behavior merged on the same branch. Update the plan or PR description to list all touched surfaces or split unrelated changes so the plan matches the diff.
- **Suggested revision**: Address the concern above.

### FINDING_12: panel [code-review/accepted]

## risk-integration: scripts/merge-pr.md:48

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Step 4 lists OID mismatch as unconditional fail-closed while flush recovery can resolve some OID mismatches Operators misread step 4 as exhaustive hard-fail list Qualify OID mismatch or cross-reference flush recovery subsection
- **Suggested revision**: Address the concern above.

### FINDING_16: panel [code-review/accepted]

## risk-integration: scripts/test-sessionstart-health.sh

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No regression asserts all three boundary advisories appear together when design manifest review summary and bump armed are all pending Plan edge case simultaneous boundaries MSG concatenation could regress without CI catching Add one tmpdir fixture and assert one JSON additionalContext contains post-/design post-/review and post-/bump-version substrings
- **Suggested revision**: Address the concern above.

### FINDING_4: panel [code-review/accepted]

## code-quality: implementation_plan (run-log)

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Plan text references test cases 12-16 but the harness labels cases 12-15b without a case 16. Mild doc/plan drift; coverage still maps to the feature bullets. Renumber plan text to match 12-15b (or add a case 16 label in tests if desired).
- **Suggested revision**: Address the concern above.

### FINDING_6: panel [code-review/accepted]

## code-quality: scripts/test-sessionstart-health.md:4-5

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Stray ')' before the period in 'boundary state).' breaks contract prose. Readers mis-parse the sentence; minor doc defect. Remove the stray parenthesis.
- **Suggested revision**: Address the concern above.

### FINDING_8: panel [code-review/accepted]

## correctness: scripts/sessionstart-health.sh

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] When session_id is omitted from stdin LARCH_TOKEN_SESSION_ID is not cleared before resolve_implement_tmpdir Inherited stale LARCH_TOKEN_SESSION_ID can skew session binding and suppress advisories fail-open Unset LARCH_TOKEN_SESSION_ID or export empty when SID absent before resolver call
- **Suggested revision**: Address the concern above.

### FINDING_9: panel [code-review/accepted]

## correctness: scripts/sessionstart-health.sh:129-131

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] When jq-parsed session_id is empty, inherited LARCH_TOKEN_SESSION_ID is not cleared before resolve_implement_tmpdir, so lib-resolve session binding can reject the real tmpdir and skip boundary advisories. Keepalive has SESSION_ID=A; process env has LARCH_TOKEN_SESSION_ID=B from a wrapper leak; stdin omits session_id. Resolver binds on B, finds no matching keepalive, returns empty; pending manifest/review/bump boundaries emit no advisory (false negative vs resume re-prompt). Unset LARCH_TOKEN_SESSION_ID (or otherwise neutralize stale exports) whenever SID is empty after parsing, before calling resolve_implement_tmpdir.
- **Suggested revision**: Address the concern above.

### FINDING_1: panel [code-review/accepted]

## **Important** `security` `SECURITY.md:46`: The branch adds SessionStart tmpdir resolution and boundary advisory behavior in `scripts/sessionstart-health.sh:116-149`, but `SECURITY.md` still documents only the PostToolUse/Stop hook trust model around this resolver. Concrete breakage: a consumer auditing shipped hooks before upgrade will not see that `SessionStart` now reads `cwd`/`session_id`, scans session roots through `lib-resolve-implement-tmpdir.sh`, and emits resolved tmpdir basenames into session context. Update `SECURITY.md:46-48` to cover the new SessionStart path, including fail-open behavior, session-id binding/TTL reuse, no file writes, and basename-only disclosure.

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `security` `SECURITY.md:46`: The branch adds SessionStart tmpdir resolution and boundary advisory behavior in `scripts/sessionstart-health.sh:116-149`, but `SECURITY.md` still documents only the PostToolUse/Stop hook trust model around this resolver. Concrete breakage: a consumer auditing shipped hooks before upgrade will not see that `SessionStart` now reads `cwd`/`session_id`, scans session roots through `lib-resolve-implement-tmpdir.sh`, and emits resolved tmpdir basenames into session context. Update `SECURITY.md:46-48` to cover the new SessionStart path, including fail-open behavior, session-id binding/TTL reuse, no file writes, and basename-only disclosure.
- **Suggested revision**: Address the concern above.

### FINDING_10: panel [code-review/accepted]

## risk-integration: scripts/merge-pr.sh:166-180

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Flush-only OID recovery gates on commit subjects only, not on changed paths. A commit in PR_HEAD_OID..HEAD can carry arbitrary code while its %s subject still matches ^chore(larch-logs): flush ; merge-base can still pass, so merge-pr may force-push and continue as if the divergence were log-only. Add path-scoped verification (e.g. diffstat limited to larch-logs/) and/or a stricter subject template tied to larch-log-flush.sh.
- **Suggested revision**: Address the concern above.

### FINDING_11: panel [code-review/accepted]

## risk-integration: scripts/sessionstart-health.md:25 / scripts/test-sessionstart-health.sh:375-460

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Doc claims malformed SessionStart JSON fails open; no harness asserts that. Future jq/stdin parsing changes could violate the fail-open contract without CI signal. Add stdin case with invalid JSON expecting exit 0 and empty stdout.
- **Suggested revision**: Address the concern above.

