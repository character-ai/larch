### [Plan Review] FINDING_2

### FINDING_2: New repo-wide Codex exec auth linter is scope creep
- **Reviewer(s)**: Codex-Arch, Codex-Innovation
- **Severity**: latent
- **Concern**: Adding a new repo-wide `codex-exec` auth linter and wiring expands a targeted auth sweep into a new enforcement subsystem with allowlist, pragma, Makefile, pre-commit, docs, and harness maintenance surface that could block unrelated work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Drop the new linter and its wiring from this PR; keep the launcher/routing changes and targeted regression tests for the six swept call sites
  - From Codex-Innovation: Defer lint-codex-exec-auth and its pre-commit/Makefile/docs/harness wiring to a follow-up; keep this PR to the launcher/auth wiring and targeted tests for the changed call sites.


### [Plan Review] FINDING_9

### FINDING_9: Installation prerequisite doc omitted from auth inventory updates
- **Reviewer(s)**: Codex-dyn-doc-contract-drift
- **Severity**: latent
- **Concern**: The canonical auth inventory is updated in other consumer docs, but `docs/installation-and-setup.md` would still describe a narrower set of OpenAI API key covered surfaces.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-doc-contract-drift: Add docs/installation-and-setup.md to the doc update set, preferably with a short wording that matches or links to the canonical inventory rather than duplicating another long list.

