### [Plan Review] FINDING_11

### FINDING_11:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: .pre-commit-config.yaml:76-124; scripts/test-design-log-publish.sh:234-235
- **Concern**: The plan relies on a prompt reminder with no mechanical regression guard. Scenario: Future scripts, Python subprocess argv, or unlisted rule paths can reintroduce inline --body while make lint remains green; the existing design-log harness only checks that pr create ran, not that --body-file was used
- **Proposed resolution**: Add a small lint/pre-commit hook or harness that rejects inline gh --body/--notes outside an allowlist, and extend the design-log-publish gh stub to assert --body-file and inspect the body-file contents


