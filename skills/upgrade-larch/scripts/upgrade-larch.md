# scripts/upgrade-larch.sh — contract

Upgrades the larch plugin to the latest stable version, with idempotency and post-install verification.

## Purpose

Automates the full teardown-and-reinstall sequence needed to pick up the latest stable larch version. Invoked by `/upgrade-larch`.

## Behavior

1. **Resolve latest stable release** — queries `gh api repos/character-ai/larch/releases` and selects the most recent release with `prerelease=false` and `draft=false`. Strips the leading `v` from the tag to get a bare version string. Skipped when `gh` is not available; the upgrade proceeds unconditionally in that case.
2. **Idempotency check** — compares the resolved stable version against the currently installed version (derived as `basename "$PLUGIN_ROOT"`). If they match, prints `Already at latest stable larch release (<version>). No upgrade needed.` and exits 0 without touching any plugin state.
3. Uninstalls `larch@larch-local` (best-effort — may not be installed).
4. Removes the `larch-local` marketplace (best-effort — may not be registered).
5. Re-adds the marketplace from `character-ai/larch` on GitHub.
6. Installs the `larch` plugin from the freshly-added marketplace.
7. **Post-install verification** — when a target stable version was resolved in step 1, checks whether `$LARCH_CACHE_DIR/$LATEST_STABLE` exists. If not, identifies the actually-installed version and emits a warning so the operator can investigate pre-release installs.
8. **Prune old versions** — lists all version subdirectories under `$LARCH_CACHE_DIR` (directories starting with a digit), sorts them by version, and removes all except the two most recent. This ensures at most two versions are ever installed (latest + one rollback).
9. Prints the installed `larch@larch-local` version block for visual confirmation.

Steps 3–4 use `|| true` because the plugin/marketplace may not exist (first install, or already removed). Steps 5–6 run under `set -e` and will fail loudly on network errors, auth issues, or CLI problems. Step 9 also uses `|| true` so an unexpected `claude plugin list` failure does not turn a successful install into a failed upgrade. On failure after teardown, the script prints recovery commands so the user can manually re-add.

## `gh` availability

`gh` must be installed and authenticated for the stable-release resolution (steps 1–2) and post-install verification (step 7) to work. When `gh` is unavailable, the idempotency check and pre-release guard are skipped; the upgrade runs unconditionally.

## Edit-in-sync

- `skills/upgrade-larch/SKILL.md` — the skill that invokes this script
- `docs/installation-and-setup.md` — documents the Upgrade flow
