### FINDING_1: **Important** `risk-integration` [skills/review/scripts/test-dispatch-panel.sh:192](<OPERATOR_REPO_PATH>/skills/review/scripts/test-dispatch-panel.sh:192): The new harness-path guard suppresses `append_scout_parse_issue` for any `REVIEW_TMPDIR` under `test-dispatch-panel.*`, but the existing core parse-failed test still expects the explicit `$issues_log` to be written. Concrete failing scenario: `make test-dispatch-panel-core` creates `TMP=$(mktemp -d .../test-dispatch-panel.XXXXXX)`, runs the parse-failed case with `--review-tmpdir "$TMP/dynamic-parse-failed"`, `dispatch-panel.sh:298` returns before appending, then `grep -Fq ... "$issues_log"` fails because the log was intentionally not written. Update this case to assert the new suppressed-harness behavior and local diag sidecar, or move any production append assertion to a temp root outside `test-dispatch-panel.*`; do the same for the append-failure/WARN assertion at `skills/review/scripts/test-dispatch-panel.sh:199-209`.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `risk-integration` [skills/review/scripts/test-dispatch-panel.sh:192](<OPERATOR_REPO_PATH>/skills/review/scripts/test-dispatch-panel.sh:192): The new harness-path guard suppresses `append_scout_parse_issue` for any `REVIEW_TMPDIR` under `test-dispatch-panel.*`, but the existing core parse-failed test still expects the explicit `$issues_log` to be written. Concrete failing scenario: `make test-dispatch-panel-core` creates `TMP=$(mktemp -d .../test-dispatch-panel.XXXXXX)`, runs the parse-failed case with `--review-tmpdir "$TMP/dynamic-parse-failed"`, `dispatch-panel.sh:298` returns before appending, then `grep -Fq ... "$issues_log"` fails because the log was intentionally not written. Update this case to assert the new suppressed-harness behavior and local diag sidecar, or move any production append assertion to a temp root outside `test-dispatch-panel.*`; do the same for the append-failure/WARN assertion at `skills/review/scripts/test-dispatch-panel.sh:199-209`.
- **Suggested revision**: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] **code-quality** (optional hardening, not a functional bug under current Bash) `skills/review/scripts/test-dispatch-panel.sh:261-281`, `skills/review/scripts/test-dispatch-panel.sh:330-353`, `skills/review/scripts/test-dispatch-panel.sh:543-566` — Adding an explicit `) || exit 1` after each parenthesized block would document intent for maintainers who might later add `set +e` inside the group; current behavior already relies on inherited `set -e` for propagation.
- **Reviewer**: dyn-bash-subshell-propagation-output.txt
- **Concern**: - **code-quality** (optional hardening, not a functional bug under current Bash) `skills/review/scripts/test-dispatch-panel.sh:261-281`, `skills/review/scripts/test-dispatch-panel.sh:330-353`, `skills/review/scripts/test-dispatch-panel.sh:543-566` — Adding an explicit `) || exit 1` after each parenthesized block would document intent for maintainers who might later add `set +e` inside the group; current behavior already relies on inherited `set -e` for propagation.
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] **correctness** `skills/review/scripts/test-dispatch-panel.sh:345-348` — The `if grep -q '"prompt_file"' ...` pattern treats `grep` exit status only as true/false; a `grep` I/O error (exit 2) would follow the “no match” branch rather than failing the harness. This structure already existed before the subshell move and was not introduced by this diff.
- **Reviewer**: dyn-bash-subshell-propagation-output.txt
- **Concern**: - **correctness** `skills/review/scripts/test-dispatch-panel.sh:345-348` — The `if grep -q '"prompt_file"' ...` pattern treats `grep` exit status only as true/false; a `grep` I/O error (exit 2) would follow the “no match” branch rather than failing the harness. This structure already existed before the subshell move and was not introduced by this diff.
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] risk-integration: skills/review/scripts/dispatch-panel.sh:301
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Missing/non-executable append-execution-issue.sh yields silent return. Pre-existing; not introduced by this diff. No change required for this PR scope.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] risk-integration: skills/review/scripts/test-dispatch-panel.md:18
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Doc references make test-dispatch-panel while Makefile lists split targets. Operators may run a non-existent aggregate target. Update docs/Makefile in a doc-focused change; not introduced by this diff.
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] security: skills/review/scripts/dispatch-panel.sh:303-306 (unchanged interpolation)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] --entry still embeds reason and manifest_label from scout-derived state. If those values ever contained hostile content, risk would be in append-execution-issue consumer; not introduced by this branch. None for this PR; consider central escaping/validation separately.
- **Suggested revision**: Address the concern above.

### FINDING_7: code-quality: plan: Part B vs skills/review/scripts/test-dispatch-panel.sh:332-385
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Plan promised three distinct regressions; two are structurally overlapping (code-quality / plan). Slightly inflated test surface for one guard clause. Consolidate or differentiate scenarios per finding 1.
- **Suggested revision**: Address the concern above.

### FINDING_8: code-quality: skills/review/scripts/dispatch-panel.md:18-19
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Doc says harness ancestor; code matches path substrings/globs. Misleading operational contract for integrators. Align wording with glob semantics or tighten implementation to ancestor checks.
- **Suggested revision**: Address the concern above.

### FINDING_9: code-quality: skills/review/scripts/dispatch-panel.sh:279-289
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Parameter manifest_path vs passed SCOUT_MANIFEST value naming (manifest_label) obscures intent. Readers may misread which path the second OR branch is guarding. Rename parameter or caller variable for consistency.
- **Suggested revision**: Address the concern above.

### FINDING_10: code-quality: skills/review/scripts/dispatch-panel.sh:284-299
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] append_scout_parse_issue resolves execution-issues log before the harness suppress return. Suppressed harness runs still invoke resolve_execution_issues_log even though issues_log is unused. Move issues_log resolution after the suppress check or only when invoking append-execution-issue.sh.
- **Suggested revision**: Address the concern above.

### FINDING_11: code-quality: skills/review/scripts/test-dispatch-panel.sh:332-385
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Regression env-isolation and path-guard largely duplicate the same harness-tmpdir plus parent LARCH_EXECUTION_ISSUES_LOG setup; only the second adds a diag grep. Maintainers may update one test and miss the other, or spend time reasoning about two names for one behavior. Merge into one test with the stronger assertions or give regression 2 a distinct invariant (different code path or inputs).
- **Suggested revision**: Address the concern above.

### FINDING_12: correctness: skills/review/scripts/dispatch-panel.sh:267-281
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Path-only harness detection uses broad globs (test-dispatch-panel.*, test-review-core.*, test-scout-*) on REVIEW_TMPDIR and SCOUT_MANIFEST. If TMPDIR or another ancestor directory is named like test-scout-foo, a production REVIEW_TMPDIR can match and scout parse-failed warnings are suppressed from execution-issues.md; test-dispatch-panel.sh prod-shape regression can fail when TMPDIR matches the glob. Prefer an explicit env flag from harnesses, narrow patterns to known tmp prefixes, or avoid TMPDIR-relative prod-shape paths without documenting constraints.
- **Suggested revision**: Address the concern above.

### FINDING_13: correctness: skills/review/scripts/dispatch-panel.sh:279-282
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Suppression OR-tests SCOUT_MANIFEST path against harness globs; SCOUT_MANIFEST can be set from scout SCOUT_OUTPUT stdout, not only the round file under REVIEW_TMPDIR. A parse-failed round with production REVIEW_TMPDIR but SCOUT_MANIFEST path containing /test-scout-... (or other matched segment) never appends the Warnings entry to the real execution-issues log. Suppress only when REVIEW_TMPDIR matches harness (or require manifest path prefix REVIEW_TMPDIR before applying harness glob).
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: skills/review/scripts/dispatch-panel.sh:265-275;skills/review/scripts/test-dispatch-panel.sh:486-566
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Three harness path prefixes are implemented but only test-dispatch-panel tmp layout is exercised in CI. Typo or regression in */test-review-core.* or */test-scout-* arms suppresses or leaks without failing tests. Add minimal cases with mktemp dirs matching test-review-core.* and test-scout-* prefixes (same as those harnesses).
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: skills/review/scripts/dispatch-panel.sh:267-271
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Broad path substring globs (e.g. */test-scout-*) can match legitimate project directories. Accidental suppression of execution-issues warnings if real paths include test-scout-* segments. Narrow patterns or use explicit opt-in from harness.
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: skills/review/scripts/dispatch-panel.sh:267-276;skills/review/scripts/dispatch-panel.sh:49
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Harness glob requires a slash before test-dispatch-panel.*; REVIEW_TMPDIR is not normalized to absolute. Relative --review-tmpdir like test-dispatch-panel.abc/review fails the guard; parse-failed can still append to a parent LARCH_EXECUTION_ISSUES_LOG. Normalize REVIEW_TMPDIR to an absolute path before is_harness_scout_path, or document absolute-path requirement.
- **Suggested revision**: Address the concern above.

### FINDING_17: risk-integration: skills/review/scripts/dispatch-panel.sh:267-281
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Suppression uses path-component globs including test-scout-* on REVIEW_TMPDIR or SCOUT_MANIFEST. A production REVIEW_TMPDIR that includes a matching segment (e.g. test-scout-artifacts) drops the execution-issues warning; a future harness using a different mktemp basename than test-dispatch-panel. / test-review-core. may not match and can leak again. Document naming contract; add explicit opt-out env; or gate on harness-set flag instead of path substrings.
- **Suggested revision**: Address the concern above.

### FINDING_18: risk-integration: skills/review/scripts/dispatch-panel.sh:291-296
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Diag file write uses || true; failures are silent. Disk full: no diag sidecar and (if not suppressed) still possible silent skip of useful telemetry. On diag write failure emit WARN= or avoid swallowing the error entirely.
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: skills/review/scripts/test-dispatch-panel.sh:486-539
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Regression 1 and 2 largely duplicate the same parse-failed scenario. Maintenance noise if one assertion changes but not the other. Merge into one test with combined assertions.
- **Suggested revision**: Address the concern above.

### FINDING_20: risk-integration: skills/review/scripts/test-dispatch-panel.sh:486-566;Makefile:490-497
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] New scout-parse regressions are unconditional so each sharded harness target runs them once. Redundant CI time (same three tests on core, reuse, limits shards) without additional branch coverage. Shard into one Makefile target/section or accept and document intentional triple smoke.
- **Suggested revision**: Address the concern above.

### FINDING_21: security: skills/review/scripts/dispatch-panel.sh:279-300
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] OR-ing is_harness_scout_path(REVIEW_TMPDIR) with is_harness_scout_path(SCOUT_MANIFEST) lets a manifest path alone suppress append_scout_parse_issue. SCOUT_MANIFEST can be stale or attacker-influenced via round status sidecar; a path containing /test-scout-* (or other globs) triggers parse-failed append suppression even when REVIEW_TMPDIR is a normal prod-shape dir, so LARCH_EXECUTION_ISSUES_LOG may miss scout parse-failed warnings. Suppress only on REVIEW_TMPDIR and/or explicit harness env; do not treat SCOUT_MANIFEST as a harness signal.
- **Suggested revision**: Address the concern above.

