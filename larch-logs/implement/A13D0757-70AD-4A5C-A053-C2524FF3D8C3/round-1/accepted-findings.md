### FINDING_1: Missing breadcrumb no-op/preserve-existing contract
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Breadcrumb docs no longer clearly state that missing, empty, or zero-accepted-ndjson sources are a successful no-op and do not create, replace, or clear an existing committed `breadcrumbs/` destination. Operators could misread stale committed breadcrumbs as newly published or assume publication failed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


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


