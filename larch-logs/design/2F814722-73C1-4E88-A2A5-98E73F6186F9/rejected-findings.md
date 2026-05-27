### [Plan Review] FINDING_3

### FINDING_3: mtime refresh can happen before validation failure
- **Reviewer(s)**: Codex-Arch
- **Severity**: latent
- **Concern**: The proposed touch placement can mark a cache version as recently used before all writer inputs are validated, so failed invocations can still mutate cache retention state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Move the mtime refresh after every validation block and preferably after a successful session-env write, or centralize it in a validated session-setup helper


### [Plan Review] FINDING_7

### FINDING_7: missing idempotency validation for unchanged mtimes
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The plan does not add the required idempotency test showing that an already-at-latest `/upgrade-larch` run leaves cache mtimes unchanged when install state does not change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add a test case, likely in skills/upgrade-larch/scripts/test-upgrade-larch.sh, that seeds the executing cache dir mtime, runs the already-at-latest path, and asserts no install/prune occurs and the cache dir mtime is unchanged


