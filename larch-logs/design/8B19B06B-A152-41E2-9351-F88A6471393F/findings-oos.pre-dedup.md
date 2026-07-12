### OOS_1: Thin wrapper shellcheck manifest is incomplete after rewrite
- **Description**: Thin wrapper shellcheck manifest is incomplete after rewrite. Scenario: `step-5-review.sh` and `step-7a.sh` are listed in `residual-bash-paths.txt`, but the four other scripts becoming thin wrappers (`step-5-resume.sh`, `step-6-entry.sh`, `run-step-checks.sh`, `step-8-ci-fixer.sh`) are not. Lint may skip shellcheck on rewritten wrappers.
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: scripts/residual-bash-paths.txt
- **Phase**: design



### OOS_2: [OUT_OF_SCOPE] Rewritten implement wrappers are absent from the residual Bash manifest
- **Description**: [OUT_OF_SCOPE] Rewritten implement wrappers are absent from the residual Bash manifest. Scenario: Only step-5-review.sh is listed today; step-5-resume.sh, step-6-entry.sh, run-step-checks.sh, and step-8-ci-fixer.sh are not. After the thin-wrapper rewrite they remain Bash and may fall outside residual Bash lint coverage unless added.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: code-quality
- **Location**: scripts/residual-bash-paths.txt
- **Phase**: design



