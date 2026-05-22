Here is the normalized structured finding list (merged duplicates; `FINDING_2`/`FINDING_5` and `FINDING_3`/`FINDING_6` collapsed; `FINDING_4`/`FINDING_8`/`FINDING_9` merged with `[OUT_OF_SCOPE]` retained on the heading per your rule).

```text
### FINDING_1: Non-ASCII apostrophe in local-cleanup doc
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: [nit] `scripts/local-cleanup.md` uses Unicode right single quotation mark (U+2019) in “PR’s” instead of an ASCII apostrophe, which is inconsistent with typical doc typography and can complicate copy/paste or scripted searches.
- **Suggested revision**: Replace U+2019 with an ASCII apostrophe (e.g. `PR's`).

### FINDING_2: Squash-merge remote-advance gap in harness and contract doc
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: [important] The local-cleanup integration harness does not advance `origin/main` with non-`larch-logs` paths between pre-fetch and Step 3 while local `main` stays flush-only ahead, so CI could stay green if `git diff` logic wrongly falls back to post-fetch `origin/main`. Separately, [nit] `scripts/test-local-cleanup.md` does not document that scenario, so maintainers may drop it when refactoring.
- **Suggested revision**: Add a fourth sandbox that pushes a non-`larch-logs` commit to the bare remote after a local flush-only ahead state; assert the expected drop warning and that `HEAD` matches `origin/main` after cleanup (`scripts/test-local-cleanup.sh` / `scripts/local-cleanup.sh` as cited). Document that fourth case in `scripts/test-local-cleanup.md` next to the existing three paths.

### FINDING_3: Missing automated coverage for RELEASE_ALREADY_LATEST early exit
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: [latent] The new `RELEASE_ALREADY_LATEST` early exit in `.claude/skills/release/scripts/promote-latest-release.sh` has no automated coverage; regressions in the guard or string comparison would not fail existing Makefile harness targets.
- **Suggested revision**: Add a stubbed `gh`/`jq` harness or extract a small testable guard function so the branch is exercised by CI.

### FINDING_4: [OUT_OF_SCOPE] Monolithic branch mixes unrelated concerns
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt
- **Concern**: [nit] One branch/PR bundles unrelated work (e.g. promote-latest-release, version bump, local-cleanup, and `larch-logs` flush), which complicates review, bisect, and revert because fixing or backing out one concern may drag others along.
- **Suggested revision**: Split into focused PRs/branches per concern, or explicitly justify intentional bundling in the PR description if policy allows a single merge.

### FINDING_5: [OUT_OF_SCOPE] Theoretical vacuous `_all_flushes` when log is empty but ahead>0
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: [nit] Rare path: `_all_flushes` could be vacuous if `git log` emits no lines while `ahead_before>0`, which could theoretically skew orphan-drop predicates; noted as not introduced by the pre-fetch SHA edit.
- **Suggested revision**: If hardening, add an explicit guard when the log is empty but `rev-list` still reports ahead commits (`scripts/local-cleanup.sh` as cited).
```
