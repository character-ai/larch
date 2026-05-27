### FINDING_1: [OUT_OF_SCOPE] Enforce monitor_rc two-branch propagation in Family B lint
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Family B foreground lint accepts wrappers that launch a background writer, run `breadcrumb-monitor.sh`, and `wait`, but do not reliably capture `monitor_rc` or propagate monitor failures through the canonical two-branch exit contract. This can mask monitor timeout/infrastructure failures as writer success and lets unsafe wrapper shapes pass CI, including case 47.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: Split missing-monitor and missing-wait diagnostics
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: When `breadcrumb-monitor.sh` is absent, the linter reports a missing wait-after-monitor diagnostic. This misleads contributors toward wait-order fixes instead of restoring the required monitor invocation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_3: Align PID-capture window documentation with lint behavior
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `BASH_AUTHORING.md` describes the PID-capture placement more strictly than the linter enforces. Authors may believe a third non-blank line capture is invalid even though lint accepts it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: Clarify Step 8+ wrapper exit 4 routing
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The Step 8+ exit matrix does not distinguish wrapper exit 4 caused by monitor timeout from writer stall handling. A monitor timeout with no stall tracking can be routed through the wrong cleanup/resume path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_5: Document or harden test-only kill-by-PID-file pattern
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: The fake monitor test harness kills a process using an unvalidated PID read from a paired PID file. Although harness-only, it resembles an unsafe pattern unless explicitly scoped or validated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_6: Monitor failure branch may leave writer running
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The documented monitor-failure branch uses non-blocking wait without signaling the writer when `monitor_rc=2`. A monitor argv failure can leave `ship-pr.sh` running and race later invocations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_7: Make wrapper exit authoritative over stale status file reads
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Step 8+ routing can read a stale successful `LARCH_STATUS_FILE` value before the writer’s final exit. If the wrapper later exits nonzero, bail or conflict routing may be skipped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] Monitor exit 0 can be misread as writer success
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `breadcrumb-monitor.sh` exits 0 when a done sentinel is present regardless of the status file `EXIT_CODE`. Orchestrators must not treat monitor success as writer success without post-monitor wait/status handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_9: Add explicit wait-and-propagate rationale subsection
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Acceptance criteria require a dedicated `Why wait and propagate?` subsection citing incident `984F0AA4-4436-40F3-A82E-9D114C1A58B4` and naming orphan and discarded-exit-code regression risks. The current prose embeds related rationale elsewhere, making the required narrative harder to find.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_10: Cross-reference lint helper from BASH_AUTHORING.md
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `BASH_AUTHORING.md` cites the lint target but not the enforcing helper by name, making it harder to jump from authoring rules to `fence_has_family_b_pid_capture_and_wait` while debugging CI failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_11: Name enforcing helpers in docs/linting.md table
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The canonical linter table omits helper function names, so readers cannot grep directly for `fence_has_family_b_pid_capture_and_wait` or `scan_shell_file_for_family_b_wait`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
