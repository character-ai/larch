# Rebase + Re-bump Sub-procedure

**Retired in Phase 1 (#3364).** `/implement` no longer performs per-PR version bumps or `CHANGELOG.md` writes on the ship path. The CI-fix rebase + force-push logic lives in `scripts/ship-pr.sh` (`run_rebase_rebump`). Standalone bump/CHANGELOG scripts and this reference doc's historical contract are deleted in Phase 5.
