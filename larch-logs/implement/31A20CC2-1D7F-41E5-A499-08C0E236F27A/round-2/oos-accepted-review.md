### OOS_1: [OUT_OF_SCOPE] Sentinel extraction parser is duplicated across drafter launchers
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-architecture-output.txt
- **Severity**: latent
- **Concern**: `launch-codex-drafter.sh` and `launch-claude-drafter.sh` duplicate inline Python sentinel parsing logic, creating a future drift risk if delimiter or `diff_lines` rules change in only one vendor path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-architecture-output.txt: Address the concern above.


### OOS_2: [OUT_OF_SCOPE] Trusted-instructions merge path lacks direct exec-level regression coverage
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The new `--trusted-instructions-file` path is not directly tested against an operator `~/.codex/config.toml` containing conflicting instructions, so regressions in stripping operator instructions could allow them to override the trusted drafter contract while current tests still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


