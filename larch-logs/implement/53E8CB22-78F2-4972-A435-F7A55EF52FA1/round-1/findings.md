### FINDING_1: Missing regression test for outside-input move failure
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The guarded outside-input `mv` failure path is implemented but not covered by regression tests. A future regression could lose the non-fatal `REASON=dispatch-failed` behavior, clobber or alter the input ballot, or exit under `set -e` without CI catching it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_2: CLI docs show unsupported equals-form flag syntax
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: The CLI table documents `--allow-findings-outside-tmpdir=true`, but the parser accepts only split argv form. Operators copying the documented caveat get an unknown option instead of enabling outside input.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_3: Move-failure warning hardcodes findings.md
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: The new move-failure warning hardcodes `findings.md` despite generic `--findings-file` support, so outside-ballot failures with other names report a misleading preserved-file message.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_4: Duplicate stub-compatible heredoc in tests
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Cases 2 and 3 duplicate the same 3-block stub-compatible heredoc, so future slot-name changes require editing identical content in two places.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] Pre-existing warnings hardcode findings.md
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Pre-existing warning paths uniformly say `findings.md` regardless of the actual `--findings-file` path, causing misleading diagnostics for non-default ballot paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: Outside-findings opt-in can clobber arbitrary writable files
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: The opt-in flag permits a successful merge to `mv -f` over any same-UID writable regular file outside `--review-tmpdir` with no destination allowlist, so a misconfigured caller could overwrite sensitive writable files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] Raw findings path used after canonical containment check
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: The script computes a canonical findings path but later mutates the raw `FINDINGS_FILE`; a relative path plus cwd change between validation and `mv` could target a different inode than the containment check validated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_8: Guarded mv contract widens for all opt-in invocations
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The guarded `mv` path runs for every `--allow-findings-outside-tmpdir true` invocation, not just outside-tmpdir ballots. A driver that always passes the flag would lose the hard `set -e` abort behavior for in-tmpdir move failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_9: Move failure reuses dispatch-failed reason
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The `move-failed` path reuses `REASON=dispatch-failed`, so callers branching only on `REASON` cannot distinguish post-validation replace failures from dispatch failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] Default path still uses unguarded mv under set -e
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: The default-off path still uses unguarded `mv` under `set -e`; this predates the current feature scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
