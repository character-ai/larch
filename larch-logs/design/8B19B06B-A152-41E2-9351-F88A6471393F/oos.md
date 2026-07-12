### FINDING_5: Preserve the owner-PID fallback
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Concern**: The planned adapter-spec construction may omit the existing `LARCH_CLAUDE_PID`/`CLAUDE_PID`/PPID fallback, causing launches to fail when those environment variables are absent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Derive the owner identity with the existing LARCH_CLAUDE_PID-or-PPID policy and test the missing-environment fallback


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_1: Thin wrapper shellcheck manifest is incomplete after rewrite
- **Description**: Thin wrapper shellcheck manifest is incomplete after rewrite. Scenario: `step-5-review.sh` and `step-7a.sh` are listed in `residual-bash-paths.txt`, but the four other scripts becoming thin wrappers (`step-5-resume.sh`, `step-6-entry.sh`, `run-step-checks.sh`, `step-8-ci-fixer.sh`) are not. Lint may skip shellcheck on rewritten wrappers.
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: scripts/residual-bash-paths.txt
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_2: [OUT_OF_SCOPE] Rewritten implement wrappers are absent from the residual Bash manifest
- **Description**: [OUT_OF_SCOPE] Rewritten implement wrappers are absent from the residual Bash manifest. Scenario: Only step-5-review.sh is listed today; step-5-resume.sh, step-6-entry.sh, run-step-checks.sh, and step-8-ci-fixer.sh are not. After the thin-wrapper rewrite they remain Bash and may fall outside residual Bash lint coverage unless added.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: code-quality
- **Location**: scripts/residual-bash-paths.txt
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

