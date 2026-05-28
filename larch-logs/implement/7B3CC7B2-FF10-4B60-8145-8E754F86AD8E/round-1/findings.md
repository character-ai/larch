### FINDING_1: Finalize Plan Review conflicts with multi-round auto-apply
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Finalize Plan Review still says Step 3 never applies findings and must not revise `plan.txt`, while the multi-round loop and approval-gates guidance document in-loop auto-apply behavior. Operators following only Finalize may skip or duplicate `revise-plan-with-waterfall` behavior or mishandle Gate B after convergence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: Severity precedence cross-reference points to a non-matching heading
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: A cross-reference names a `Severity precedence rule` heading that does not exist verbatim in `approval-gates.md`, making the intended rubric hard to find.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: Structure tests under-pin severity fallback rubric text
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: The #2667 structure test pins only part of the approval-gates severity fallback rubric. It does not cover whole-set Concern-text fallback language or invalid-severity fallback prose, so future edits could remove important Gate B documentation while CI stays green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] Run-log docs omit first-pass vote outputs
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The representative per-round artifact list in `docs/run-logs.md` omits `*-vote-output-first-pass.txt`, even though it is present in the authoritative allowlist.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] Accepted finding templates omit Scenario suffix
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: The accepted FINDING/OOS templates in `plan-review.md` omit the `. Scenario: <text>` suffix that `emit_finding` and `emit_oos` append to Concern and Description. Manual blocks copied from the template may not match loop-produced accepted findings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_6: Loop-emitted Severity lines make Concern-text fallback effectively unreachable
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `emit_finding` always writes a structured Severity line and defaults missing TSV severity to `nit`, so normal loop output uses H/M/L structured buckets rather than Concern-text C/H/M/L fallback. Operators may expect Concern-text classification for empty reviewer TSV severity, but that path generally requires a missing or invalid Severity line.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_7: Gate B prompt text acceptance criteria lack structure-test coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The two Gate B AskUserQuestion question-text formats are acceptance criteria but are not pinned by the new structure tests. A future edit could remove or swap the structured H/M/L and Concern-text C/H/M/L prompt strings without failing the #2667 checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_8: Env-var documentation parity is not protected across docs
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Env-var contracts are duplicated in `flags.md` and `configuration-and-permissions.md` without cross-doc structure pins, and docs-only `relevant-checks` may not run `test-design-structure`. A follow-up could change fail-closed exit-2 prose in one file but not the other.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] SECURITY.md conflates round allowlist with top-level snapshot staging
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: New `SECURITY.md` prose suggests `plan.txt.before-revise` is covered by the strict plan-review round allowlist, but that allowlist covers round-N paths while the rollback snapshot can be staged as a top-level tmpdir file via permissive maxdepth-1 staging. Readers may conclude the snapshot is publish-blocked or governed by the wrong allowlist.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_10: Invalid loop env-var docs omit Step 3b branch behavior
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Loop env-var docs state invalid argv values exit 2, but omit the plan edge-case that Step 3 short-circuits to Step 3b through `panel-failed` handling without Gate B. Operators reading only `flags.md` or `configuration-and-permissions.md` may not know where `/design` lands after argv failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
