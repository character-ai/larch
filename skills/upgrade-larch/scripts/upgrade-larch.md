# scripts/upgrade-larch.sh — contract

Upgrades the larch plugin to the latest stable version, with idempotency and post-install verification.

## Purpose

Automates the full teardown-and-reinstall sequence needed to pick up the latest stable larch version. Invoked by `/upgrade-larch`.

## Behavior

1. **Resolve latest stable release** — queries paginated GitHub releases, selects stable releases (`prerelease=false`, `draft=false`), strips the leading `v`, and ignores any unexpected non-version lines before choosing the first valid stable tag as `LATEST_STABLE` and the next valid stable tag as `PREVIOUS_STABLE`. If `gh` is unavailable or the query fails / returns no stable releases, the script warns and proceeds unconditionally. On `gh` failure it logs only a short warning with the exit status, not the full stderr payload.
2. **Idempotency check** — compares the resolved stable version against the currently installed version from Claude plugin metadata / CLI output, falling back to `basename "$PLUGIN_ROOT"` only when metadata is unavailable. If they match, prints `Already at latest stable larch release (<version>). No upgrade needed.` and exits 0 without touching any plugin state.
3. Uninstalls `larch@larch-local` (best-effort — may not be installed).
4. Removes the `larch-local` marketplace (best-effort — may not be registered).
5. Re-adds the marketplace from `character-ai/larch` on GitHub.
6. Installs the `larch` plugin from the freshly-added marketplace.
7. **Post-install verification** — when a target stable version was resolved in step 1, reads the actual installed `larch@larch-local` version from Claude plugin metadata / CLI output and confirms it matches `LATEST_STABLE`. If verification fails, the script warns and exits non-zero so operators and automation do not misread the run as a successful stable upgrade.
8. **Prune old versions** — runs only after step 7 verifies the expected stable version. It keeps the verified stable version plus one rollback candidate: the previous stable release resolved in step 1 when available and cached locally, otherwise the newest other cached version that is not newer than the verified stable release. Other numeric version directories are removed from the plugin cache. If verification fails, pruning is skipped to preserve rollback candidates.
9. Prints the installed `larch@larch-local` version block for visual confirmation.

Steps 3–4 use `|| true` because the plugin/marketplace may not exist (first install, or already removed). Steps 5–6 run under `set -e` and will fail loudly on network errors, auth issues, or CLI problems. Step 9 also uses `|| true` so an unexpected `claude plugin list` failure does not turn a successful install into a failed upgrade. On failure after teardown, the script prints recovery commands so the user can manually re-add.

## `gh` availability

`gh` must be installed and authenticated for the stable-release resolution (steps 1–2) and stable-target verification / pruning decisions (steps 7–8) to work. When `gh` is unavailable, fails, or returns no stable releases, the idempotency check is skipped, the upgrade runs unconditionally, and prune is skipped.

## Edit-in-sync

- `skills/upgrade-larch/SKILL.md` — the skill that invokes this script
- `docs/installation-and-setup.md` — documents the Upgrade flow
- `skills/upgrade-larch/scripts/test-upgrade-larch.sh` — regression harness for stable resolution, idempotency, verification, prune fallback, and `gh` stderr redaction
