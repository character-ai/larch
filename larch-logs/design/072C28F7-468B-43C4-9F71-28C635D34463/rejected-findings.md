### [Plan Review] FINDING_15

### FINDING_15:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: nit
- **Focus area**: architecture
- **Location**: scripts/design-log-publish.sh:289-396
- **Concern**: FINDING 3: The plan copies another bespoke tree-staging block instead of removing the drift source. Scenario: This issue exists because plan-review and render-cache staging evolved separately; duplicating the same symlink, prefix, enumeration, and staging logic leaves future hardening to be patched in two places again
- **Proposed resolution**: Consider extracting a small shared staging helper with parameters for subtree name, destination prefix, and optional relpath validator; keep render-cache deny-only by passing no allowlist validator while sharing the safety checks


