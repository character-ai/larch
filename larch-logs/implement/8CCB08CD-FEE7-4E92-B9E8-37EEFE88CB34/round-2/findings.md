### FINDING_1: **Important** `security` `SECURITY.md:46`: The branch adds SessionStart tmpdir resolution and boundary advisory behavior in `scripts/sessionstart-health.sh:116-149`, but `SECURITY.md` still documents only the PostToolUse/Stop hook trust model around this resolver. Concrete breakage: a consumer auditing shipped hooks before upgrade will not see that `SessionStart` now reads `cwd`/`session_id`, scans session roots through `lib-resolve-implement-tmpdir.sh`, and emits resolved tmpdir basenames into session context. Update `SECURITY.md:46-48` to cover the new SessionStart path, including fail-open behavior, session-id binding/TTL reuse, no file writes, and basename-only disclosure.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `security` `SECURITY.md:46`: The branch adds SessionStart tmpdir resolution and boundary advisory behavior in `scripts/sessionstart-health.sh:116-149`, but `SECURITY.md` still documents only the PostToolUse/Stop hook trust model around this resolver. Concrete breakage: a consumer auditing shipped hooks before upgrade will not see that `SessionStart` now reads `cwd`/`session_id`, scans session roots through `lib-resolve-implement-tmpdir.sh`, and emits resolved tmpdir basenames into session context. Update `SECURITY.md:46-48` to cover the new SessionStart path, including fail-open behavior, session-id binding/TTL reuse, no file writes, and basename-only disclosure.
- **Suggested revision**: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] architecture: scripts/sessionstart-health.sh:17
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] SessionStart hook uses set -e unlike implement hooks that omit -e for fail-open scripts. Pre-existing strictness model; boundary logic follows existing guarded patterns. Only revisit if standardizing hook strictness across the repo.
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] code-quality: docs/linting.md:240
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] make test-sessionstart description omits boundary stdin regression coverage. Discoverability only; not introduced by the touched files in this feature. Optionally extend the linting table row when editing docs.
- **Suggested revision**: Address the concern above.

### FINDING_4: architecture: supplied_plan_Files_to_Modify_vs_branch_diff
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] The_implementation_plan_lists_only_four_runtime_doc_files_but_the_branch_diff_also_changes_merge-pr.sh_test-merge-pr.sh_and_plugin.json Plan_fidelity_reviewers_cannot_trace_merge_PR_and_version_changes_to_the_stated_SessionStart_plan_without_external_context Update_the_plan_or_PR_scope_narrative_or_split_unrelated_changes
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: scripts/merge-pr.sh;scripts/test-merge-pr.sh;scripts/merge-pr.md (branch vs main)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Unrelated merge-pr flush-recovery and docs/tests ride on the same branch as SessionStart boundary advisories. Reviewers must validate two features in one pass; bisect/cherry-pick for a SessionStart regression isolates more commits than necessary. Split merge-pr recovery from SessionStart into separate PRs when workflow allows.
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: scripts/sessionstart-health.sh:1-4
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Opening header comment omits stdin JSON and implement boundary advisories. Readers skimming only the top of the file may underestimate SessionStart behavior already documented at lines 14-15. Align the opening paragraph with scripts/sessionstart-health.md.
- **Suggested revision**: Address the concern above.

### FINDING_7: code-quality: scripts/sessionstart-health.sh:116-118
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Stdin JSON is parsed twice with separate jq invocations for cwd and session_id. Minor redundant CPU on every SessionStart; no user-visible failure mode. Combine into one jq extraction into a small helper or one TSV line.
- **Suggested revision**: Address the concern above.

### FINDING_8: code-quality: scripts/sessionstart-health.sh:116-118
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicate jq pipelines parse stdin twice for cwd and session_id. Extra process overhead and two parse passes on every non-empty SessionStart payload; low risk of inconsistency if jq flags differed per call. Parse once with a single jq invocation and split fields in shell.
- **Suggested revision**: Address the concern above.

### FINDING_9: code-quality: scripts/sessionstart-health.sh:136-150 vs skills/implement/scripts/hook-stop-fail-close.sh:52-80
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Three boundary file predicates duplicate the Stop hook’s halt logic. Future boundary sentinel changes may be updated in one hook and missed in the other, causing SessionStart advisories and Stop blocking to disagree until noticed. Consider a small shared sourced predicate helper if this logic keeps evolving in lockstep.
- **Suggested revision**: Address the concern above.

### FINDING_10: risk-integration: scripts/merge-pr.sh:166-180
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Flush-only OID recovery gates on commit subjects only, not on changed paths. A commit in PR_HEAD_OID..HEAD can carry arbitrary code while its %s subject still matches ^chore(larch-logs): flush ; merge-base can still pass, so merge-pr may force-push and continue as if the divergence were log-only. Add path-scoped verification (e.g. diffstat limited to larch-logs/) and/or a stricter subject template tied to larch-log-flush.sh.
- **Suggested revision**: Address the concern above.

### FINDING_11: risk-integration: scripts/sessionstart-health.md:25 / scripts/test-sessionstart-health.sh:375-460
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Doc claims malformed SessionStart JSON fails open; no harness asserts that. Future jq/stdin parsing changes could violate the fail-open contract without CI signal. Add stdin case with invalid JSON expecting exit 0 and empty stdout.
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: scripts/sessionstart-health.sh:116-136
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Boundary reinjection depends on exact CLONE_PATH vs SessionStart cwd string match inside lib-resolve-implement-tmpdir. If cwd in the JSON payload differs by symlink or trailing-slash normalization from CLONE_PATH in .larch-keepalive, resolve returns empty and the user gets no boundary advisory after a real halt. Normalize cwd and CLONE_PATH the same way at write and read, or document the exact path contract.
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: scripts/test-merge-pr.sh:131-134
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Fake git fetch stub accepts any `git fetch origin …` with exit 0. A mistaken `git fetch origin <unexpected>` in merge-pr.sh could pass offline tests that previously failed closed on unexpected argv, hiding regressions until real runs. Scope the relaxed stub to opt-in tests or restore strict `origin main` matching for legacy cases.
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: scripts/test-sessionstart-health.sh:402-404
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Case 13 combines assert_empty with a broad assert_not_contains needle boundary. Redundant with assert_empty; a future unrelated advisory containing substring boundary could false-fail the harness. Keep assert_empty or narrow needles to post-/design|review|bump-version markers.
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: scripts/test-sessionstart-health.sh:403-404
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Redundant assert_not_contains after assert_empty on stdout. Low signal; noise if assertions are used as documentation for expected invariants. Remove or replace with a materially stronger assertion.
- **Suggested revision**: Address the concern above.

### FINDING_16: security: scripts/sessionstart-health.sh:31
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Unbounded read of SessionStart stdin into INPUT before jq parsing Very large stdin can exhaust memory or delay SessionStart hook completion Bound stdin (e.g. head -c) or cap and skip boundary parsing when over limit
- **Suggested revision**: Address the concern above.

