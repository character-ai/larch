### FINDING_1: Duplicate render-cache symlink test boilerplate
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Five new render-cache symlink tests repeat the same fixture setup, making future variants easier to copy incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] plan-review dangling root symlink bypass remains
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `plan-review/` still gates on `[[ -e "$DESIGN_TMPDIR/plan-review" ]]`, so a dangling root symlink is skipped instead of rejected. This is asymmetric with the new `render-cache/` behavior and may conflict with wording that implies both strict subtrees are handled the same way.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_3: Missing render-cache regular-file rejection test
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The harness tests plan-review as an existing regular file but lacks the symmetric render-cache case, so removing render-cache’s `[[ ! -d ]]` guard could go undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_4: Render-cache symlink tests do not assert nothing was staged
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The new render-cache symlink tests only check `PUBLISH_OK=false`; they would miss a failure mode where symlinked content was staged before publish failed for another reason.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] Branch includes unrelated #2945 context-files work
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The branch includes #2945 context-files / validate-plan-commands changes alongside render-cache hardening, which can confuse review scope, CI attribution, and plan fidelity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] find errors are suppressed during symlink scans
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Tree-wide symlink scans use `find ... 2>/dev/null || true`, so permission or traversal failures can be treated like “no symlinks found” for render-cache and plan-review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] Residual TOCTOU gap can silently skip symlink replacements
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: A file or parent directory can still change between enumeration, the per-file `-L` recheck, and `design_publish_stage_file`; in the narrow symlink replacement case, staging may skip without setting `PUBLISH_OK=false`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] plan-review dangling-root behavior lacks a harness case
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The plan-review symlink suite has no dangling-root case, leaving the pre-existing dangling plan-review behavior untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] render-cache has no filename allowlist
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Any regular file under the physical render-cache tree can be published after redaction; this is by design under the same-user `$DESIGN_TMPDIR` trust model.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] Context files are passed to Claude before redaction
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Explicit context file bytes still reach `claude` without `redact-secrets.sh`; publication-boundary redaction happens later, and this is pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_11: Documentation phrase does not match acceptance text exactly
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `scripts/design-log-publish.md` says “Symlinks at the top level are skipped” rather than the acceptance phrase “Top-level symlinks are skipped,” which could break strict grep-based acceptance checks despite equivalent meaning.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
