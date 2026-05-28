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


### FINDING_8: Absolute in-root positional behavior lacks regression coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The documented absolute in-root positional path conversion is not covered by the harness, so regressions in the `${file#"$ROOT"/}` branch could pass while repo-relative tests still succeed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


