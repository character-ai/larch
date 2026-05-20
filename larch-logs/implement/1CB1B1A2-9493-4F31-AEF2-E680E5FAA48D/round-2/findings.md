### FINDING_1: [OUT_OF_SCOPE] architecture: CHANGELOG.md:574
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Historical note references skipped-no-bullets routing not touched by this branch diff. Reader confusion only. Update only if doing a docs sweep; not introduced here.
- **Suggested revision**: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] code-quality: CHANGELOG.md:574
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Historical note references skipped-no-bullets routing; file not in branch diff. N/A Leave or update separately from this PR.
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] code-quality: scripts/create-pr.sh:150-152
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Push stderr not redacted in error message Pre-existing pattern unchanged this PR Optionally mirror PR-create redaction for push failures in a follow-up
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] code-quality: scripts/implement-finalize.sh:720-723
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicate set +e around write_changelog_entry. Minor readability only. Remove redundant set +e when touching this file for other reasons.
- **Suggested revision**: Address the concern above.

### FINDING_5: architecture: scripts/drop-bump-commit.md (Edit-in-sync list vs repo)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Behavioral expansion (walk-back) without updating named cross-references (e.g. rebase-rebump-subprocedure.md). Subprocedure prose may still describe HEAD-only drop. Update referenced docs if maintainers treat the checklist as mandatory.
- **Suggested revision**: Address the concern above.

### FINDING_6: architecture: skills/implement/scripts/test-step-8a-changelog.sh (overall shape)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Plan asked for a narrow shim around maybe_update_changelog; harness runs full postbump with many stubs. Higher harness maintenance cost than the plan implied. Optional refactor to a smaller shim if desired.
- **Suggested revision**: Address the concern above.

### FINDING_7: code-quality: .claude/skills/bump-version/scripts/apply-bump.md:27;scripts/apply-bump.sh:83-88;scripts/test-apply-bump.sh:985-1013
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Docs and test name say rebase-in-progress; implementation and fixture cover generic unmerged paths via merge --no-conflict. Operators may mis-attribute exit 4 to rebases only; plan text and behavior disagree slightly. Rename or reword consistently (merge or rebase) or narrow detection if rebase-only is required.
- **Suggested revision**: Address the concern above.

### FINDING_8: code-quality: docs/linting.md:229-230
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Harness catalog omits new test-apply-bump exit-4 coverage and test-git-push stderr dedup coverage. Readers of docs/linting.md underestimate harness scope. Extend the two table descriptions for make test-apply-bump and make test-git-push.
- **Suggested revision**: Address the concern above.

### FINDING_9: code-quality: scripts/create-pr.sh:170-197
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Item I specified argv redaction via redact-tmpdir-paths.sh; GH_CREATE_ARGV is hand-built with fixed placeholders instead of piping real argv through the helper. Tmp paths or richer argv shapes may leak or diverge from the repo redaction contract the plan called for. Build argv text from actual invocation args and run it through scripts/redact-tmpdir-paths.sh before larch_err.
- **Suggested revision**: Address the concern above.

### FINDING_10: code-quality: scripts/drop-bump-commit.sh:145-155
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Stale WARN still references HEAD subject after walk-back refactor Misleading stderr when bump is not at HEAD Update WARN to found-commit phrasing consistent with adjacent branches
- **Suggested revision**: Address the concern above.

### FINDING_11: code-quality: scripts/drop-bump-commit.sh:159
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Stale WARN still references HEAD subject after walk-back to HEAD~FOUND_AT. Misleading stderr when bump is below HEAD. Update WARN string to reference HEAD~FOUND_AT like sibling messages.
- **Suggested revision**: Address the concern above.

### FINDING_12: code-quality: scripts/implement-finalize.sh:538
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Comment references skipped-no-bullets path though that status is no longer emitted. Maintainers misread control flow when debugging Step 8a. Rewrite comment for post–Item J behavior.
- **Suggested revision**: Address the concern above.

### FINDING_13: code-quality: scripts/implement-finalize.sh:538
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Stale skipped-no-bullets comment after Item J behavior change. Misleading for future edits to maybe_update_changelog. Reword comment to describe empty categories feeding fallback/fail logic.
- **Suggested revision**: Address the concern above.

### FINDING_14: code-quality: scripts/test-drop-bump-commit.sh:1141
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Test 18 discards drop-bump stderr Regression failures lose WARN context Capture stderr like sibling tests
- **Suggested revision**: Address the concern above.

### FINDING_15: correctness: .claude/skills/bump-version/scripts/apply-bump.md (~invariants / larch-log-flush bullet)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Still claims drop-bump-commit requires the bump at HEAD, contradicting Item H walk-back (flush on top of bump). Operators read apply-bump.md and believe flush-after-bump is incompatible with drop; tests show the opposite. Rewrite the invariant to match walk-back drop semantics.
- **Suggested revision**: Address the concern above.

### FINDING_16: correctness: .claude/skills/bump-version/scripts/apply-bump.md:27-32
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Doc narrows exit 4 to rebase-only while script covers merge and generic unmerged paths Operators grep for rebase-only strings or mis-handle merge-conflict exit 4 Align apply-bump.md wording with apply-bump.sh ERROR text and semantics
- **Suggested revision**: Address the concern above.

### FINDING_17: correctness: .claude/skills/bump-version/scripts/apply-bump.sh
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Awk second-field extraction for porcelain paths can break on paths with spaces. Hypothetical repo with spaced paths would list wrong conflict targets while still exiting 4. Use cut/sed-based porcelain parsing.
- **Suggested revision**: Address the concern above.

### FINDING_18: correctness: .claude/skills/bump-version/scripts/apply-bump.sh (emit_kv ERROR for unmerged paths)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] ERROR wording diverges from the plan’s specified rebase-in-progress phrasing; tests assert a different stable prefix. External parsers matching the plan’s exact ERROR text would not trigger on this branch. Align ERROR prefix with the plan or declare the implemented string canonical across docs/tests.
- **Suggested revision**: Address the concern above.

### FINDING_19: correctness: .claude/skills/bump-version/scripts/apply-bump.sh + apply-bump.md + scripts/test-apply-bump.sh
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Item E plan/test called for rebase-in-progress phrasing; implementation uses unmerged paths present and tests merge conflict UU. No functional miss for UU detection; traceability to written plan diverges. Align message/test with plan or revise plan wording to merge-or-rebase semantics.
- **Suggested revision**: Address the concern above.

### FINDING_20: correctness: scripts/create-pr.sh (gh pr create failure path)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Item I required argv diagnostics redacted via scripts/redact-tmpdir-paths.sh; implementation only hand-redacts title/body in GH_CREATE_ARGV and never invokes the helper. Tmpdir-bearing or sensitive argv fragments can leak into stderr and execution-issues attachments. Pipe the final argv diagnostic string through REDACT_TMPDIR_HELPER before larch_err.
- **Suggested revision**: Address the concern above.

### FINDING_21: correctness: scripts/drop-bump-commit.md (**Invariant** paragraph)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Invariant text still describes only git reset --hard HEAD~1 as the destructive primitive. Does not document rebase --onto path introduced for found_at>0. Extend invariant wording to cover reset and rebase-on-drop plus abort-on-failure behavior.
- **Suggested revision**: Address the concern above.

### FINDING_22: correctness: scripts/drop-bump-commit.sh:159
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Stale WARN says HEAD matches bump pattern when the matched commit can be at HEAD~N. On ALLOWED_FAILED with found_at>0 the message incorrectly names HEAD as the bump commit. Use found commit at HEAD~FOUND_AT wording like sibling branches.
- **Suggested revision**: Address the concern above.

### FINDING_23: correctness: scripts/implement-finalize.sh:699-703
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Fallback changelog embeds PR_TITLE raw. Rare odd PR titles could yield awkward CHANGELOG.md bullets. Sanitize or truncate PR_TITLE for markdown bullet context.
- **Suggested revision**: Address the concern above.

### FINDING_24: correctness: scripts/implement-finalize.sh:706-710
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Execution-issue prose says no manifest even when manifest_exists=true for an empty or bullet-less manifest file. Operator trusts ERROR line over manifest_exists and misdiagnoses the failure mode. Tighten prose to bullets/manifest content absent while keeping stable status token.
- **Suggested revision**: Address the concern above.

### FINDING_25: correctness: scripts/implement-finalize.sh:710
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] ERROR text claims no manifest when failure can be empty manifest bullets with MANIFEST_PATH set Operator follows ERROR=no manifest while manifest_exists=true in the same execution-issue line Reword ERROR to reflect missing bullets / missing tracking issue, not missing manifest file
- **Suggested revision**: Address the concern above.

### FINDING_26: risk-integration: .claude/skills/bump-version/scripts/apply-bump.md (exit 4 section) vs .claude/skills/bump-version/scripts/apply-bump.sh:97-106
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Doc says rebase-specific exit 4 but code treats any unmerged index state (merge included) Downstream runbooks assume rebase-only semantics and pick wrong recovery Align documentation with merge-or-rebase behavior or narrow detection if rebase-only is required
- **Suggested revision**: Address the concern above.

### FINDING_27: risk-integration: .claude/skills/bump-version/scripts/apply-bump.sh:83-88
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Item E plan text emphasizes rebase-in-progress wording; shipped ERROR uses unmerged paths present. Operator regexes tuned to plan phrasing miss exit-4 events. Align ERROR copy and/or tests with the agreed substring contract.
- **Suggested revision**: Address the concern above.

### FINDING_28: risk-integration: docs/linting.md:229
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] test-apply-bump row omits new exit-4 unmerged-path harness coverage. Contributors rely on linting.md for harness inventory; new case is undocumented. Add exit-4 unmerged-path coverage to the test-apply-bump description.
- **Suggested revision**: Address the concern above.

### FINDING_29: risk-integration: scripts/create-pr.sh:170-171
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Item I plan specified argv redaction via redact-tmpdir-paths.sh; argv is hand-assembled with literal redacted placeholders. Rare future leak if argv embeds tmp paths outside placeholders. Run argv through redact helper or document intentional manual redaction.
- **Suggested revision**: Address the concern above.

### FINDING_30: risk-integration: scripts/create-pr.sh:170-197
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] GH_CREATE_ARGV diagnostic omits redact-tmpdir-paths for head/base/repo fragments Local branch names or bases that embed cache/tmp path segments leak into stderr-driven logs when PR creation fails Run argv diagnostic through redact-tmpdir-paths (or redact BRANCH/BASE_REF) before larch_err
- **Suggested revision**: Address the concern above.

### FINDING_31: risk-integration: scripts/create-pr.sh:170-197
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] PR-create failure diagnostics omit redact-tmpdir-paths.sh on argv/stderr/stdout tail per Item I. Tmp paths or other sensitive gh output can be copied verbatim into operator-facing errors. Pipe the composed diagnostic through scripts/redact-tmpdir-paths.sh before larch_err; keep fail-closed if helper missing.
- **Suggested revision**: Address the concern above.

### FINDING_32: risk-integration: scripts/drop-bump-commit.sh:159
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] LARCH_BUMP_FILES allow-list failure still logs HEAD-only bump wording When bump is at HEAD~N with custom LARCH_BUMP_FILES, WARN falsely claims HEAD matched the bump pattern, misleading triage Update WARN to reference HEAD~FOUND_AT like the default-path branch
- **Suggested revision**: Address the concern above.

### FINDING_33: risk-integration: scripts/drop-bump-commit.sh:92-105
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] WARNING always cites full MAX_DEPTH even if walk stopped early for missing parents Shallow history shows within N commits of HEAD though fewer commits were examined Emit walked depth or reason when rev-parse fails before depth limit
- **Suggested revision**: Address the concern above.

### FINDING_34: risk-integration: scripts/implement-finalize.md:61
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] CHANGELOG_STATUS enum still lists skipped-no-bullets but maybe_update_changelog no longer emits that value after Item J. Downstream parsers or humans following the doc expect skipped-no-bullets on no-bullet/no-issue runs; runtime now emits fail-no-manifest-no-issue and changelog-failed so doc-driven expectations never match. Update the enum (or mark deprecated with migration note) to match code; align any consumer docs.
- **Suggested revision**: Address the concern above.

### FINDING_35: risk-integration: scripts/implement-finalize.md:61
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] CHANGELOG_STATUS enum still lists skipped-no-bullets but implement-finalize.sh no longer emits it. Downstream parsers expecting skipped-no-bullets as the non-fatal skip signal desynchronize from runtime. Remove or deprecate skipped-no-bullets in the documented enum to match emitted statuses.
- **Suggested revision**: Address the concern above.

### FINDING_36: risk-integration: scripts/implement-finalize.sh:911-937;scripts/test-implement-finalize.sh:1366-1393
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Soft skip changed to hard fail when no bullets and no issue context Workflows expecting skipped-no-bullets now get changelog-failed and bail Ensure ISSUE_NUMBER is always populated for postbump runs that may lack bullets document contract change for consumers
- **Suggested revision**: Address the concern above.

### FINDING_37: risk-integration: skills/implement/scripts/test-step-8a-changelog.sh (fixture c)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Item J calls for append_execution_issue including ERROR=Cannot generate changelog bullet…; test does not read execution-issues.md. Regression could drop the execution-issue append while postbump stderr still mentions the phrase. Assert_file_contains on IMPLEMENT_TMPDIR/execution-issues.md for the ERROR= line.
- **Suggested revision**: Address the concern above.

### FINDING_38: risk-integration: skills/implement/scripts/test-step-8a-changelog.sh:1688-1704
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Fixture (c) never asserts execution-issues.md append with ERROR=… as Item J requires. append_execution_issue could fail silently while warn_line still satisfies stdout/stderr grep. assert_file_contains on SANDBOX/tmp/execution-issues.md for ERROR=Cannot generate changelog bullet…
- **Suggested revision**: Address the concern above.

### FINDING_39: security: scripts/create-pr.sh:190-196
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] gh failure diagnostics may leak raw stderr/stdout without tmpdir redaction gh prints paths or sensitive tokens into captured streams; logs expose them Run redact-tmpdir-paths on diagnostic segments or document accepted leakage
- **Suggested revision**: Address the concern above.

### FINDING_40: security: scripts/implement-finalize.sh:920-927
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] PR_TITLE from state is copied into CHANGELOG fallback without markdown hardening Malformed or adversarial PR titles alter changelog presentation or link behavior Normalize or escape PR_TITLE for synthetic Closed line or cap/strip unsafe characters
- **Suggested revision**: Address the concern above.

