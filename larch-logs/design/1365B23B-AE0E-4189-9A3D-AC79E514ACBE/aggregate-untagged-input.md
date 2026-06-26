### FINDING_2:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:41-53; skills/implement/SKILL.md:142-150
- **Concern**: Externalizing the universal no-prose suppression into a non-mandatory shared pointer drops the only always-loaded guard for both skills.. Scenario: A session that follows the updated SKILL.md text but never opens the new shared file can start emitting inter-call prose again, silently regressing the verbosity contract.
- **Proposed resolution**: Keep the no-prose prohibition and best-effort closer in each SKILL.md, or make the shared anchor a mandatory read/load at the top of the section.
