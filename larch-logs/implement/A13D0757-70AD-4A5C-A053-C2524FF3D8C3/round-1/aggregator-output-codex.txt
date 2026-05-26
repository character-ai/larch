### FINDING_1: Missing breadcrumb no-op/preserve-existing contract
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Breadcrumb docs no longer clearly state that missing, empty, or zero-accepted-ndjson sources are a successful no-op and do not create, replace, or clear an existing committed `breadcrumbs/` destination. Operators could misread stale committed breadcrumbs as newly published or assume publication failed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_2: Failed breadcrumb publish preserves prior committed destination
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Security docs say failed publish has “no partial publication” and does not create or replace the destination, but do not explicitly say any previously committed `breadcrumbs/` tree remains unchanged after an enforced failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: Rejected-trigger list omits non-directory source paths
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `SECURITY.md` does not list the implemented rejection case where `source_dir` exists but is not a directory, so readers auditing fail-closed behavior miss that trigger.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_4: Docs imply review/research committed breadcrumbs are currently wired
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Run-log docs imply `review/` and `research/` committed `breadcrumbs/` paths are routine/currently published, but the reviewers report only implement commit and design publish paths call the helper today. Operators may expect committed review/research breadcrumb trees that are not wired.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_5: Branch mixes docs-only breadcrumb work with unrelated lint-fix-loop changes
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The branch combines the breadcrumb documentation patch with unrelated #2909 lint-fix-loop behavior, docs, version bump, and run-log flush changes. This violates the reported “No code changes” plan constraint and can block or confuse review/merge of the docs-only work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_6: Missing tests for documented symlink/hardlink rejects
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Security docs now promise source-directory symlink and hardlink rejection behavior, but reviewers report `test-larch-log.sh` lacks cases covering those rejects.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_7: Cross-document breadcrumb anchors lack regression coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Cross-doc links such as `#breadcrumb-stream-redaction` and `#breadcrumbs` can break if headings are renamed, with no automated check reported.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_8: docs/linting.md diff is broader than necessary
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The harness table block in `docs/linting.md` was reportedly rewritten when only one row needed to change, increasing merge-conflict risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] Branch includes unrelated lint-fix-loop and run-log flush commits
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Source reviewer marked unrelated lint-fix-loop and `larch-logs` flush commits as out of scope for the breadcrumb documentation review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] Missing design-log-publish cross-link to breadcrumb docs
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/design-log-publish.md` does not point to the consolidated breadcrumb contract, so future design-publisher readers may miss the canonical docs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] Early SECURITY summary lacks cross-link to canonical breadcrumb contract
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: The early `SECURITY.md` breadcrumb summary under “Security Findings in OOS Workflows” is not cross-linked to the later canonical `Breadcrumb stream redaction` section.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] Branch expands external-tool trust boundary via lint-fix-loop changes
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: The branch includes #2909 coder-owned commit acceptance for external CI fixers, expanding the external-tool trust boundary by design; the reviewer marked this as outside breadcrumb-doc scope rather than a breadcrumb documentation defect.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] Committed larch-logs flush trees not evaluated as scope drift
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: The reviewer explicitly treated committed `larch-logs/implement/` trees from chore flush commits as intentional and outside the evaluated scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] Design publish handles breadcrumb helper failure differently from commit
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `design-log-publish` reportedly records breadcrumb helper failure as `PUBLISH_OK=false` with exit 0, unlike commit’s hard abort, which may allow design publish to proceed with partial logs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] Monitor output may expose session tmpdir paths
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `breadcrumb-monitor.sh` reportedly does not run `redact-tmpdir-paths` before streaming redaction, so session tmpdir paths may appear in foreground monitor output even though committed copies redact paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
