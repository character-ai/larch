### FINDING_3: Early terminal returns bypass the difficulty restage
- **Reviewer(s)**: Codex-Innovation, Codex-dyn-Run Log Integrity
- **Severity**: blocking
- **Concern**: The `main-agent-vote-required` and `coder-main-agent-required` exits return before the flush helper, so the resolved tmpdir difficulty record never gets re-staged on those terminal paths. That leaves final-summary and PR-body consumers reading the stale step-2 snapshot.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Call the restage helper in that branch too, or move the helper into a shared terminal-exit path that every Step 5 return uses after _resolve_step5_tier.
  - From Codex-dyn-Run Log Integrity: Invoke the same restage helper in that early-return branch after _record_escalation_if_needed and before return 0, so every Step 5 terminal exit writes the resolved tmpdir difficulty-rating.json into the batch.


### FINDING_5: Restage helper needs fail-open exception handling
- **Reviewer(s)**: Cursor-dyn-Run Log Integrity
- **Severity**: important
- **Concern**: If `_restage_difficulty_batch` itself throws, the outer Step 5 handler can still be tripped and turn an otherwise successful terminal exit into `stall` or `internal-error`. The restage call needs the same exception-swallowing contract as the existing code-review flush path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-Run Log Integrity: Wrap `_restage_difficulty_batch` in the same fail-open try/except Exception contract as the code-review flush (stderr warning + execution-issues Warning), matching the plan edge case "Run-log write failure: warn ... do not fail Step 5"


### FINDING_2: Audit-deltas filter should key off audit-upgrade, not audited
- **Reviewer(s)**: Cursor-Arch, Codex-Arch
- **Severity**: important
- **Concern**: `_render_audit_deltas` is expected to list only upgrade cases, but the current peer selection still relies on `audited`. Once implement runs can be audited without an upgrade, those runs will be incorrectly included/excluded from the audit-delta peer pool, skewing the analyzer and potentially hiding the intended upgrade-only view. The filter also needs to stay safe when `record.rating` is missing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: When `_render_audit_deltas` filters upgrade rows, select peers with `not _truthy(peer.rating.get("audit_upgrade"))` (or a dedicated `audit_upgraded` property), not `not peer.audited`.
  - From Codex-Arch: Add `RunRecord.audit_upgraded` or a local predicate that returns false when `record.rating is None`, then filter `_render_audit_deltas` on that guarded predicate.


