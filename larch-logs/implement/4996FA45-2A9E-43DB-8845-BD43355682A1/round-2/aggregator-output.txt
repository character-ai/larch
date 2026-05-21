Here is the normalized structured finding list (merged by behavioral risk; stable IDs in first-seen cluster order).

```text
### FINDING_1: Test 15 harness hides failures and over-accepts “OK”
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, dyn-test-assertion-quality-output.txt
- **Concern**: Test 15 wraps capture in a no-op if/else, so a non-zero verifier exit is never turned into a harness failure; success is inferred only from a substring match on `OK`, which can theoretically match incidental text without proving exit 0 or correct `LARCH_VERIFY_MANIFEST` resolution.
- **Suggested revision**: After capture, assert exit status 0 explicitly (fail on non-zero with `out` visible); replace the no-op if/else with a single assignment or meaningful branching; tighten the assertion (e.g. full-line `OK` via `grep -qx` on `out`) if substring matching is too loose.

### FINDING_2: Test numbering vs execution order (Test 15 between Test 1 and Test 2)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Comments/labels use “Test 15” immediately after “Test 1” and before later low-numbered tests, so numbers are non-monotonic relative to execution order and plan references—harder navigation, misleading grep-by-number maintenance, and higher risk of duplicate/missed cases when extending the harness.
- **Suggested revision**: Renumber or physically reorder blocks so labels follow chronological execution, or switch to descriptive test labels instead of numeric-only markers.

### FINDING_3: Inconsistent `LC_ALL=C` between allowlist grep and `*` probe
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt
- **Concern**: One path pins `LC_ALL=C` while the adjacent glob-vs-literal `*` probe uses plain `grep`; unusual locales could theoretically change how a row is classified as glob vs literal file path.
- **Suggested revision**: Add `LC_ALL=C` to the second `grep` or use a pure Bash test such as `[[ ... == *'*'* ]]` for asterisk detection.

### FINDING_4: Documentation vs implementation on single `*` vs multiple `*`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Docs describe a single `*` segment semantics, but allowlist handling permits multiple `*` characters, so a malformed manifest row could trigger broader glob expansion than operators expect from the documentation.
- **Suggested revision**: Tighten validation to the documented single-`*` shape, or update the documentation to explicitly allow and define multi-`*` paths.

### FINDING_5: [OUT_OF_SCOPE] execution-issues greps lack `LC_ALL=C`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: execution-issues probes use `grep` without `LC_ALL=C`; unchanged by the new allowlist work—possible locale edge cases if pursuing repo-wide `grep` locale hygiene.
- **Suggested revision**: Track separately as optional repo-wide hygiene if desired.

### FINDING_6: Relative `LARCH_VERIFY_MANIFEST` can resolve outside `REPO_ROOT` via `..`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: A repo-root-relative `LARCH_VERIFY_MANIFEST` is joined under `REPO_ROOT` without forbidding `..` in the relative tail, so the manifest path can resolve outside the repository; verification then enforces the wrong manifest with false OK or false MISSING relative to the intended `docs/run-logs-required-files.tsv`, weakening the integrity boundary of what defines required artifacts.
- **Suggested revision**: Reject `..` in the relative tail, normalize/collapse the path, or canonicalize and assert the resolved path stays under `REPO_ROOT`; document and add a test for a `../` escape attempt.

### FINDING_7: Test 14 does not assert non-zero exit for bad manifest
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Test 14 checks for the invalid-characters message while using `|| true`, so exit status is not verified—a future regression could print the expected substring yet exit 0, contradicting intended failure semantics.
- **Suggested revision**: Rerun the bad-manifest invocation without `|| true`, or capture output and assert non-zero `$?` explicitly.

### FINDING_8: [OUT_OF_SCOPE] Harness-wide `|| true` plus substring-only assertions
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-test-assertion-quality-output.txt
- **Concern**: Multiple tests (including Test 1 and Test 15’s broader context) already use `|| true` with substring-only checks—weaker regression signal on success vs failure is pre-existing across the harness, not introduced solely by newer tests; branch history spans hardening, run-log flush, review, and relevant-checks commits.
- **Suggested revision**: Optional follow-up—add exit-code assertions consistently across the harness if tightening signal, not only on individual new tests.

### FINDING_9: [OUT_OF_SCOPE] `RUN_DIR` argv not normalized to a fixed root prefix
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: `RUN_DIR` is accepted from argv without normalizing to a fixed root prefix—pre-existing; could interact oddly with `..` or symlinks for run-dir checks independent of this branch’s manifest-path work.
- **Suggested revision**: Consider `realpath` and a prefix check if hardening the CLI surface becomes a goal.

### FINDING_10: [OUT_OF_SCOPE] `manifest_field` swallows JSON errors
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: `manifest_field` can swallow JSON errors and exit 0, yielding empty `MANIFEST_STATUS` / `MANIFEST_PR_NUMBER`; malformed `manifest.json` could silence later-phase requirements and yield false OK for partial trees—not introduced by this diff.
- **Suggested revision**: Treat as separate hardening if desired.

### FINDING_11: `/implement` run-log slice bundled with verifier change widens shipped surface
- **Reviewer(s)**: dyn-test-assertion-quality-output.txt
- **Concern**: The branch diff adds a full `/implement` run tree slice under `larch-logs/implement/4996FA45-2A9E-43DB-8845-BD43355682A1` (e.g. `manifest.json`, `parent-issue.md`, plan artifacts, tally) alongside verifier hardening—couples unrelated operational metadata to security-hardening unless the flush is intentional and separately motivated.
- **Suggested revision**: If the PR goal is only manifest-path validation, drop or relocate those run-log files per repo run-log policy; if intentional, isolate in its own commit/PR with a clear rationale for independent review gating.

### FINDING_12: [OUT_OF_SCOPE] Pre-existing weak assertion pattern beyond Test 15
- **Reviewer(s)**: dyn-test-assertion-quality-output.txt
- **Concern**: Same theme as FINDING_8: Test 1 and several later tests already follow substring-only success checks with `|| true`; tightening should ideally be consistent rather than only on Test 15; input also references commits on branch since merge-base with `main`.
- **Suggested revision**: If improving harness strictness, apply exit assertions consistently and keep commit/PR scope boundaries explicit for reviewers.
```
