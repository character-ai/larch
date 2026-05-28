### FINDING_14: [OUT_OF_SCOPE] architecture: scripts/lint-awk-multibyte-regex.md:37
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Rule 2 example cites dac0d00c POSIX-class hypothesis commit Doc inconsistency with plan non-goals only Update historical example to #3144 em-dash family
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_15: [OUT_OF_SCOPE] code-quality: docs/linting.md:237
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Harness table omits round-1 test cases Doc lag vs scripts/test-lint-awk-multibyte-regex.sh Extend harness row to list added fixtures
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_21: [OUT_OF_SCOPE] risk-integration: scripts/lint-awk-multibyte-regex.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Lint does not detect mawk POSIX [[:class:]] in dynamic regex (plan non-goal). [[:space:]]-style mawk failures would not be caught at commit time. File follow-up lint or document limitation prominently if that class remains a concern.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_22: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **security** `scripts/lint-awk-multibyte-regex.sh:15-41` — `--root PATH` allows scanning any directory’s `*.sh` / `*.awk` trees when invoked outside the default pre-commit path (same contract as `lint-bare-grep-probe.sh`). **Suggested fix:** Only relevant if a caller ever passes untrusted `--root`; keep invocation limited to repo root / harness tempdirs.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_23: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **security** `scripts/lint-awk-multibyte-regex.sh:88` — `path="$ROOT/$rel"` does not canonicalize `..` or reject repo-internal symlinks that resolve outside the root; a malicious tree entry could cause the linter to read unexpected files (shared with the bare-grep-probe family). **Suggested fix:** Reject `rel` values containing `..` and/or resolve paths with a root-prefix check before `awk` reads them.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_24: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **correctness** `scripts/ship-pr.sh:1932-1947` — If both `baseline_head` and `vendor_head` are the literal `unknown`, the equality branch fires and can misclassify as `first-fixer-non-health` (plan noted detached-HEAD guard makes this rare). **Suggested fix:** Require known SHAs (`!= unknown`) before the no-commit bail, matching the original plan guard.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_30: [OUT_OF_SCOPE] code-quality: CHANGELOG.md:17-18
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] New lint listed under Fixed instead of Added/Changed. Misleading changelog categorization only; no runtime impact. Recategorize under Added or Changed in a follow-up docs commit.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_36: [OUT_OF_SCOPE] architecture: scripts/test-ship-pr.sh:238-257
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Global make_repo launcher stubs auto-commit beyond plan's enumerated tier-order edits. Broader harness behavior change than plan listed. Document in test comments or narrow to cases that need it.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_37: [OUT_OF_SCOPE] architecture: docs/linting.md
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Harness cases 13-17 not reflected in docs row. Docs slightly under-describe harness scope. Add cases 13-17 to docs/linting.md and test-lint-awk-multibyte-regex.md if desired.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_7: [OUT_OF_SCOPE] architecture: scripts/ship-pr.md
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Contract doc omits new no-commit vendor bail Operators relying on ship-pr.md alone miss #3134 routing Update ship-pr.md in a follow-up
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_8: [OUT_OF_SCOPE] correctness: scripts/lint-awk-multibyte-regex.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Lint does not detect ASCII POSIX classes in dynamic awk Original mawk [[:space:]] incident class not caught by multibyte-only rules Tracked as plan non-goals; separate issue if still needed
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

