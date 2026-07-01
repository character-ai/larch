### [Plan Review] FINDING_2

### FINDING_2: Plan omits harness anchor-placement constraints for anti-polling literals
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan lists several anti-polling literals as protected but does not document that `scripts/test-implement-anti-polling-rule.sh` enforces them with `check_context` anchor windows, not file-wide grep alone. For `skills/shared/design-background-wait.md`, `When task output is empty` and `call no tool` must appear within two lines after `After the background launch ack`; `end the turn without probing` must appear within two lines after `Foreground terminal-sentinel probe`. Density edits that keep substrings elsewhere but move them out of those windows can still fail CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Extend the protected-literal section with an anchor layout table copied from the harness: `After the background launch ack` plus two lines must retain `When task output is empty` and `call no tool`; `Foreground terminal-sentinel probe` plus two lines must retain `end the turn without probing`; keep the `After the background launch ack` anchor phrase byte-identical.

---

**Merge notes**

- **FINDING_1** merges Innovation **FINDING_1** and Pragmatic **FINDING_3** (same behavioral risk: safe-compression vs dual waiter-ban literals).
- **FINDING_2** stays separate (anchor-placement / `check_context` window constraints; different fix surface).
- Both inventory slots appear in at least one `- **Reviewer(s)**:` line.
- No `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` token (non-empty merge).

