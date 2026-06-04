## Proposed Design Outline

### Goals
- Make a merged `LARCH_SPARSE_DIRS` addition reach existing installs via the documented `/release` + `/upgrade-larch` path — no manual marketplace remove + add.
- On an already-latest install, `/upgrade-larch` reconciles a drifted sparse cone (RC2 — the blocker).
- Warn operators about cone drift proactively at session start.

### Non-goals
- No change to allowlist *contents*, prune/retention ranking, or legacy-full-clone migration.
- No `python`-specific branches — the fix is generic to any future allowlist dir.
- No auto-reconcile from the SessionStart hook (warn only; hook never mutates).

### Approach sketch
- RC2: gate the idempotency early-exit on `marketplace_sparse_cone_matches`; on cone drift, fall through to the existing remove + sparse re-add + reinstall path (which also repairs `known_marketplaces.json` sparsePaths).
- RC1: change `/release` Step 7 so the just-released allowlist applies within the release cycle, resolving cache/version paths correctly (do not run the working-tree script with a mis-derived `PLUGIN_ROOT`).
- Drift warning: add a warn-only cone-drift probe to `scripts/sessionstart-health.sh`, comparing the marketplace cone against the expected `LARCH_SPARSE_DIRS`.
- Single source of truth for `LARCH_SPARSE_DIRS` shared by the upgrade script and the drift probe (or a synced + linted duplicate).
- Regression coverage for both "reconcile on drift" and "allowlist addition propagates."

### Surfaces in scope
- `skills/upgrade-larch/scripts/upgrade-larch.sh` (+ sibling `.md`)
- `.claude/skills/release/SKILL.md` (Step 7 invocation)
- `scripts/sessionstart-health.sh` (+ sibling `.md`)
- Shared allowlist source (new small lib) consumed by both scripts
- `skills/upgrade-larch/scripts/test-upgrade-larch-retention.sh` (or a sibling harness) + `Makefile`

### Open questions
- RC1 mechanism: re-run the newly-installed `upgrade-larch.sh` (with a correct `CLAUDE_PLUGIN_ROOT`) after install, vs. another path — for the plan + review to settle.
- Extract `LARCH_SPARSE_DIRS` to a shared lib vs. duplicate-with-sync-lint — for the plan + review to settle.
