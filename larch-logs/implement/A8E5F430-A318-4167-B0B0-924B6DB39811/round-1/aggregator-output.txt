### FINDING_1: Non-regular breadcrumb matches can trigger empty atomic swap
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-staging-atomicity-output.txt
- **Severity**: important
- **Concern**: `scripts/lib-larch-log.sh` marks `found_any=true` after `stage_file` returns success, but `stage_file` can return success for skipped non-regular or vanished paths. A directory, fifo, or other non-regular entry named like `*.ndjson` or `larch-quiet-*-*.log` can therefore cause an empty staging directory to be atomically swapped over an existing committed `breadcrumbs/` tree, deleting prior forensics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-staging-atomicity-output.txt: Address the concern above.

### FINDING_2: Redundant quiet-log basename filtering branch
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/lib-larch-log.sh` has an extra quiet-log basename `case` branch after the glob has already filtered quiet-log basenames, adding maintenance noise in the dual-loop publish path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: Dead no-breadcrumbs quiet-log test assignment
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-larch-log.sh` contains an erroneous `_bc_no_bc_quiet` assignment that is immediately overwritten by the correct path, creating misleading test maintenance noise without runtime effect.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_4: Duplicated publish recipe in design skill
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `skills/design/SKILL.md` duplicates the long `set +e` publish recipe at two callsites, risking divergent edits if the contract changes again.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] Breadcrumb-monitor documentation remains after deprecation
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `SECURITY.md` still documents live `breadcrumb-monitor` behavior while the feature deprecates, so operators may assume monitor streaming is still the committed-path source of truth.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] PR-create recovery test does not assert exit code
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-design-log-publish.sh` still uses `|| true` in a PR-create recovery-success test, so it can pass based on stdout even if publish exits nonzero.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_7: Missing symlink rejection coverage for root quiet logs
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-larch-log.sh` lacks a symlink rejection case for session-root quiet logs, so a symlink quiet-log regression would not be caught by the harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] Other soft-failure tests still mask exit codes
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Other pre-existing soft-failure cases in `scripts/test-design-log-publish.sh` still use `|| true`, leaving inconsistent exit-code assertions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_9: Quiet-log publication expands sensitive-output exposure
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Publishing quiet logs commits full script stdout/stderr with pattern-only redaction, increasing exposure risk for env vars, tokens outside known patterns, or PII compared with ndjson-only breadcrumbs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] Design artifact symlinks are silently skipped
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `scripts/design-log-publish.sh` silently skips symlinked top-level design artifacts while breadcrumb publication rejects symlinks, creating inconsistent handling if parity is desired.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_11: Step 5c failure-log instruction names inconsistent stderr path
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `skills/design/SKILL.md` Step 5c item 9 says to capture stderr to `design-log-publish.failure.log`, but the fenced command redirects stderr to `design-log-publish.stderr`, weakening operator recovery when `PUBLISH_OK=false`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] Merge-failure path removes staged worktree before recovery
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: After `gh pr merge` fails, `scripts/design-log-publish.sh` removes the worktree before emitting recovery stdout, making local inspection of the staged design log tree impossible and leaving recovery remote-branch oriented only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] Implement teardown swallows breadcrumb commit failures
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `scripts/implement-finalize.sh` teardown only warns on `larch-log.sh commit` failures, so quiet-log, hardlink, or redaction errors may leave no committed breadcrumbs without failing finalize.
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

### FINDING_16: [OUT_OF_SCOPE] Pause-save already handles new publish exit contract
- **Reviewer(s)**: dyn-exit-boundary-output.txt
- **Severity**: nit
- **Concern**: `scripts/design-pause-save.sh` already wraps `design-log-publish.sh` with `set +e`, captures exit code, and parses `PUBLISH_OK` from a file, so no change is needed there for the post-push `exit 1` contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-exit-boundary-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] Design-log publish hard-fail paths match plan
- **Reviewer(s)**: dyn-exit-boundary-output.txt
- **Severity**: nit
- **Concern**: `scripts/design-log-publish.sh` hard-fail paths for `git push`, post-push `gh pr create`, and `gh pr merge` emit `PUBLISH_OK=false` and exit 1, while pre-push failures remain exit 0 as planned.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-exit-boundary-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] Only design skill prose one-liners call publish incorrectly
- **Reviewer(s)**: dyn-exit-boundary-output.txt
- **Severity**: nit
- **Concern**: No other in-diff Bash caller invokes `design-log-publish.sh` without the `set +e` pattern; only the two `skills/design/SKILL.md` prose one-liners are affected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-exit-boundary-output.txt: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] No harness syntax-checks inline shell in SKILL.md
- **Reviewer(s)**: dyn-exit-boundary-output.txt
- **Severity**: nit
- **Concern**: There is no existing harness that syntax-checks inline shell in `SKILL.md`; `scripts/test-design-structure.sh` only checks ordering mentions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-exit-boundary-output.txt: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] Existing empty-source breadcrumb test misses non-regular match
- **Reviewer(s)**: dyn-staging-atomicity-output.txt
- **Severity**: nit
- **Concern**: Existing `scripts/test-larch-log.sh` empty breadcrumb source coverage removes `*.ndjson` files rather than leaving a non-regular `*.ndjson` path, so it would not catch the false-positive `found_any` empty-swap regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-staging-atomicity-output.txt: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] Missing-source breadcrumb test does not exercise false-positive found_any
- **Reviewer(s)**: dyn-staging-atomicity-output.txt
- **Severity**: nit
- **Concern**: The missing breadcrumb source test still passes because no `breadcrumbs/` directory and no quiet logs leave `found_any=false`, so it does not exercise the false-positive `found_any` path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-staging-atomicity-output.txt: Address the concern above.

### FINDING_22: Unplanned global DESIGN_TMPDIR export broadens environment exposure
- **Reviewer(s)**: dyn-unplanned-export-output.txt
- **Severity**: latent
- **Concern**: `scripts/design-log-publish.sh` exports `DESIGN_TMPDIR` globally even though breadcrumb staging uses it in-process and child redactors do not need it. The export leaks the live design session path into descendant `git`/`gh`/hook environments and may let helpers treat unrelated paths as session-bound.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-unplanned-export-output.txt: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] Other session tmpdir exports are intentional child contracts
- **Reviewer(s)**: dyn-unplanned-export-output.txt
- **Severity**: nit
- **Concern**: Existing exports in `scripts/dispatch-plan-voters.sh` and `scripts/implement-finalize.sh` are intentional because spawned children need those session tmpdir variables, but that does not justify the new `design-log-publish.sh` export.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-unplanned-export-output.txt: Address the concern above.

### FINDING_24: [OUT_OF_SCOPE] Branch commit metadata observed
- **Reviewer(s)**: dyn-unplanned-export-output.txt
- **Severity**: nit
- **Concern**: Reviewer noted branch commits `8fb43bde` and `fb92441f`; this is branch metadata, not a code behavior requiring a fix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-unplanned-export-output.txt: Address the concern above.
