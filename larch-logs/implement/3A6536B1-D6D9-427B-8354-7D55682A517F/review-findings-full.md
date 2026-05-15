### REJ_C1: Cursor-Edge-cases (round 1) [code-review/rejected]

**Finding**: `scripts/ship-pr.sh:1166-1175` — `git add -u` in `run_ci_fix_vendor` only stages tracked files; a vendor CI fix that adds untracked files would leave the tree dirty after commit.
**Reason not implemented**: The `git add -u` change is a pre-existing fix added by Codex to address a staging bug (not part of Phase 3 scope). The untracked-file scenario is latent and unlikely in practice; the existing dirty-tree check after the commit provides a safety net. Fixing this is out of scope for Phase 3.

### REJ_C2: Generic-Codex (round 1) [code-review/rejected]

**Finding**: Committed larch-log files include `operator_cwd` and `operator_repo_root` with absolute host paths.
**Reason not implemented**: larch-log commits with operational metadata are expected behavior by design — see `docs/run-logs.md`. The run logs are committed by larch as part of the tracking-issue workflow and are intentional artifacts, not a Phase 3 concern.

### REJ_C3: Generic-Codex (round 1) [code-review/rejected]

**Finding**: `.md` files document `FAILURE_LOG=<path>` "may appear on stdout" but scripts do not actually emit it.
**Reason not implemented**: The "may appear" wording is intentionally non-committal; this same pattern exists in all Phase 1/2 converted scripts. Implementing actual FAILURE_LOG emission requires a trap-based pattern across all scripts — a Phase 4 follow-up task, not Phase 3 scope.

