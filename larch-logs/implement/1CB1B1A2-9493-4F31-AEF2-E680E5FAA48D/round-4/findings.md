### FINDING_1: **Nit** `code-quality` `scripts/test-git-push.md:3` — The sibling harness docs are stale for changed tests: `scripts/test-git-push.md`, `scripts/test-create-pr.md`, and `scripts/test-drop-bump-commit.md` do not describe the new dedup, empty-diagnostic, or walk-back coverage added in `scripts/test-git-push.sh`, `scripts/test-create-pr.sh`, and `scripts/test-drop-bump-commit.sh`. Update those sibling `.md` stubs to match the new assertions.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Nit** `code-quality` `scripts/test-git-push.md:3` — The sibling harness docs are stale for changed tests: `scripts/test-git-push.md`, `scripts/test-create-pr.md`, and `scripts/test-drop-bump-commit.md` do not describe the new dedup, empty-diagnostic, or walk-back coverage added in `scripts/test-git-push.sh`, `scripts/test-create-pr.sh`, and `scripts/test-drop-bump-commit.sh`. Update those sibling `.md` stubs to match the new assertions.
- **Suggested revision**: Address the concern above.

### FINDING_2: **Nit** `code-quality` `skills/implement/scripts/test-step-8a-changelog.sh:199` — Fixture (b) claims to cover “empty manifest + ISSUE_NUMBER”, but it passes `MANIFEST_PATH=""`, so it only covers the no-manifest path and not the valid-empty-JSON manifest path in `scripts/implement-finalize.sh:701-704`. Add a `{}` manifest fixture with `ISSUE_NUMBER` set and pass that path, so the stated fallback behavior is actually pinned.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Nit** `code-quality` `skills/implement/scripts/test-step-8a-changelog.sh:199` — Fixture (b) claims to cover “empty manifest + ISSUE_NUMBER”, but it passes `MANIFEST_PATH=""`, so it only covers the no-manifest path and not the valid-empty-JSON manifest path in `scripts/implement-finalize.sh:701-704`. Add a `{}` manifest fixture with `ISSUE_NUMBER` set and pass that path, so the stated fallback behavior is actually pinned.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: scripts/drop-bump-commit.sh:102-106
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] No-bump warning cites configured max depth rather than actual walked ancestor count. Slightly weaker signal when the branch is shorter than max_depth. Include searched depth in the WARN text if you want strict plan fidelity.
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: scripts/implement-finalize.md:43-44,scripts/implement-finalize.md:98-99
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Postbump/Step 8a documentation still describes a single skip+execution-issues shape for no bullets and a blanket skip when no bullets exist. Operators following implement-finalize.md expect an execution-issues append on every no-bullet skip and may misunderstand fail-no-manifest-no-issue vs JSON skip vs ISSUE_NUMBER fallback. Rewrite lines 43-44 and 98-99 to match implement-finalize.sh:695-726 branches and which paths write execution-issues.md.
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: scripts/implement-finalize.sh:706-710
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Nested local fallback_line inside maybe_update_changelog vs function-level local declarations. Minor readability and style drift only. Hoist fallback_line into the opening local list.
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: scripts/test-drop-bump-commit.sh:213
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Test 18 redirects drop-bump-commit stderr to /dev/null. Harder to diagnose intermittent failures in CI logs. Capture stderr and print on failure or remove 2>/dev/null.
- **Suggested revision**: Address the concern above.

### FINDING_7: risk-integration: .claude/skills/bump-version/scripts/apply-bump.sh:102-107;scripts/test-apply-bump.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Plan cited stable substring rebase in progress and MERGE_HEAD-style fixture; implementation and test use unmerged paths present and a real merge conflict. Downstream runbooks grepping only rebase in progress would miss exit-4 text; behavior is still a distinct exit 4 before dirty-tree checks. Update plan/runbooks or add optional assertion for the old phrase if compatibility matters.
- **Suggested revision**: Address the concern above.

### FINDING_8: risk-integration: scripts/implement-finalize.md:37,scripts/implement-finalize.sh:280-287
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Doc marks PR_TITLE required for postbump state but require_postbump_state_keys does not list PR_TITLE. Resume or hand-built postbump state without PR_TITLE passes validation and loses the optional title suffix in the changelog fallback line. Add PR_TITLE to require_postbump_state_keys with an explicit empty policy or relax the doc wording.
- **Suggested revision**: Address the concern above.

### FINDING_9: risk-integration: scripts/implement-finalize.sh:695-716
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Item J fallback is narrower than plan wording: synthetic Closed bullet runs only for empty MANIFEST_PATH or jq-valid manifest; non-JSON manifest with ISSUE_NUMBER set still takes skipped-no-bullets. A misrouted manifest.env-style path plus a real issue id never gets the Closed: #N fallback; only silent skip + breadcrumb unless operators fix manifest routing. Decide intended contract; if broader fallback is desired, branch before jq and treat invalid JSON like empty bullets with issue context; else document the JSON/empty-path gate explicitly in implement-finalize.md / plan.
- **Suggested revision**: Address the concern above.

### FINDING_10: risk-integration: skills/implement/scripts/test-step-8a-changelog.sh:1955-1984
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Sandbox harness duplicates implement-finalize.sh and a hand-picked helper set. Future postbump changes that add new sourced helpers can break CI until the harness copy list is updated. When adding postbump dependencies, extend build_sandbox in the same PR (same pattern as other stub harnesses).
- **Suggested revision**: Address the concern above.

### FINDING_11: security: scripts/implement-finalize.sh:706-710
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Changelog fallback interpolates ISSUE_NUMBER and PR_TITLE into markdown without single-line sanitization. If PR_TITLE or issue context contains newlines (mis-set state, unusual API data, or tmpdir/state tampering), the synthetic bullet can span multiple lines or inject extra markdown list lines into CHANGELOG.md, breaking changelog structure and downstream parsers. Normalize issue/title to a safe single line (strip CR/LF/control chars, optional max length) or skip fallback when validation fails.
- **Suggested revision**: Address the concern above.

