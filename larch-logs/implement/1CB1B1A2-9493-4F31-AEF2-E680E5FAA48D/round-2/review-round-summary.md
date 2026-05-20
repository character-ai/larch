# Review Round 2

- Mode: `diff`
- Accepted findings: 10
- Rejected findings: 8
- Exonerated findings: 3
- Neutral findings: 15

## Accepted Findings

### FINDING_10: code-quality: scripts/drop-bump-commit.sh:145-155
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Stale WARN still references HEAD subject after walk-back refactor Misleading stderr when bump is not at HEAD Update WARN to found-commit phrasing consistent with adjacent branches
- **Suggested revision**: Address the concern above.


### FINDING_12: code-quality: scripts/implement-finalize.sh:538
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Comment references skipped-no-bullets path though that status is no longer emitted. Maintainers misread control flow when debugging Step 8a. Rewrite comment for post–Item J behavior.
- **Suggested revision**: Address the concern above.


### FINDING_15: correctness: .claude/skills/bump-version/scripts/apply-bump.md (~invariants / larch-log-flush bullet)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Still claims drop-bump-commit requires the bump at HEAD, contradicting Item H walk-back (flush on top of bump). Operators read apply-bump.md and believe flush-after-bump is incompatible with drop; tests show the opposite. Rewrite the invariant to match walk-back drop semantics.
- **Suggested revision**: Address the concern above.


### FINDING_20: correctness: scripts/create-pr.sh (gh pr create failure path)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Item I required argv diagnostics redacted via scripts/redact-tmpdir-paths.sh; implementation only hand-redacts title/body in GH_CREATE_ARGV and never invokes the helper. Tmpdir-bearing or sensitive argv fragments can leak into stderr and execution-issues attachments. Pipe the final argv diagnostic string through REDACT_TMPDIR_HELPER before larch_err.
- **Suggested revision**: Address the concern above.


### FINDING_24: correctness: scripts/implement-finalize.sh:706-710
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Execution-issue prose says no manifest even when manifest_exists=true for an empty or bullet-less manifest file. Operator trusts ERROR line over manifest_exists and misdiagnoses the failure mode. Tighten prose to bullets/manifest content absent while keeping stable status token.
- **Suggested revision**: Address the concern above.


### FINDING_34: risk-integration: scripts/implement-finalize.md:61
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] CHANGELOG_STATUS enum still lists skipped-no-bullets but maybe_update_changelog no longer emits that value after Item J. Downstream parsers or humans following the doc expect skipped-no-bullets on no-bullet/no-issue runs; runtime now emits fail-no-manifest-no-issue and changelog-failed so doc-driven expectations never match. Update the enum (or mark deprecated with migration note) to match code; align any consumer docs.
- **Suggested revision**: Address the concern above.


### FINDING_37: risk-integration: skills/implement/scripts/test-step-8a-changelog.sh (fixture c)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Item J calls for append_execution_issue including ERROR=Cannot generate changelog bullet…; test does not read execution-issues.md. Regression could drop the execution-issue append while postbump stderr still mentions the phrase. Assert_file_contains on IMPLEMENT_TMPDIR/execution-issues.md for the ERROR= line.
- **Suggested revision**: Address the concern above.


### FINDING_5: architecture: scripts/drop-bump-commit.md (Edit-in-sync list vs repo)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Behavioral expansion (walk-back) without updating named cross-references (e.g. rebase-rebump-subprocedure.md). Subprocedure prose may still describe HEAD-only drop. Update referenced docs if maintainers treat the checklist as mandatory.
- **Suggested revision**: Address the concern above.


### FINDING_7: code-quality: .claude/skills/bump-version/scripts/apply-bump.md:27;scripts/apply-bump.sh:83-88;scripts/test-apply-bump.sh:985-1013
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Docs and test name say rebase-in-progress; implementation and fixture cover generic unmerged paths via merge --no-conflict. Operators may mis-attribute exit 4 to rebases only; plan text and behavior disagree slightly. Rename or reword consistently (merge or rebase) or narrow detection if rebase-only is required.
- **Suggested revision**: Address the concern above.


### FINDING_8: code-quality: docs/linting.md:229-230
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Harness catalog omits new test-apply-bump exit-4 coverage and test-git-push stderr dedup coverage. Readers of docs/linting.md underestimate harness scope. Extend the two table descriptions for make test-apply-bump and make test-git-push.
- **Suggested revision**: Address the concern above.


