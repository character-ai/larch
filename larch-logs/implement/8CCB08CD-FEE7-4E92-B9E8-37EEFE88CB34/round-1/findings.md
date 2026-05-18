### FINDING_1: [OUT_OF_SCOPE] code-quality: skills/implement/scripts/hook-stop-fail-close.sh:39
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] SessionStart copies the existing conditional LARCH_TOKEN_SESSION_ID export pattern from the Stop hook. Shared latent env inheritance (see in-scope item) predates SessionStart. Fix in both places if you harden session binding semantics.
- **Suggested revision**: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] risk-integration: branch vs main (merge-pr git-force-push plugin.json larch-logs)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Multiple independent behavioral areas ship in one diff Sessionstart tests do not exercise merge-pr or force-push paths Use separate PRs or at least run full make lint harness buckets including test-harnesses-6 for merge-pr
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] risk-integration: skills/implement/scripts/hook-stop-fail-close.sh:35-39
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Sibling Stop hook mirrors conditional LARCH_TOKEN_SESSION_ID export without clearing inherited env. Same stale-env vs missing session_id interaction as sessionstart (not introduced here). Align with unset/export pattern if sessionstart is hardened; file not in branch diff.
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: implementation_plan (run-log)
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Plan text references test cases 12-16 but the harness labels cases 12-15b without a case 16. Mild doc/plan drift; coverage still maps to the feature bullets. Renumber plan text to match 12-15b (or add a case 16 label in tests if desired).
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: scripts/sessionstart-health.sh:116-119
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Two separate jq invocations on the same INPUT for cwd and session_id. Slightly higher cost and more failure points than needed. Single jq read producing both fields.
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: scripts/test-sessionstart-health.md:4-5
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Stray ')' before the period in 'boundary state).' breaks contract prose. Readers mis-parse the sentence; minor doc defect. Remove the stray parenthesis.
- **Suggested revision**: Address the concern above.

### FINDING_7: code-quality: scripts/test-sessionstart-health.sh (case numbering vs plan)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Implementation plan text referenced tests 12-16; harness uses 12-15b naming with no combined multi-boundary case. Reviewers comparing to the plan may think coverage is missing. Rename or add one combined case, or align the plan document numbering.
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: scripts/sessionstart-health.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] When session_id is omitted from stdin LARCH_TOKEN_SESSION_ID is not cleared before resolve_implement_tmpdir Inherited stale LARCH_TOKEN_SESSION_ID can skew session binding and suppress advisories fail-open Unset LARCH_TOKEN_SESSION_ID or export empty when SID absent before resolver call
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: scripts/sessionstart-health.sh:129-131
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] When jq-parsed session_id is empty, inherited LARCH_TOKEN_SESSION_ID is not cleared before resolve_implement_tmpdir, so lib-resolve session binding can reject the real tmpdir and skip boundary advisories. Keepalive has SESSION_ID=A; process env has LARCH_TOKEN_SESSION_ID=B from a wrapper leak; stdin omits session_id. Resolver binds on B, finds no matching keepalive, returns empty; pending manifest/review/bump boundaries emit no advisory (false negative vs resume re-prompt). Unset LARCH_TOKEN_SESSION_ID (or otherwise neutralize stale exports) whenever SID is empty after parsing, before calling resolve_implement_tmpdir.
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: scripts/sessionstart-health.sh:129-131
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Conditional export leaves inherited LARCH_TOKEN_SESSION_ID active when JSON session_id is empty, so resolve_implement_tmpdir can session-bind using stale env instead of TTL-only selection. Wrong tmpdir chosen or advisories missing/extra under a wrapper that exports LARCH_TOKEN_SESSION_ID while SessionStart payload omits session_id. unset LARCH_TOKEN_SESSION_ID before resolve or export LARCH_TOKEN_SESSION_ID="${SID:-}" from payload; mirror any change in hook-stop-fail-close.sh for consistency.
- **Suggested revision**: Address the concern above.

### FINDING_11: risk-integration: implementation_plan Files to Modify vs diff:scripts/merge-pr.sh scripts/merge-pr.md scripts/test-merge-pr.sh
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Branch diff changes merge-pr and its offline harness extensively but those paths are not listed in the supplied four-file implementation plan. A reviewer or release note author who trusts only the sessionstart plan misses new merge/flush-recovery and CI re-check behavior merged on the same branch. Update the plan or PR description to list all touched surfaces or split unrelated changes so the plan matches the diff.
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: scripts/merge-pr.md:48
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Step 4 lists OID mismatch as unconditional fail-closed while flush recovery can resolve some OID mismatches Operators misread step 4 as exhaustive hard-fail list Qualify OID mismatch or cross-reference flush recovery subsection
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: scripts/merge-pr.sh scripts/test-merge-pr.sh (branch vs pasted plan)
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Branch diff includes merge-pr flush-recovery and related harness changes not described in the SessionStart-only feature_description / implementation_plan excerpt. Reviewers expecting a single-feature PR may mis-scope review, bisect, or revert. Split unrelated changes or make PR scope explicit in description.
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: scripts/sessionstart-health.sh:116-131
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Pre-existing LARCH_TOKEN_SESSION_ID is not cleared when SessionStart JSON omits session_id; resolver uses strict session binding per lib-resolve-implement-tmpdir.sh. Resolver returns empty tmpdir despite an active CLONE_PATH-bound run within TTL; post-/design|review|bump boundary advisories are silently skipped. Unset LARCH_TOKEN_SESSION_ID before exporting from payload (only export when SID non-empty).
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: scripts/sessionstart-health.sh:129-131
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] LARCH_TOKEN_SESSION_ID is set when SID is nonempty but not cleared when SID is empty. Inherited stale LARCH_TOKEN_SESSION_ID skews resolve_implement_tmpdir session binding so boundary advisories may omit or mis-associate the active tmpdir. Unset or clear-export LARCH_TOKEN_SESSION_ID when session_id is absent; export only after parsing a nonempty SID.
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: scripts/test-sessionstart-health.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No regression asserts all three boundary advisories appear together when design manifest review summary and bump armed are all pending Plan edge case simultaneous boundaries MSG concatenation could regress without CI catching Add one tmpdir fixture and assert one JSON additionalContext contains post-/design post-/review and post-/bump-version substrings
- **Suggested revision**: Address the concern above.

### FINDING_17: risk-integration: scripts/test-sessionstart-health.sh:375-445
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] No regression case asserts combined post-/design + post-/review + post-/bump-version advisories in one SessionStart emission. Concatenation or append_msg regressions could ship undetected. Add one harness case expecting all three boundary phrases in a single additionalContext.
- **Suggested revision**: Address the concern above.

### FINDING_18: security: scripts/sessionstart-health.sh:31
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Unbounded read of SessionStart stdin into INPUT via cat. Very large stdin can exhaust memory in the hook process during SessionStart. Bound the read (e.g. head -c with a documented maximum) before jq parsing.
- **Suggested revision**: Address the concern above.

