### FINDING_1: [OUT_OF_SCOPE] Link helper placement in tracking-issue module
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `link_pr_closes` PR-body formatting lives in `python/tracking_issue.py`; reviewer marked this as a pre-existing/accepted placement choice rather than a diff-worsened defect.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] Bash and Python still have separate Closes composers
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash-state-output.txt, dyn-contract-sync-output.txt
- **Severity**: latent
- **Concern**: Live bash still composes `Closes #N` inline while the dev Python tree centralizes on `tracking_issue.link_pr_closes`; reviewers describe drift/parity risk deferred until Phase 7.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-bash-state-output.txt: Address the concern above.
  - From dyn-contract-sync-output.txt: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] Pre-existing weak append test
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: An older `test_link_pr_closes_appends` only checks substring presence, not footer layout or occurrence count; reviewer marked it out of scope because newer tests cover harder cases and the test was not weakened.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] Extractor reads first Closes mention anywhere in body
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-python-closes-output.txt
- **Severity**: latent
- **Concern**: `scripts/extract-closes-issue-from-pr.sh` greps the first `Closes #N` anywhere, which can disagree with Python’s intended footer semantics when prose, Mermaid, or earlier mentions contain a different issue number.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-python-closes-output.txt: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] Plan/acceptance text still says digit-boundary guard
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-state-output.txt, dyn-final-report-flow-output.txt, dyn-python-closes-output.txt, dyn-contract-sync-output.txt
- **Severity**: important
- **Concern**: Plan/acceptance text describes a `(?!\d)` digit-boundary substring guard, while implementation/tests use footer-line idempotency. Reviewers disagree on whether this is merely out-of-scope drift or an acceptance failure, but the normalized risk is split authority for Phase 7 reviewers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-bash-state-output.txt: Address the concern above.
  - From dyn-final-report-flow-output.txt: Address the concern above.
  - From dyn-python-closes-output.txt: Address the concern above.
  - From dyn-contract-sync-output.txt: Address the concern above.

### FINDING_6: Exact footer regex misses common existing Closes variants
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `link_pr_closes` only treats an exact column-0 `Closes #N` line with spaces/tabs as idempotent. Existing lines with leading indentation, trailing commentary, punctuation, or CRLF can get a duplicate footer.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] Branch scope exceeds python-only plan
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-state-output.txt, dyn-final-report-flow-output.txt, dyn-python-closes-output.txt, dyn-contract-sync-output.txt
- **Severity**: important
- **Concern**: The plan/acceptance expected `python/`-only changes, but the branch also contains implement-skill, Makefile, docs, version, log, stall-recovery, and Step 18b changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-bash-state-output.txt: Address the concern above.
  - From dyn-final-report-flow-output.txt: Address the concern above.
  - From dyn-python-closes-output.txt: Address the concern above.
  - From dyn-contract-sync-output.txt: Address the concern above.

### FINDING_8: Missing shorter-prefix masking regression test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Tests do not explicitly cover `issue_number=4` when the body already contains `Closes #42`, so a future substring-style guard could skip appending the intended `Closes #4`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_9: Ensure-pr path lacks Closes-specific unit coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `ensure_pr` create/update behavior has no direct tests asserting that the linked body is passed through `gh.pr_create` or `update_pr_body`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_10: Compose PR body test does not assert footer placement
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The `compose_pr_body` Closes test checks substring count but not that the canonical `Closes #42` line is the trailing footer.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: Fenced or non-footer exact Closes line can suppress real footer
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-python-closes-output.txt
- **Severity**: latent
- **Concern**: Because the idempotency check scans the whole body for an exact `Closes #N` line, an example inside a fenced block or other non-footer context can prevent appending the real trailing footer.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-python-closes-output.txt: Address the concern above.

### FINDING_12: Compose-body delegation remains a fragile regression point
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-contract-sync-output.txt
- **Severity**: latent
- **Concern**: Round 1 briefly reintroduced inline `Closes #N` composition before Round 2 restored delegation and tests. Reviewers flag the routing test as important to avoid future duplicate composers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-contract-sync-output.txt: Address the concern above.

### FINDING_13: Stall-recovery keyless-file contract contradicts helper behavior
- **Reviewer(s)**: dyn-bash-state-output.txt, dyn-final-report-flow-output.txt
- **Severity**: important
- **Concern**: `stall-recovery.md` says empty/comment-only `ship-pr-state.sh` exits with `CLEARED=false` and remains unchanged, but `clear-stall` rewrites those files with `STALL_TRACKING=false` and emits `CLEARED=true`; orchestrators following the prose can mis-route recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-state-output.txt: Address the concern above.
  - From dyn-final-report-flow-output.txt: Address the concern above.

### FINDING_14: Absent state file clear path can force terminal routing
- **Reviewer(s)**: dyn-bash-state-output.txt
- **Severity**: important
- **Concern**: When `ship-pr-state.sh` is absent, `clear-stall` emits `CLEARED=false` and creates no file, unlike the old inline path that wrote `STALL_TRACKING=false`; a memory/session-only stall may therefore fail the success-path disk clear.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-state-output.txt: Address the concern above.

### FINDING_15: Post-mv reread failure can report uncleared after disk mutation
- **Reviewer(s)**: dyn-bash-state-output.txt
- **Severity**: latent
- **Concern**: If `mv -f` succeeds but the destination re-read fails, `clear-stall` can emit `CLEARED=false` while the on-disk file already contains `STALL_TRACKING=false`, causing disk/memory divergence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-state-output.txt: Address the concern above.

### FINDING_16: Step 18b snapshot-failure contract disagrees with script and tests
- **Reviewer(s)**: dyn-final-report-flow-output.txt, dyn-contract-sync-output.txt
- **Severity**: important
- **Concern**: `step-18b-final-report.md` says `SNAPSHOT_OK=false` must not promote `emit_body`, but the shell and harness intentionally fail open and emit when `write-final-report.sh` succeeds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-final-report-flow-output.txt: Address the concern above.
  - From dyn-contract-sync-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] Token-report failures can leave stale rendered JSON
- **Reviewer(s)**: dyn-final-report-flow-output.txt
- **Severity**: latent
- **Concern**: Step 17/18b token-report failures remain best-effort, so a failed Step 18b token report can leave stale rendered token data for `write-final-report.sh`; reviewer marked this pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-final-report-flow-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] Redaction still runs on pre-sanitize body
- **Reviewer(s)**: dyn-python-closes-output.txt
- **Severity**: latent
- **Concern**: `sanitize_fragment(body, from_md=True)` is only used for pass/fail while `redact.redact(body)` still processes the pre-sanitize string; reviewer marked this as pre-existing and unchanged by the Closes refactor.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-python-closes-output.txt: Address the concern above.
