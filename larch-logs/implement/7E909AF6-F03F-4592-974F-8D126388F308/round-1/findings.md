### FINDING_1: Relative positional paths can escape the lint root
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Positional path handling does not canonicalize or reject `..` segments before scanning, so crafted relative paths, and some absolute paths with embedded traversal, can read `.sh` files outside the configured root.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_2: Docs overstate lint-bash32 as staged-files only
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `docs/linting.md` describes the hook as staged-files only, but CI and `make lint-only` run pre-commit over all tracked shell files. The docs should distinguish commit-time incremental behavior from repo-wide lint behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_3: Positional violation test duplicates fixture setup
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The positional violation test duplicates the whole-repo bad-unsuppressed fixture heredoc, creating drift risk if rule fixtures change later.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: Whole-repo temp file is created for positional-only runs
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `lint-bash32.sh` always creates the temporary file used for whole-repo enumeration, even when positional arguments mean that path is unused.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: Flags after positional paths can change the root unexpectedly
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Argument parsing permits options after positional paths, so a manual invocation like `path --root /other` can scan earlier paths against a later root value.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] Branch contains unrelated feature and log collateral
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The branch includes unrelated `check-contains-pins` Makefile/test wiring, large `larch-logs/` artifacts, and version-bump collateral alongside the lint-bash32 work, increasing review noise but not changing the feature surface under review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_7: Absolute in-root paths are compared without canonicalization
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Absolute in-root detection relies on raw string prefix checks against `"$ROOT"/`, which can skip valid in-root files when macOS path aliases such as `/private/...` versus `/...` differ.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_8: Absolute in-root positional behavior lacks regression coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The documented absolute in-root positional path conversion is not covered by the harness, so regressions in the `${file#"$ROOT"/}` branch could pass while repo-relative tests still succeed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_9: Positional mode silently ignores missing files
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `scan_file` no-ops for missing positional paths, so a typo or deleted `.sh`/`.inc.bash` argument can exit successfully without warning that the intended file was not scanned.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] Zero-arg hook invocation would full-scan the repo
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Unlike `pre-commit-shellcheck.sh`, `lint-bash32.sh` has no zero-argument fast path, so a theoretical empty-argument hook invocation would trigger a whole-repo scan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
