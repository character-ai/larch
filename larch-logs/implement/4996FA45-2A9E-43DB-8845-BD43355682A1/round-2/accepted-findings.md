### FINDING_4: Documentation vs implementation on single `*` vs multiple `*`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Docs describe a single `*` segment semantics, but allowlist handling permits multiple `*` characters, so a malformed manifest row could trigger broader glob expansion than operators expect from the documentation.
- **Suggested revision**: Tighten validation to the documented single-`*` shape, or update the documentation to explicitly allow and define multi-`*` paths.


### FINDING_6: Relative `LARCH_VERIFY_MANIFEST` can resolve outside `REPO_ROOT` via `..`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: A repo-root-relative `LARCH_VERIFY_MANIFEST` is joined under `REPO_ROOT` without forbidding `..` in the relative tail, so the manifest path can resolve outside the repository; verification then enforces the wrong manifest with false OK or false MISSING relative to the intended `docs/run-logs-required-files.tsv`, weakening the integrity boundary of what defines required artifacts.
- **Suggested revision**: Reject `..` in the relative tail, normalize/collapse the path, or canonicalize and assert the resolved path stays under `REPO_ROOT`; document and add a test for a `../` escape attempt.


### FINDING_7: Test 14 does not assert non-zero exit for bad manifest
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Test 14 checks for the invalid-characters message while using `|| true`, so exit status is not verified—a future regression could print the expected substring yet exit 0, contradicting intended failure semantics.
- **Suggested revision**: Rerun the bad-manifest invocation without `|| true`, or capture output and assert non-zero `$?` explicitly.


