### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/references/plan-review.md:57
- **Concern**: Plan extracts plan-line dedup into a named helper but does not update the existing runtime reference that says the Python is embedded in the bash post-apply step. Scenario: After the PR lands, /design plan-review docs point maintainers to the old implementation shape and obscure the new dedup-plan-lines.py contract
- **Proposed resolution**: Update this bullet to name skills/design/scripts/dedup-plan-lines.py as the whitespace-key post-apply dedup helper while preserving the Gate B divergence note and normalization detail

