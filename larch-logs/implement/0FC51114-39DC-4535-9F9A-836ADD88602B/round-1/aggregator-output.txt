### FINDING_1: [OUT_OF_SCOPE] Stub-root naming clarity
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The harness now has two similarly named stub roots, `stub-bin` for `LARCH_PLAN_REVIEW_*_SH` wrappers and `bin` for PATH binary backstops, which could be misread when adding cases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] Production external-agent launchers can still hang when installed binaries are unhealthy
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Production Codex/Cursor launcher paths still lack a fast-fail health probe or shorter timeout, so installed-but-unhealthy external binaries can still block outside this test harness. Reviewers consistently marked this as pre-existing or intentionally deferred from #3338.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] EXTSTUB cursor output path does not match capture-stdout-only mode
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: The `EXTSTUB` cursor test helper parses `--output` from argv, but `launch-review` uses capture-stdout-only for cursor agent invocations, so the real-panel case may not deterministically produce JSON when the real cursor is broken.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] Broader harness re-audit is not evidenced
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The diff does not document a plan re-audit of other make-lint harnesses, leaving a future risk that another harness could reintroduce real binary launches without this file’s `STUB_BIN` pattern.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_5: Reviewed feature commit scope marker
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Reviewers identified `476cb2b5b` as the in-scope feature commit for fixing the `test-plan-review-loop` hang when externals are unavailable. No distinct behavioral risk was stated beyond scope identification.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] larch-logs chore commits
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Reviewers marked the `d51eb4db4` / `f884a182d` larch-logs chore commits as out of scope for this review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] Harness outcomes do not assert stub binary execution
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The harness verifies outcomes but does not directly assert that `STUB_BIN` / `EXTSTUB` binaries were executed, so a future PATH regression could theoretically fall back to real CLIs without a targeted assertion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] Reused `D1C` test directory variable
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `D1C` is assigned twice in `test-plan-review-loop.sh`, first for combined-fallback and then for codex-down, overwriting the first directory variable. The reviewer marked this as pre-existing and not introduced by the diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
