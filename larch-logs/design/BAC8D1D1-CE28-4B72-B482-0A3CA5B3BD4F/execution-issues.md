### Warnings
- Step 5b OOS filing: bulk `/larch:issue` filing SKIPPED by operator judgment.
  - SECURITY: a security-focus-area OOS ("prefix-only tmpdir validation allows symlink escape") was present in oos-combined.md; the mechanical security filter (`focus-area=security`) did not match the rendered block format (`**Focus area**: security`), so it leaked to the public combined file. Held locally per SECURITY.md; NOT filed. This is a filter format-mismatch bug in the OOS security route worth a separate larch follow-up.
  - STALE: OOS "cleanup audit-log append" is now in-scope (round-2 FINDING_9 folded the audit-log append into the plan).
  - REDUNDANT: validator-duplication OOS items are tracked by the deferred-libs DAG-threaded follow-up issue.
  - All accepted-OOS observations remain captured in the published design log for posterity.
