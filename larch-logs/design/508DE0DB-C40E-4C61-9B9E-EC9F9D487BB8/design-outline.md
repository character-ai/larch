## Proposed Design Outline

### Goals
- Never let `prune_cached_versions` delete the running version dir or the just-installed target (Defect A).
- Stamp every successful `claude plugin install`, not only stable-verified ones (Defect B).
- Harden Defect C additively so no cached dir stays unstamped and mis-ranked.

### Non-goals
- No committed offline harness and no source-safe refactor of `upgrade-larch.sh` — verify static + by-hand only.
- No change to `keep_versions=8`, the #3231 marketplace-refresh logic, or `claude plugin update` usage.
- No rework of the `has_stamp`-first sort tiering — #3174's "trust stamps over mtime" ranking stays.

### Approach sketch
- Defect A: seed the retained set with both `target_version` and `INSTALLED_VERSION`, guarded by `is_safe_version` + `version_is_retained`; keep the 8-cap.
- Defect B: resolve `ACTUAL_VERSION` before the `LATEST_STABLE` branch and stamp it unconditionally; keep prune gated on `VERIFIED_TARGET`.
- Defect C: backfill a persistent `.larch-installed-at` from `stat_mtime` for any unstamped cached dir, so it ranks by real age while `has_stamp`-first ordering is unchanged.
- Update sibling `upgrade-larch.md` to match the new stamp + retain-running + backfill behavior.

### Surfaces in scope
- `skills/upgrade-larch/scripts/upgrade-larch.sh`
- `skills/upgrade-larch/scripts/upgrade-larch.md`

### Open questions
- None.
