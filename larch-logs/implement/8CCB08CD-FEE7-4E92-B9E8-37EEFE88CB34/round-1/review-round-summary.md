# Review Round 1

- Mode: `diff`
- Accepted findings: 7
- Rejected findings: 2
- Exonerated findings: 6
- Neutral findings: 0

## Accepted Findings

### FINDING_11: risk-integration: implementation_plan Files to Modify vs diff:scripts/merge-pr.sh scripts/merge-pr.md scripts/test-merge-pr.sh
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Branch diff changes merge-pr and its offline harness extensively but those paths are not listed in the supplied four-file implementation plan. A reviewer or release note author who trusts only the sessionstart plan misses new merge/flush-recovery and CI re-check behavior merged on the same branch. Update the plan or PR description to list all touched surfaces or split unrelated changes so the plan matches the diff.
- **Suggested revision**: Address the concern above.


### FINDING_12: risk-integration: scripts/merge-pr.md:48
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Step 4 lists OID mismatch as unconditional fail-closed while flush recovery can resolve some OID mismatches Operators misread step 4 as exhaustive hard-fail list Qualify OID mismatch or cross-reference flush recovery subsection
- **Suggested revision**: Address the concern above.


### FINDING_16: risk-integration: scripts/test-sessionstart-health.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No regression asserts all three boundary advisories appear together when design manifest review summary and bump armed are all pending Plan edge case simultaneous boundaries MSG concatenation could regress without CI catching Add one tmpdir fixture and assert one JSON additionalContext contains post-/design post-/review and post-/bump-version substrings
- **Suggested revision**: Address the concern above.


### FINDING_4: code-quality: implementation_plan (run-log)
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Plan text references test cases 12-16 but the harness labels cases 12-15b without a case 16. Mild doc/plan drift; coverage still maps to the feature bullets. Renumber plan text to match 12-15b (or add a case 16 label in tests if desired).
- **Suggested revision**: Address the concern above.


### FINDING_6: code-quality: scripts/test-sessionstart-health.md:4-5
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Stray ')' before the period in 'boundary state).' breaks contract prose. Readers mis-parse the sentence; minor doc defect. Remove the stray parenthesis.
- **Suggested revision**: Address the concern above.


### FINDING_8: correctness: scripts/sessionstart-health.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] When session_id is omitted from stdin LARCH_TOKEN_SESSION_ID is not cleared before resolve_implement_tmpdir Inherited stale LARCH_TOKEN_SESSION_ID can skew session binding and suppress advisories fail-open Unset LARCH_TOKEN_SESSION_ID or export empty when SID absent before resolver call
- **Suggested revision**: Address the concern above.


### FINDING_9: correctness: scripts/sessionstart-health.sh:129-131
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] When jq-parsed session_id is empty, inherited LARCH_TOKEN_SESSION_ID is not cleared before resolve_implement_tmpdir, so lib-resolve session binding can reject the real tmpdir and skip boundary advisories. Keepalive has SESSION_ID=A; process env has LARCH_TOKEN_SESSION_ID=B from a wrapper leak; stdin omits session_id. Resolver binds on B, finds no matching keepalive, returns empty; pending manifest/review/bump boundaries emit no advisory (false negative vs resume re-prompt). Unset LARCH_TOKEN_SESSION_ID (or otherwise neutralize stale exports) whenever SID is empty after parsing, before calling resolve_implement_tmpdir.
- **Suggested revision**: Address the concern above.


