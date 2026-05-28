### FINDING_1: code-quality: scripts/ship-pr.sh:59,1758-1928
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] HEAD tracking uses file-scope _SAPCF_EFFECTIVE_HEAD instead of a return channel from _stage_and_push_ci_fixes. A future nested or parallel call to _stage_and_push_ci_fixes could leave stale effective_head and mis-classify vendor health. Return or write effective HEAD via an explicit out-parameter from _stage_and_push_ci_fixes.
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: CHANGELOG.md:17-18
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] New lint is documented under ### Fixed rather than ### Added. Release-note readers may misread a new enforcement surface as only a bugfix. Split Added vs Fixed bullets or use ### Changed with clear wording.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: scripts/test-ship-pr.sh:235-256,317-318
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] write_stubs makes every default CI launcher commit README.md, wider than plan per-case sentinel updates. Unrelated fix-loop cases always advance HEAD via the default stub, weakening tests that assumed a no-edit vendor. Limit auto-commit to cases that need it or keep explicit per-case launcher stubs only.
- **Suggested revision**: Address the concern above.

### FINDING_4: correctness: scripts/lint-awk-multibyte-regex.sh:309-316
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Rule 2 skips double-quoted awk program bodies. A future awk "… — …" / match(…) one-liner could reach CI and still break mawk-style harnesses without tripping this lint. Document as accepted gap or add double-quoted body tracking.
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: scripts/lint-awk-multibyte-regex.sh:45-340
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Large embedded awk program duplicates bare-grep enumeration boilerplate. Third similar lint would copy the same ~60 lines again. Defer shared lib-lint-scan.sh until a third consumer exists.
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] architecture: scripts/ship-pr.sh:2287-2290
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Per-job local fix calls _stage_and_push_ci_fixes without HEAD-non-advance escalation. Local fix can succeed with no Fix CI failure commit while vendor path would bail; behavior predates #3134. Track separately if per-job and vendor paths should share the same health contract.
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] code-quality: scripts/lint-awk-multibyte-regex.md:55
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Rule 2 example references dac0d00c and [[:space:]] alongside the em-dash. Readers may think the lint targets POSIX classes in dynamic regex. Clarify the example targets the em-dash byte only.
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: scripts/ship-pr.sh:1811-1932
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] HEAD-non-advance compares baseline_head to _SAPCF_EFFECTIVE_HEAD before refresh-run-logs, not post-_stage_and_push HEAD as the plan specifies. Vendor noop and no Fix CI failure commit, but refresh-run-logs commits larch logs: effective_head equals baseline_head while final_head advances, causing spurious first-fixer-non-health and exit 3. Compare baseline_head to final_head after _stage_and_push_ci_fixes (or move the effective snapshot past refresh); add a harness where refresh commits and vendor is noop expecting rc 0.
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: scripts/lint-awk-multibyte-regex.sh:137-146
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Rule 2 requires non-ASCII and a regex callsite on the same line. pat assigned with em-dash on one line and $0 ~ pat on the next (ASCII-only) is not flagged though runtime dynamic regex still carries multibyte bytes. Document as limitation or track non-ASCII awk assignments used later at regex sites.
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: scripts/lint-awk-multibyte-regex.sh:218-317
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Double-quoted awk programs are not body-scanned for Rule 2. awk "BEGIN { match($0, \"—\") }" bypasses Rule 2; Rule 1 does not apply without -v. Add double-quoted body tracking or document the gap in lint-awk-multibyte-regex.md.
- **Suggested revision**: Address the concern above.

### FINDING_11: correctness: scripts/lint-awk-multibyte-regex.sh:137-140
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Regex callsite detection requires spaces around ~ and !~. $0~pat or !~/x/ with multibyte on the pattern line is not flagged. Relax callsite patterns for common awk spacing in this repo.
- **Suggested revision**: Address the concern above.

### FINDING_12: correctness: scripts/lint-awk-multibyte-regex.sh:250-256
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] close_single_quoted_body closes on any single quote in the line when not opened on the current line. An apostrophe inside an awk string mid-body ends the span early and can miss a later match(..., "—") line. Close only on a real closing delimiter at line end or use a safer quote scanner.
- **Suggested revision**: Address the concern above.

### FINDING_13: code-quality: scripts/test-ship-pr.sh:238-256
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Default install_scripts launcher stub always commits README before LAUNCHER_EXIT=0. A future test using the default stub expecting no launcher commit could mask HEAD-non-advance detection. Keep default launcher stubs side-effect-free; commit only in opt-in cases.
- **Suggested revision**: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] architecture: CHANGELOG.md:10-11
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] #3134 changelog entry is under Fixed but describes new lint and ship-pr behavior. Miscategorized release note only. Move to Added/Changed in a follow-up if desired.
- **Suggested revision**: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] architecture: feature_description vs plan
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Original mawk [[:space:]] narrative vs multibyte-only lint scope. Docs disagree on root cause class; code follows plan non-goals. Align issue/PR narrative in a docs-only follow-up.
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: scripts/lint-awk-multibyte-regex.sh:218-317
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Rule 2 does not scan double-quoted awk program literals. A multibyte character in awk "match($0, \"—\")" would pass make lint and can still break assert_lint_ok-style harnesses on mawk. Add a failing fixture plus parser support for awk "..." bodies, or document and grep for the pattern if rare.
- **Suggested revision**: Address the concern above.

### FINDING_17: risk-integration: scripts/lint-awk-multibyte-regex.md:48-54
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Lint excludes POSIX [[:class:]] in dynamic awk regex per plan non-goals. Reintroducing only ASCII POSIX classes in dynamic match() (original #3134 hypothesis) passes lint but can still fail on Ubuntu mawk CI. File a follow-up lint or mawk smoke test; cross-link the residual class in docs/linting.md.
- **Suggested revision**: Address the concern above.

### FINDING_18: risk-integration: scripts/lint-awk-multibyte-regex.sh:137-140
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Rule 2 requires whitespace around ~ and !~. $0~re with multibyte regex content would not be reported. Tighten regex_callsite() or add a regression fixture if that style exists in-tree.
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: scripts/test-ship-pr.sh:235-254
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Default write_stubs launchers always commit before LAUNCHER_EXIT=0. Future fix-loop tests reusing default stubs may never hit HEAD-non-advance detection except in explicit #3134 cases. Document in write_stubs; keep dedicated no-commit cases as the canonical pattern.
- **Suggested revision**: Address the concern above.

### FINDING_20: risk-integration: scripts/test-lint-awk-multibyte-regex.sh:103-108
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Clean fixture does not assert empty stderr. Lint could emit non-rule-id warnings and still pass the clean case. Assert stderr is empty or lacks the lint-awk-multibyte-regex: prefix.
- **Suggested revision**: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] risk-integration: scripts/test-ship-pr-fix-loop-2632.inc.sh:403-467
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] 2632 include has LAUNCHER_EXIT=0 vendors without HEAD advance but is not sourced from test-ship-pr.sh. Those scenarios are not exercised in make test-ship-pr-fix-loop CI after the new HEAD check. Re-source the include or update 2632 cases with sentinel/git-commit stubs (separate follow-up).
- **Suggested revision**: Address the concern above.

### FINDING_22: **Injection:** `lint-awk-multibyte-regex.sh` follows the same `awk -v rel="$rel"` and `path="$ROOT/$rel"` patterns as `lint-bare-grep-probe.sh`, `lint-bash32.sh`, and siblings; no new `eval`, unquoted command substitution, or user-controlled shell execution. Heredoc delimiters are restricted to `[A-Za-z_][A-Za-z0-9_]*` before use in awk matching.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Injection:** `lint-awk-multibyte-regex.sh` follows the same `awk -v rel="$rel"` and `path="$ROOT/$rel"` patterns as `lint-bare-grep-probe.sh`, `lint-bash32.sh`, and siblings; no new `eval`, unquoted command substitution, or user-controlled shell execution. Heredoc delimiters are restricted to `[A-Za-z_][A-Za-z0-9_]*` before use in awk matching.
- **Suggested revision**: Address the concern above.

### FINDING_23: **Path traversal:** Symlinks are skipped (`! -L`); `..` in `rel` is the same inherited enumeration model as other repo-wide lints—not introduced or widened beyond the existing lint family contract.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Path traversal:** Symlinks are skipped (`! -L`); `..` in `rel` is the same inherited enumeration model as other repo-wide lints—not introduced or widened beyond the existing lint family contract.
- **Suggested revision**: Address the concern above.

### FINDING_24: **Secrets:** No hard-coded credentials in new scripts; ship-pr detail logs only record SHAs and vendor tier; CI log redaction path is unchanged.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Secrets:** No hard-coded credentials in new scripts; ship-pr detail logs only record SHAs and vendor tier; CI log redaction path is unchanged.
- **Suggested revision**: Address the concern above.

### FINDING_25: **AuthZ / escalation:** `first-fixer-non-health` on vendor exit 0 with no effective HEAD advance is intentional workflow routing (Exit 3 → autonomous main-agent), only after verified CI failure and successful `_stage_and_push_ci_fixes`; `effective_head` is hex-validated before comparison. This does not grant new privileges to untrusted input—it replaces a silent retry stall.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **AuthZ / escalation:** `first-fixer-non-health` on vendor exit 0 with no effective HEAD advance is intentional workflow routing (Exit 3 → autonomous main-agent), only after verified CI failure and successful `_stage_and_push_ci_fixes`; `effective_head` is hex-validated before comparison. This does not grant new privileges to untrusted input—it replaces a silent retry stall.
- **Suggested revision**: Address the concern above.

### FINDING_26: **DoS:** Repo-wide lint is bounded to `*.sh`/`*.awk` with binary skip; same class as other `always_run` pre-commit hooks.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **DoS:** Repo-wide lint is bounded to `*.sh`/`*.awk` with binary skip; same class as other `always_run` pre-commit hooks.
- **Suggested revision**: Address the concern above.

### FINDING_27: correctness: scripts/lint-awk-multibyte-regex.sh:218-316
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Rule 2 body tracking covers only single-quoted awk and heredocs; double-quoted awk programs are unscanned. A future em-dash or CJK byte inside match()/gsub() in awk "..." (already used in launch-review.sh and launch-codex-implement.sh) would pass make lint and fail at runtime on mawk CI. Extend Rule 2 to double-quoted awk bodies or document the limitation and add a negative harness fixture.
- **Suggested revision**: Address the concern above.

### FINDING_28: architecture: scripts/ship-pr.sh:59,1758,1811,1928
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] HEAD-after-stage is returned via module-global _SAPCF_EFFECTIVE_HEAD instead of an explicit out-parameter. A future refactor calling _stage_and_push_ci_fixes twice or from a subshell could leave run_ci_fix_vendor comparing against a stale effective_head, misclassifying success as first-fixer-non-health or vice versa. Return effective HEAD via a named out-var or temp file written by _stage_and_push_ci_fixes.
- **Suggested revision**: Address the concern above.

### FINDING_29: correctness: scripts/lint-awk-multibyte-regex.sh:167-200,258-271
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Rule 1 scans all non-comment shell lines without heredoc context. A shell heredoc documenting awk -v label='テスト' triggers awk-v-nonascii even though the line is not executable awk code, blocking an unrelated PR. Track shell heredoc spans for Rule 1 or tighten matching to executable command contexts only.
- **Suggested revision**: Address the concern above.

### FINDING_30: correctness: scripts/lint-awk-multibyte-regex.sh:250-256,278-283
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] close_single_quoted_body closes the awk span on any line containing a single quote. Shell '"'"' quote assembly inside a multi-line awk invocation can end the Rule 2 span early, missing a non-ASCII regex on a later physical line (false negative). Improve quote-aware body tracking for single-quoted awk spans.
- **Suggested revision**: Address the concern above.

### FINDING_31: risk-integration: scripts/test-ship-pr.sh:235-257
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Default write_stubs launchers git-commit during invocation, diverging from production where only _stage_and_push_ci_fixes commits. Tests like ci_fix_vendor_retry accumulate launcher commits on verify-fail paths, weakening fidelity to the no-commit vendor stall this branch fixes. Make default launcher stubs touch the tree only; commit via git-commit.sh stub on success paths.
- **Suggested revision**: Address the concern above.

### FINDING_32: [OUT_OF_SCOPE] architecture: scripts/ship-pr.sh:2287-2290
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Per-job local fix success path lacks HEAD-non-advance detection added to run_ci_fix_vendor. Per-job fix can exit 0 through _stage_and_push with unchanged Fix-CI HEAD and still loop to max-retries instead of exit 3. Mirror the effective_head gate in the per-job _stage_and_push success branch (follow-up issue).
- **Suggested revision**: Address the concern above.

### FINDING_33: [OUT_OF_SCOPE] architecture: scripts/ship-pr.sh:1942-1943
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] BAIL_REASON first-fixer-non-health is set when any winning tier produces no Fix-CI commit. Operators reading state may assume Cursor-only failure when Codex/Claude no-op triggered the bail. Rename reason or split tier-specific bail keys (cosmetic; pre-existing naming).
- **Suggested revision**: Address the concern above.

### FINDING_34: correctness: scripts/ship-pr.sh:1754-1811
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] _stage_and_push_ci_fixes was modified despite plan "No change to _stage_and_push_ci_fixes" Plan reviewers and downstream callers assume the helper is untouched; the global _SAPCF_EFFECTIVE_HEAD side channel is undeclared in the plan Document the hook in the plan/acceptance or refactor to compare HEAD only in run_ci_fix_vendor after the helper returns
- **Suggested revision**: Address the concern above.

### FINDING_35: correctness: scripts/ship-pr.sh:1927-1945
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] HEAD equality uses effective_head not plan-specified final_head Vendor exit 0 with no fix plus refresh-run-logs-only commit: plan would continue; implementation sets first-fixer-non-health Match plan (baseline vs final_head after _stage_and_push) or update plan/acceptance to codify effective_head semantics
- **Suggested revision**: Address the concern above.

### FINDING_36: correctness: scripts/lint-awk-multibyte-regex.md:15
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Binary heuristic omits plan's first-4KB file sampling note Doc vs implementation mismatch for operators debugging false negatives/positives Align doc or add 4KB-capped file probe per plan
- **Suggested revision**: Address the concern above.

### FINDING_37: architecture: CHANGELOG.md:67-68
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Changelog bullet under ### Fixed only Release notes may under-report the new lint as an addition Split Added/Fixed bullets or note deviation in PR text
- **Suggested revision**: Address the concern above.

