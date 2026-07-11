### [Plan Review] FINDING_1

### FINDING_1: Trusted root remains forgeable by direct callers
- **Reviewer(s)**: Codex-Pragmatic, Codex-Requirements
- **Severity**: major
- **Concern**: The proposed changes still trust caller-supplied trusted-root, context, and run-identity values without independently proving that the root belongs to a live guarded session. A direct caller can create a canonical-looking allowed directory, place matching authorization and run-ID values inside it, pass the forged root to the helper or checker, and reach `gh`, leaving the authorization bypass unresolved.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Add a minimal check that proves the trusted root belongs to a live guarded session rather than relying only on its parent and basename, then cover the forged canonical-directory case in the planned negative tests
  - From Codex-Requirements: Bind authorization to independently established live-session state rather than trusting all caller-supplied values. For example, resolve the trusted root and run identity from a live-run registry or remove direct mutation authority from the shell helper and expose it only through an already-authorized Python caller.

