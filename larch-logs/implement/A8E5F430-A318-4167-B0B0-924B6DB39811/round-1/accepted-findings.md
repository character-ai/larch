### FINDING_1: Non-regular breadcrumb matches can trigger empty atomic swap
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-staging-atomicity-output.txt
- **Severity**: important
- **Concern**: `scripts/lib-larch-log.sh` marks `found_any=true` after `stage_file` returns success, but `stage_file` can return success for skipped non-regular or vanished paths. A directory, fifo, or other non-regular entry named like `*.ndjson` or `larch-quiet-*-*.log` can therefore cause an empty staging directory to be atomically swapped over an existing committed `breadcrumbs/` tree, deleting prior forensics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-staging-atomicity-output.txt: Address the concern above.


### FINDING_11: Step 5c failure-log instruction names inconsistent stderr path
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `skills/design/SKILL.md` Step 5c item 9 says to capture stderr to `design-log-publish.failure.log`, but the fenced command redirects stderr to `design-log-publish.stderr`, weakening operator recovery when `PUBLISH_OK=false`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_14: Breadcrumb silent-skip docs omit quiet-log basename rules
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `docs/run-logs.md` still documents only ndjson sibling silent-skip behavior after quiet-log additions, so operators may miss root quiet-log basename filtering rules.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_15: Design publish snippets have stray quote causing Bash syntax error
- **Reviewer(s)**: dyn-exit-boundary-output.txt
- **Severity**: important
- **Concern**: Both new `design-log-publish.sh` invocations in `skills/design/SKILL.md` include a stray `"` after `${REPO:+--repo "$REPO"}`, leaving an unclosed double quote and making the one-liners fail at Bash parse time before `design-log-publish.sh` can run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-exit-boundary-output.txt: Address the concern above.


### FINDING_22: Unplanned global DESIGN_TMPDIR export broadens environment exposure
- **Reviewer(s)**: dyn-unplanned-export-output.txt
- **Severity**: latent
- **Concern**: `scripts/design-log-publish.sh` exports `DESIGN_TMPDIR` globally even though breadcrumb staging uses it in-process and child redactors do not need it. The export leaks the live design session path into descendant `git`/`gh`/hook environments and may let helpers treat unrelated paths as session-bound.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-unplanned-export-output.txt: Address the concern above.


### FINDING_3: Dead no-breadcrumbs quiet-log test assignment
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-larch-log.sh` contains an erroneous `_bc_no_bc_quiet` assignment that is immediately overwritten by the correct path, creating misleading test maintenance noise without runtime effect.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_7: Missing symlink rejection coverage for root quiet logs
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-larch-log.sh` lacks a symlink rejection case for session-root quiet logs, so a symlink quiet-log regression would not be caught by the harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


