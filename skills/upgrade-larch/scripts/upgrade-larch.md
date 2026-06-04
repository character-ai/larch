# scripts/upgrade-larch.sh — contract

Upgrades the larch plugin to the latest stable version, with idempotency, sparse-cone reconciliation, and post-install verification.

## Purpose

Automates the uninstall-and-reinstall sequence needed to pick up the latest stable larch version. Invoked by `/upgrade-larch`, and by `/release` Step 7 through the working-tree script when a marketplace/cache install root is resolvable.

## Behavior

1. **Resolve latest stable release** — queries paginated GitHub releases, selects stable releases (`prerelease=false`, `draft=false`), strips the leading `v`, and ignores any unexpected non-version lines before choosing the first valid stable tag as `LATEST_STABLE`. If `gh` is unavailable or the query fails / returns no stable releases, the script warns and proceeds unconditionally. On `gh` failure it logs only a short warning with the exit status, not the full stderr payload.
2. **Idempotency and cone check** — compares the resolved stable version against the currently installed version from Claude plugin metadata / CLI output, falling back to `basename "$PLUGIN_ROOT"` only when metadata is unavailable. If they match, `marketplace_sparse_cone_matches` succeeds, and any active cache-shaped `PLUGIN_ROOT` basename also matches the stable version, the script writes or refreshes `.larch-installed-at` on the installed version directory, runs prune (step 7, which retains both the target and the currently-running version directory), prints `Already at latest stable larch release (<version>). No upgrade needed.`, and exits 0 without mutating the marketplace or reinstalling the plugin.
3. **Same-version cone reconciliation** — if the installed version is already the latest stable but the marketplace clone is missing, not a git repo, has `larch-logs/`, has an empty sparse list, or has a sparse cone that differs from `scripts/lib-sparse-dirs.sh`, the script does not early-exit. It prints the fixed reconcile message, uninstalls/reinstalls, and refreshes the marketplace through step 5. After the reinstall command succeeds, post-install version verification passes, and the marketplace cone matches the expected allowlist, it emits `LARCH_CONE_RECONCILED=true` on stderr for `/release` Step 7; the signal is not inferred from the earlier prose banner. Operators with a legacy full active install are now repaired on this same-version reconcile path instead of waiting for the next version-changing upgrade.
4. Uninstalls `larch@larch-local` (best-effort — may not be installed).
5. **Marketplace refresh** — uses a sparse cone checkout that includes every top-level tracked directory except `larch-logs/` (committed run logs, never read at runtime) and `mermaid-lint/` (dev-only Mermaid toolchain, excluded so the installed plugin has no `package.json` and the installer runs no `npm install`). The include list lives in `scripts/lib-sparse-dirs.sh` as `LARCH_SPARSE_DIRS`; `upgrade-larch.sh` sources that library from `SCRIPT_ROOT`, not from `PLUGIN_ROOT`.
   - **Steady state** — when `$HOME/.claude/plugins/marketplaces/larch-local` is a git clone, `larch-logs/` is absent, and `git sparse-checkout list` exactly matches `LARCH_SPARSE_DIRS`, runs `claude plugin marketplace update larch-local` (in-place git pull). On update failure, falls back to removing any remaining clone directory and then running `marketplace add character-ai/larch --sparse $LARCH_SPARSE_DIRS`.
   - **One-time / legacy / missing / stale cone** — when the clone is missing, not a git repo, still has `larch-logs/` (legacy full clone), or has a sparse cone that differs from `LARCH_SPARSE_DIRS`, runs `marketplace remove`, removes any remaining clone directory, then runs `marketplace add character-ai/larch --sparse $LARCH_SPARSE_DIRS` to establish the sparse cone. Subsequent upgrade runs take the steady-state update path until the include list changes again.
6. Installs the `larch` plugin from the marketplace (`claude plugin install larch@larch-local`). `uninstall` + `install` are unchanged: old cached version directories persist until prune (keeps up to 8 for rollback). Do not use `claude plugin update`.
7. **Post-install verification** — resolves the installed `larch@larch-local` version from Claude plugin metadata / CLI output and writes `.larch-installed-at` (epoch seconds) when the resolved version is version-shaped and stable verification passes. When a target stable version was resolved in step 1, the script confirms the installed version matches `LATEST_STABLE`. If verification fails, the script warns and exits non-zero so operators and automation do not misread the run as a successful stable upgrade; pruning (step 8) is still skipped on that path to preserve rollback candidates. When the resolved installed version changed from the pre-run version after stable verification, the script emits `LARCH_NEW_VERSION_INSTALLED=true` for release automation. When no stable version can be resolved but reinstall commands succeed, it emits `LARCH_RESTART_REQUIRED=true` instead so release cleanup can request a restart without treating the install as a verified new version.
8. **Prune old versions** — runs only after step 7 verifies the expected stable version, or on the already-latest-and-cone-matches path in step 2. At prune entry, best-effort backfill writes persistent `.larch-installed-at` from directory mtime for unstamped numeric cache dirs before ranking. Always retains both the just-installed or verified target directory and the currently-running version directory (`basename "$PLUGIN_ROOT"`) when present. `/release` Step 7 must pass the active cache-shaped root as `CLAUDE_PLUGIN_ROOT` so prune protects the running cache even when metadata names a newer version.
9. Prints the installed `larch@larch-local` version block for visual confirmation.

Steps 4–5 use `|| true` on uninstall and remove where noted because the plugin/marketplace may not exist (first install, or already removed). A failed marketplace remove emits a warning, then the sparse re-add path removes `$HOME/.claude/plugins/marketplaces/larch-local` itself before calling `marketplace add`; if add still fails, the recovery banner includes manual `marketplace remove`, clone removal, sparse marketplace add, and plugin install commands. Marketplace clone paths are bound from `$HOME` per call rather than at source time, so harnesses can isolate `HOME` before sourcing.

## Script root versus plugin root

`SCRIPT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"` is the tree containing the script being executed. `upgrade-larch.sh` sources `scripts/lib-sparse-dirs.sh` from `SCRIPT_ROOT`, so a working-tree `/release` invocation reads the just-released allowlist even when `CLAUDE_PLUGIN_ROOT` points at an older cached install.

`PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$SCRIPT_ROOT}"` remains the installed/cache root for `scripts/lib-quiet.sh`, `LARCH_CACHE_DIR`, `INSTALLED_VERSION`, install stamps, and prune protection. Do not source the sparse allowlist from `PLUGIN_ROOT`.

## `/release` coupling

`.claude/skills/release/SKILL.md` Step 7 runs the working-tree `skills/upgrade-larch/scripts/upgrade-larch.sh` against the resolved active installed/cache root whenever that root exists. It captures combined stdout/stderr, parses only the machine-readable `LARCH_CONE_RECONCILED=true`, `LARCH_NEW_VERSION_INSTALLED=true`, and `LARCH_RESTART_REQUIRED=true` lines from successful invocations, and writes `release-step7.env` so Step 8 can require a Claude Code restart after a verified version install, same-version cone repair, or successful unverified reinstall. The release flow must prefer an existing cache-shaped active `CLAUDE_PLUGIN_ROOT` over newer installed metadata for the prune/stamp context.

## `gh` availability

`gh` must be installed and authenticated for the stable-release resolution (steps 1–3) and stable-target verification / pruning decisions (steps 7–8) to work. When `gh` is unavailable, fails, or returns no stable releases, the idempotency check is skipped, the upgrade runs unconditionally, and prune is skipped.

## Edit-in-sync

- `scripts/lib-sparse-dirs.sh` and `scripts/lib-sparse-dirs.md` — canonical sparse allowlist and source-root contract
- `skills/upgrade-larch/SKILL.md` — the skill that invokes this script
- `.claude/skills/release/SKILL.md` — Step 7 working-tree invocation and Step 8 restart coupling
- `docs/installation-and-setup.md` — documents the Upgrade and release flows
- `docs/skills.md` — skill catalog entry
- `SECURITY.md` — trust model for install-stamp pruning and SessionStart sparse-cone drift warning
- `skills/upgrade-larch/scripts/test-upgrade-larch-retention.sh` — includes the intentional sparse-dir literal guard; allowlist edits must update both it and `scripts/lib-sparse-dirs.sh`
- `Makefile` — wires remaining local validation targets such as `test-upgrade-larch-retention`
