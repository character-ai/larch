## Decision 1: Fix the idempotent cone-reconciliation gap (RC2) — the blocker
- **Question**: Must the fix make `/upgrade-larch` reconcile a drifted sparse cone on an already-latest install (`installed == latest_stable`)?
- **Resolution**: Yes — must-fix. The idempotency early-exit in `upgrade-larch.sh` must, when the sparse cone does not match `LARCH_SPARSE_DIRS`, reconcile the cone (and the installed cache) instead of `exit 0`. This is the load-bearing fix; once shipped, any future allowlist addition self-heals on the next `/upgrade-larch`.
- **Source**: issue requirement #2 (confirmed in HEAD: early-exit at upgrade-larch.sh `Idempotency` block never calls `marketplace_sparse_cone_matches`).

## Decision 2: Address RC1 immediately (not just defer one cycle)
- **Question**: How far should the design address RC1 — the `/release` bootstrap lag where `/release` runs the *previously-installed* `/upgrade-larch` (stale `LARCH_SPARSE_DIRS`)?
- **Resolution**: **RC2 + immediate RC1.** `/release` must be changed so a newly-merged `LARCH_SPARSE_DIRS` addition takes effect within its own release cycle (rather than relying on a deferred second `/upgrade-larch` after restart). Mechanism is for the plan/review to choose, but the user's intent is "apply within the release." Note: naively running the working-tree `upgrade-larch.sh` mis-derives `PLUGIN_ROOT`/`LARCH_CACHE_DIR` (they default to the script's repo root, not `~/.claude/plugins/cache/larch-local/larch/<ver>`), so the plan must resolve cache/version paths correctly.
- **Source**: user (Step 1c Q1 = "RC2 + immediate RC1"); issue requirement #3.

## Decision 3: Add a proactive sparse-cone drift warning
- **Question**: Should the design also surface sparse-cone drift proactively, so operators learn about drift without running `/upgrade-larch`?
- **Resolution**: Yes. Add a **warn-only** proactive drift notice. Natural home is the SessionStart advisory hook (`scripts/sessionstart-health.sh`), which already emits advisory `additionalContext`. The detector compares the marketplace clone's actual sparse cone against the expected `LARCH_SPARSE_DIRS`. The hook must NOT mutate state (SessionStart is non-blocking, fast, always exit 0); it only warns and points the operator at `/upgrade-larch`.
- **Source**: user (Step 1c Q2 = "Also add proactive drift warning").

## Decision 4: Regression coverage for both failure modes
- **Question**: What regression coverage is required?
- **Resolution**: Cover (a) "cone drift on an already-latest install is reconciled" and (b) "an allowlist addition propagates to an existing install." Extend the existing offline harness `skills/upgrade-larch/scripts/test-upgrade-larch-retention.sh` (already mocks `claude`/`git`/`gh`) or add a sibling harness; add coverage for any new drift-detection helper. Wire any new harness into the Makefile.
- **Source**: issue requirement #4; codebase (existing `test-upgrade-larch-retention.sh`).

## Decision 5: Generic, not python-specific
- **Question**: Should the fix special-case `python/`?
- **Resolution**: No. The fix must be generic to any future top-level dir added to `LARCH_SPARSE_DIRS`. No `python`-specific branches. `python` is the first instance, not the subject.
- **Source**: user (Step 1c Q2 = "Tightly scoped + generic" intent) + issue ("Not python-specific").

## Decision 6: Hard constraints / must-not-break (codebase-derived)
- **Question**: What existing behavior must be preserved?
- **Resolution**:
  - Preserve the version-changed upgrade path (uninstall → `refresh_larch_marketplace` → install → verify → prune) unchanged.
  - Preserve install-stamp/prune retention semantics (keep-8, stamp-first ranking) — do not modify retention logic.
  - Reuse the existing `marketplace_sparse_cone_matches()` / `prepare_sparse_marketplace_add` / `add_sparse_larch_marketplace` helpers rather than reimplementing cone logic.
  - Bash 3.2 compatibility (BASH_AUTHORING.md): no associative arrays, namerefs, `mapfile`, `${var^^}`, `&>>`.
  - `set -euo pipefail` + the `recover` ERR trap must keep working.
  - SessionStart hook stays fast, non-mutating, always exit 0, and safe (advisory content via `jq -n --arg`).
  - `LARCH_SPARSE_DIRS` is the canonical allowlist source. If both `upgrade-larch.sh` and the drift detector need it, avoid divergence (single source of truth or a synced/linted duplicate) — the plan decides.
  - `/release` is dev-only (`.claude/skills/release/`); keep its existing guards and recovery semantics.
  - Reconciling the cone must also fix `known_marketplaces.json` `sparsePaths` (the `marketplace remove` + `add --sparse` path does this; a bare `git sparse-checkout set` would not).
- **Source**: codebase (`upgrade-larch.sh`, `sessionstart-health.sh`, BASH_AUTHORING.md, `.claude/skills/release/SKILL.md`).

## Decision 7: Explicit non-goals
- **Question**: What is out of scope?
- **Resolution**: Do NOT change the *contents* of `LARCH_SPARSE_DIRS` (python is already present), the prune/retention algorithm, the legacy-full-clone migration trigger semantics, or the Python ship-pr rework. No auto-reconcile from the SessionStart hook (warn only).
- **Source**: user + issue scope.

Record: 7 decisions resolved (2 from user in Step 1c, 5 codebase/issue-derived).
