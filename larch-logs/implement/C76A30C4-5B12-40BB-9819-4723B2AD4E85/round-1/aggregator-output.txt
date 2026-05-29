### FINDING_1: [OUT_OF_SCOPE] branch mixes Stage 3 with unrelated commits
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The branch combines Stage 3 work with unrelated `--trivial` removal and version/net-retry commits, making review, CI failures, traceability, and revert risk harder to reason about for a Stage 3-only merge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] changelog still documents removed monitor behavior
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `CHANGELOG.md` still describes #2826 sentinel/monitor behavior that Stage 3 removes, leaving release notes that contradict the shipped shim behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_3: breadcrumb-monitor truncated flag parsing can exit non-zero
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `scripts/breadcrumb-monitor.sh` uses `shift 2` under `set -e`, so malformed paired flags such as a lone `--stream` can make the shim exit non-zero despite the intended always-exit-0 contract, affecting fence routing and potentially masking writer results.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_4: no minimal regression test for breadcrumb-monitor shim
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Monitor and lint harnesses were deleted without a small replacement test proving the Stage 3 no-op shim exits 0 for representative arguments and avoids reintroducing removed dependencies, so regressions can pass lint and fail production fences.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_5: stale relevant-checks comment references removed linter
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/relevant-checks.sh` still contains a stale `lint-foreground-markers` comment after that linter was removed, misleading contributors who search for the removed check.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: done-trap no-op leaves Step 8 status-file routing broken
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `larch_quiet_append_done_trap` no longer writes `EXIT_CODE` to `LARCH_STATUS_FILE`, but `skills/implement/SKILL.md` still instructs Step 8 to parse that file, risking incorrect ship-pr/review stall, bail, merge, or OOS routing despite `writer_rc` being available.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_7: Family B fence lint removed before remaining fences are collapsed
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `lint-foreground-markers` enforcement was removed while skill markdown still contains Family B background/monitor/wait fences, so a fence edit could drop the writer wait, pass CI, and let orchestration advance before background work finishes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_8: monitor removal drops hung-writer timeout and kill behavior
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Replacing the real monitor with a no-op removes the paired-PID timeout and termination behavior, so hung external agents or Family B writers can run until an outer tool timeout while retaining launcher-injected repo credentials.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_9: lib-quiet redaction failure can emit unredacted diagnostics
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `larch_err` and `larch_errf` fail open when the streaming redactor fails, which can emit unredacted diagnostics to stderr/chat after live breadcrumb redaction removal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_10: breadcrumb-monitor accepts unknown flags silently
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: The no-op monitor shim accepts unknown arguments and exits 0, so mistyped monitor flags may be masked until a subtler runtime synchronization failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_11: no tests for lib-quiet redaction warning paths
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-lib-quiet.sh` does not cover redactor-unavailable or redactor-failed warning branches, so regressions in those fallback paths could ship unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
