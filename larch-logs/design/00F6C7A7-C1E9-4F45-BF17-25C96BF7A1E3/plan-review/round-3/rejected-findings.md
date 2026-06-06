### [Plan Review] FINDING_3

### FINDING_3: Step 2.4 recovery bail reason mirror is missing
- **Reviewer(s)**: Codex-dyn-skill-site-coverage
- **Severity**: latent
- **Concern**: The plan’s concrete SKILL.md mirror touch sites cover §2.1.5 and §2.2, but Step 2.4 also assigns `FINAL_BAIL_REASON=recovery-out-of-scope`. If that path is not mirrored to `IMPLEMENT_BAIL_REASON`, Step 18a may render the bail reason as `none` instead of the expected redacted fail-closed reason.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-skill-site-coverage: Add the recovery-out-of-scope assignment to the SKILL.md mirror pass, or explicitly state that this path is excluded because it does not route through the Step 12d stall handoff.

