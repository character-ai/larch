## Decision 8: Retention model — confirmed MAX-8 cap (overrides issue body + review panel)
- **Question**: The 5-round review loop reverted Round 1's "8 = maximum" to the issue body's floor+window model (FINDING_5, Cursor+Codex-Requirements). Floor+window or max-8?
- **Resolution**: **Hard maximum of 8.** `/upgrade-larch` keeps exactly the 8 most-recently-installed version dirs (install-stamp order) and deletes the rest. No version-dir age window. The reviewers' floor+window reversion is rejected by the user as a binding override. The 7-day window governs `/cleanup` session dirs only.
- **Source**: user (Gate B reconciliation)

## Decision 9: Identity record filename — keep `.larch-keepalive` (slimmed)
- **Question**: Rename `.larch-keepalive` → `.larch-session`, or keep the filename slimmed?
- **Resolution**: **Keep `.larch-keepalive`**, slimmed to `CLONE_PATH` + `SESSION_ID` only. No resolver read-path change, fewer files touched. (This supersedes Round 1 Decision 2's rename; matches the review panel.)
- **Source**: user (Gate B reconciliation)

## Kept from the review loop (good, model-independent)
- `/cleanup` newest-activity scan extended to `find -maxdepth 5` so committed `larch-logs/<skill>/<RUN_ID>/round-<N>/findings.md` (depth 5) keep an active session alive.
- Exact-8 fill invariant (FINDING_1): skip an already-retained `$ACTUAL_VERSION` while filling so the cap is exactly 8.
- Absent-target invariant (FINDING_2): count `$ACTUAL_VERSION` toward the cap only when its cache dir exists.
- `agent-lint.toml`, `docs/configuration-and-permissions.md` (`LARCH_CLEANUP_RETENTION_DAYS` only), `docs/installation-and-setup.md`, and `skills/upgrade-larch/SKILL.md` (already-latest path may still stamp+prune) updates.
