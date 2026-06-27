### OOS_1: [OUT_OF_SCOPE] Design runs still omit consolidated breadcrumbs after implement-only fix
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: latent
- **Concern**: Design `log-publish` uses the worktree `larch-logs` tree as `log_root`, so the breadcrumb scan root resolves to the worktree, not `DESIGN_TMPDIR` where `quiet_init` writes logs. `/design` runs still omit consolidated `breadcrumbs/quiet.log` after this fix; the feature description mentions design but the plan scoped implement-only changes. Follow-on work is out of this PR scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Follow-on: pass DESIGN_TMPDIR as source hint or set LARCH_BREADCRUMB_SOURCE_DIR before design run-log commit (out of this PR scope).

### OOS_2: [OUT_OF_SCOPE] SECURITY.md still documents non-directory hint as enforced reject
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: latent
- **Concern**: SECURITY.md §4 still lists “source path exists but is not a directory” as an enforced fail-closed reject, but `publish_breadcrumbs_main` no longer validates `src.is_dir()`. A file at `session/breadcrumbs` (not a directory) can now scan the session root and publish quiet logs instead of returning rc=1. Plan explicitly scoped out doc updates; behavior aligns with `docs/run-logs.md` hint-path contract, not the stale SECURITY.md bullet.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Restore if src.exists() and not src.is_dir(): return 1, or update SECURITY.md to match hint-only behavior.

### OOS_3: [OUT_OF_SCOPE] `_breadcrumb_source_confined` fail-open when no tmpdir env vars set
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: `_breadcrumb_source_confined` returns `True` when no `IMPLEMENT/DESIGN/REVIEW/RESEARCH_TMPDIR` env vars are set (fail-open legacy behavior). Pre-existing; plan preserves it; production `/implement` always sets `IMPLEMENT_TMPDIR`.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_4: [OUT_OF_SCOPE] `LARCH_BREADCRUMB_SOURCE_DIR` documented but unimplemented
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: `docs/run-logs.md` documents `LARCH_BREADCRUMB_SOURCE_DIR` override, but no Python implementation exists (`grep` finds zero matches under `python/`). Pre-existing doc/code gap, not introduced or amplified by this diff.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_5: [OUT_OF_SCOPE] Missing dedicated unit tests for symlink/hardlink quiet-log refusal
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: Symlink and hardlink quiet-log refusal paths in `publish_breadcrumbs_main` have no dedicated unit tests. A regression reintroducing unsafe staging of symlink/hardlink quiet logs would not be caught by this PR's test delta.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add tests asserting rc==1 and stderr for symlink/hardlink larch-quiet-*.log candidates.

### OOS_6: [OUT_OF_SCOPE] Direct CLI error handling when source hint parent missing and no tmpdir env
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: Removing the `src.is_dir()` guard changes error handling when the source hint parent does not exist and no tmpdir env is set. Direct `run-log publish-breadcrumbs` CLI use with a missing parent can traceback instead of returning rc=1.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Keep missing-dir success/no-op for confined session roots; retain exists-and-not-dir rejection for malformed hints.

---

**Merge notes (diagnostic only):**

- **FINDING_1** merges correctness FINDING_1, edge-cases FINDING_5 (same `src.is_dir()` removal risk), and codex FINDING_17 (same scenario, higher severity).
- **FINDING_2** kept in-scope; testing FINDING_16 is a separate OOS block (same theme, `out-of-scope-only` slot cannot join an in-scope block).
- Edge-cases FINDING_4 and FINDING_6–10 are positive verification notes with no distinct fix direction; those slots are attributed via merged blocks above.
- Every inventory slot appears at least once: correctness (1–3), edge-cases (1, 4–6), testing (4, 7–8), codex-generalist (1).

