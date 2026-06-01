### [Plan Review] FINDING_2

### FINDING_2: Change 3 persistent mtime backfill expands rollback retention beyond urgent fix
- **Reviewer(s)**: Codex-dyn-scope-creep-audit
- **Severity**: important
- **Concern**: Change 3 turns ranking-time-only mtime fallback for legacy unstamped dirs into persistent stamp-on-prune backfill, despite the existing contract that stamped dirs sort before unstamped legacy dirs and mtime is only a fallback at ranking time. With Change 1 protecting the running dir and Change 2 stamping future installs, backfilling every cached dir before ranking can let a recent legacy unstamped dir become stamped and outrank older real stamped installs, changing rollback cache retention beyond the scoped urgent fix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-scope-creep-audit: Remove Change 3 from this plan, including the helper, prune call, doc bullets, and manual-test expectation. Keep only Changes 1 and 2; handle legacy stamp backfill in a separate scoped follow-up if still desired.


