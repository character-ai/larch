## Goal
Implement issue #3320: [IMPLEMENTING] [BUG] (URGENT) Fix /upgrade-larch pruning the currently-running version (unstamped dirs)\n\n## Summary.

## Implementation Plan
## Plan

Fix the `/upgrade-larch` cache-prune bug in three behavior changes plus doc updates in `skills/upgrade-larch/scripts/upgrade-larch.sh`, its sibling `.md`, and the canonical install/security docs named by the sibling's edit-in-sync list (`docs/installation-and-setup.md`, `SECURITY.md`). Defects A and B are the issue's required fixes. Defect C hardening (additive, mtime-backfill) is an operator-approved scope expansion (Round 1 Decisions 2 and 3). Shell stays Bash 3.2-compatible; no new external deps. `keep_versions=8`, the #3231 marketplace logic, and the `has_stamp`-first sort tiering (#3174) stay untouched.

### UPDATED: `skills/upgrade-larch/scripts/upgrade-larch.sh`

Three changes. Anchor line numbers are from the current working tree (381 lines).

**Change 1 — protect the running version dir in `prune_cached_versions` (Defect A).**

1a. At line 224, add `_protected` to the locals:
```bash
    local retained="" version version_dir removed=0 _protected
```

1b. At lines 228-230, replace the single-version seed:
```bash
    if [ -n "$target_version" ] && is_safe_version "$target_version" && [ -d "$LARCH_CACHE_DIR/$target_version" ]; then
        retained="$target_version"
    fi
```
with a loop that retains both the target and the running version:
```bash
    # Always retain (a) the just-installed target and (b) the version this
    # script runs from (INSTALLED_VERSION). Deleting the running dir mid-run
    # removes sibling helpers it sources (scripts/lib-quiet.sh,
    # scripts/redact-secrets.sh), breaking log redaction for the rest of the run.
    for _protected in "$target_version" "$INSTALLED_VERSION"; do
        [ -n "$_protected" ] || continue
        is_safe_version "$_protected" || continue
        [ -d "$LARCH_CACHE_DIR/$_protected" ] || continue
        version_is_retained "$_protected" "$retained" && continue
        retained="${retained:+$retained }$_protected"
    done
```
Reuse existing `is_safe_version` and `version_is_retained`. The 8-cap loop below is unchanged; pre-seeding up to 2 protected versions just fills fewer ranked slots. When the running version is already in the natural top-8, `version_is_retained` makes this a no-op.

**Change 2 — stamp every successful install, not only verified ones (Defect B).**

2a. At lines 343-361, hoist `ACTUAL_VERSION` resolution out of the `LATEST_STABLE` conditional and stamp it unconditionally:
```bash
# Resolve the installed version up front so we can stamp it regardless of stable
# verification. The stamp records install time and drives cache-retention
# ranking; an unstamped dir sorts below every stamped version. Pruning stays
# gated on a verified stable install below (rollback safety).
VERIFIED_TARGET=false
ACTUAL_VERSION=$(get_installed_larch_version || true)
if is_safe_version "${ACTUAL_VERSION:-}"; then
    write_install_stamp "$ACTUAL_VERSION"
fi
if [ -n "$LATEST_STABLE" ]; then
    if [ "$ACTUAL_VERSION" = "$LATEST_STABLE" ]; then
        VERIFIED_TARGET=true
        larch_err "Verified: larch ${LATEST_STABLE} installed successfully."
    else
        larch_err ""
        larch_err "Warning: expected version ${LATEST_STABLE} but found installed version ${ACTUAL_VERSION:-unknown}."
        larch_err "A pre-release or unexpected version may have been installed."
        larch_err "Re-run /upgrade-larch or install manually:"
        larch_err "  claude plugin marketplace remove larch-local"
        larch_err "  rm -rf '$MARKETPLACE_CLONE'"
        larch_err "  claude plugin marketplace add character-ai/larch --sparse $LARCH_SPARSE_DIRS"
        larch_err "  claude plugin install larch@larch-local"
    fi
```

2b. At lines 363-369, drop the now-duplicate stamp call (prune stays gated):
```bash
# Prune old versions only after a verified stable install (rollback safety).
# The install stamp was already written above, regardless of verification.
if [ "$VERIFIED_TARGET" = true ]; then
    prune_cached_versions "$ACTUAL_VERSION"
else
    larch_err "Skipping prune because the expected stable version was not verified."
fi
```
`write_install_stamp` no-ops when the dir is absent and warns-but-continues on `date` failure, so the unconditional call is safe. Leave the idempotent already-latest branch (lines 312-324) as-is. After 2a, `ACTUAL_VERSION` is resolved even when `LATEST_STABLE` is empty (the `gh`-unavailable path), so that install gets stamped too. Grep `ACTUAL_VERSION` to confirm no path relied on the old `ACTUAL_VERSION=""` sentinel.

**Change 3 — backfill stamps for unstamped cached dirs (Defect C hardening, operator-approved).**

Add a new helper and call it at the top of `prune_cached_versions`, before listing. It gives every cached dir a persistent `.larch-installed-at` derived from its filesystem mtime, so no dir sorts below stamped dirs merely for lacking a stamp. The `has_stamp`-first sort (#3174) is preserved: after backfill the unstamped tier is empty, and already-stamped dirs are never touched or reordered.

Add the helper above `prune_cached_versions` (for example, just after `version_is_retained`):
```bash
backfill_install_stamps() {
    # Defect C hardening: persistently stamp any unstamped cached version dir
    # from its filesystem mtime (its best "installed-at" proxy), so a recent
    # but unstamped dir no longer sorts below every stamped one. Derives from
    # mtime, not `date +%s`, so a genuinely-old legacy dir keeps an old rank
    # instead of looking freshly installed. Already-stamped dirs are skipped;
    # #3174's has_stamp-first ordering is preserved.
    local version_dir version mt
    shopt -s nullglob
    for version_dir in "$LARCH_CACHE_DIR"/[0-9]*/; do
        version_dir="${version_dir%/}"
        [ -d "$version_dir" ] || continue
        version=$(basename "$version_dir")
        is_safe_version "$version" || continue
        read_install_stamp "$version_dir" >/dev/null 2>&1 && continue
        mt=$(stat_mtime "$version_dir")
        [[ "$mt" =~ ^[0-9]+$ ]] && [ "$mt" -gt 0 ] || continue
        if ! printf '%s\n' "$mt" > "$version_dir/.larch-installed-at"; then
            warn_install_stamp_failure "$version"
        fi
    done
    shopt -u nullglob
}
```
Then call it at the top of `prune_cached_versions`, right after the "Pruning old larch versions..." log line (current line 226) and before the retained seed:
```bash
    backfill_install_stamps
```
This runs on both prune call sites (the idempotent already-latest path and the post-upgrade verified path), so both rank from real install/mtime order. When `stat_mtime` fails (returns 0) the dir is left unstamped and falls to the bottom of the ranking exactly as today — no bogus `0` stamp is written. Reuse existing `is_safe_version`, `read_install_stamp`, `stat_mtime`, and `warn_install_stamp_failure`; do not reimplement.

### UPDATED: `skills/upgrade-larch/scripts/upgrade-larch.md`

Per `.claude/rules/script-md-siblings.md`, update the sibling doc in the same change. Revise the retention/stamp contract (currently 36 lines) to state:
- The install stamp is now written for **any** successfully-installed version (verified or not); **pruning** stays gated on a verified stable install.
- Prune always retains **both** the just-installed target **and** the currently-running version dir (basename of `PLUGIN_ROOT`), and why (avoid deleting sibling helpers the live process sources).
- Prune backfills a persistent stamp (from mtime) for unstamped numeric cached dirs at prune entry before ranking (best-effort). Keep the existing "ranked by install stamp; stamped sort before unstamped" wording, and qualify that unstamped dirs are normally backfilled before ranking on prune runs, but can persist until a prune runs (e.g. verification skipped, `gh` unavailable) or remain unstamped when `stat_mtime` or stamp write fails.
- Update step 6/7 bullets to match: stamp-on-any-successful-install; verified-only prune; retain target plus running version; backfill wording above.

### UPDATED: `SECURITY.md`

Minimal rewrite of the `/upgrade-larch` install-stamp prune trust paragraph (~line 240) so canonical security docs match implementation:
- **Stamp writes** run for any successfully-installed version when the resolved version is version-shaped, not only on verified/already-latest paths; prune remains gated on verified stable or the already-latest idempotent path.
- **At prune entry**, best-effort mtime backfill writes persistent `.larch-installed-at` for unstamped numeric cache dirs; failed mtime reads or stamp writes leave dirs unstamped and bottom-ranked as before (#3174 `has_stamp`-first ordering unchanged).
- **Retention** always includes both the prune target and the running version dir (`INSTALLED_VERSION`) when present and version-shaped, in addition to the eight-cap ranked set.
- Preserve existing limits: user-owned cache parent only, no session pins, version-shaped basenames only, eight-dir cap.

### UPDATED: `docs/installation-and-setup.md`

Minimal matching edits in the Upgrade section (~lines 38–40), aligned with the sibling contract:
- Any successful install writes `.larch-installed-at` when the installed version resolves safely; **pruning** still runs only after verified stable install or on the already-latest path (`gh` unavailable still skips prune).
- On prune, retain both the verified/just-installed target and the currently-running cached version dir (basename of `PLUGIN_ROOT`).
- At prune entry, unstamped numeric dirs are normally backfilled from directory mtime before ranking; dirs may stay unstamped until a prune run or if backfill cannot run.
- Keep restart/idempotency paragraphs unchanged except where they mention stamp/prune behavior.

### Approach
- Three layers protect the running dir: Defect A retains it explicitly; Defect B makes future installs always stamped, so it ranks high naturally; Defect C backfill retroactively stamps pre-existing unstamped dirs.
- Keep script changes minimal; reuse existing helpers; add only one new function. Sync canonical docs (`SECURITY.md`, `docs/installation-and-setup.md`) in the same PR so operators and reviewers do not see a stale stamp/prune contract.
- Preserve all stated invariants: `keep_versions=8`, the #3231 marketplace logic, the #3174 `has_stamp`-first ranking, Bash 3.2 compatibility, no new deps.

### Edge cases
- Running version already in top-8 (common case): the Change 1 loop is a no-op via `version_is_retained`; behavior unchanged.
- `gh` unavailable (`LATEST_STABLE` empty): Change 2a still resolves and stamps `ACTUAL_VERSION`; prune is still skipped (`VERIFIED_TARGET=false`).
- `stat_mtime` failure (returns 0): backfill skips the dir; it stays unstamped and bottom-ranked as today; no `0` stamp persisted.
- Backfill write failure (read-only cache): `warn_install_stamp_failure` warns; the loop continues; ranking falls back to current behavior for that dir.
- All dirs already stamped (post-Defect-B steady state): backfill is a no-op.
- Prune skipped (`VERIFIED_TARGET=false`, `gh` unavailable): backfill does not run; unstamped dirs persist and stay bottom-ranked until a later verified prune.
- Backfill skipped per dir (`stat_mtime` 0 or write failure): dir can remain unstamped across multiple runs.
- `target_version` empty or unsafe: the Change 1 loop skips it (guarded) and retains only the running version.

### Failure modes
- Backfill freezes a wrong mtime for a legacy dir → mis-ranks one re-downloadable cache entry. Earliest signal: an old dir surviving prune, or a recent legacy dir evicted. Mitigation: Defect A protects the one dir whose deletion breaks the run; every other dir is re-downloadable.
- Side-effect write inside the prune path on a read-only `$LARCH_CACHE_DIR` → repeated `warn_install_stamp_failure` lines. Earliest signal: warning spam. Mitigation: best-effort write; the loop continues; prune still ranks by available data.
- `INSTALLED_VERSION` unset at a prune call site → running dir unprotected. Earliest signal: running version evicted again. Mitigation: both prune call sites run after line 273 where `INSTALLED_VERSION` is assigned; confirm that ordering holds after the edits.

### Testing strategy
- Static (required): `bash scripts/relevant-checks.sh` (or `make lint`); confirm `make lint-bash32` and `shellcheck` are clean for the edited script.
- Manual retention check (required, by hand): build a throwaway `LARCH_CACHE_DIR` with 10 fake version dirs, stamp 9 with increasing values, leave the "running" one unstamped; drive `prune_cached_versions "<target>"` with `INSTALLED_VERSION="<unstamped running>"`; assert (a) the running dir survives, (b) exactly 8 are retained, (c) the oldest stamped dir is evicted, (d) backfill wrote a stamp to previously-unstamped survivors.
- Stamp-on-unverified check (required): confirm a resolved version `!= LATEST_STABLE` now writes `.larch-installed-at` while prune stays skipped (read the diff plus the manual setup; no live release needed).
- Doc contract (required): grep/read `SECURITY.md` and `docs/installation-and-setup.md` Upgrade paragraphs for stamp-on-any-install, verified-only prune, target+running retention, and best-effort backfill-at-prune-entry wording consistent with `upgrade-larch.md`.
- No committed offline harness and no source-safe refactor (Round 1 Decision 1).
- Live sanity (optional, post-merge): the next real `/upgrade-larch` emits no `WARN larch_err-redaction-unavailable` and keeps the prior version cached.


## Acceptance

- [ ] `prune_cached_versions` never deletes the directory named by `INSTALLED_VERSION` (the running tree) nor the just-installed `target_version`.
- [ ] A successful `claude plugin install` writes `.larch-installed-at` for the installed version even when stable-verification fails (`VERIFIED_TARGET=false`); pruning remains skipped on that path.
- [ ] `prune_cached_versions` backfills a persistent mtime-derived `.larch-installed-at` for unstamped numeric cache dirs at prune entry (best-effort). Failed `stat_mtime` or stamp writes leave a dir unstamped and bottom-ranked; the `has_stamp`-first ranking (#3174) is unchanged.
- [ ] Retained-set size stays capped at 8; the common case (running version already in the top-8) is unchanged.
- [ ] `skills/upgrade-larch/scripts/upgrade-larch.md`, `SECURITY.md`, and `docs/installation-and-setup.md` are updated to match the new stamp + retain-running + backfill behavior.
- [ ] `keep_versions=8`, the #3231 marketplace logic, and the `has_stamp`-first sort tiering are not otherwise changed.
- [ ] `make lint` (incl. `lint-bash32`, `shellcheck`) passes; shell stays Bash 3.2-compatible with no new external deps.
- [ ] No `WARN larch_err-redaction-unavailable` is emitted on an upgrade that prunes (verified by the manual retention check and/or the next live upgrade).

diff_lines: 115

## Test plan
(no test plan section in plan-file)
