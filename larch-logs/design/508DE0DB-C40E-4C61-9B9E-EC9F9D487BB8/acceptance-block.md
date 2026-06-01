## Acceptance

- [ ] `prune_cached_versions` never deletes the directory named by `INSTALLED_VERSION` (the running tree) nor the just-installed `target_version`.
- [ ] A successful `claude plugin install` writes `.larch-installed-at` for the installed version even when stable-verification fails (`VERIFIED_TARGET=false`); pruning remains skipped on that path.
- [ ] `prune_cached_versions` backfills a persistent mtime-derived `.larch-installed-at` for unstamped numeric cache dirs at prune entry (best-effort). Failed `stat_mtime` or stamp writes leave a dir unstamped and bottom-ranked; the `has_stamp`-first ranking (#3174) is unchanged.
- [ ] Retained-set size stays capped at 8; the common case (running version already in the top-8) is unchanged.
- [ ] `skills/upgrade-larch/scripts/upgrade-larch.md`, `SECURITY.md`, and `docs/installation-and-setup.md` are updated to match the new stamp + retain-running + backfill behavior.
- [ ] `keep_versions=8`, the #3231 marketplace logic, and the `has_stamp`-first sort tiering are not otherwise changed.
- [ ] `make lint` (incl. `lint-bash32`, `shellcheck`) passes; shell stays Bash 3.2-compatible with no new external deps.
- [ ] No `WARN larch_err-redaction-unavailable` is emitted on an upgrade that prunes (verified by the manual retention check and/or the next live upgrade).
