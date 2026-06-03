# Rebase + Re-bump Sub-procedure

**Consumer**: None after Phase 1 (#3364). Historical `caller_kind` tokens (`step8b_rebase`, `step12_phase4`) are retired.

**Contract**: Retirement stub. CI-fix rebase lives in `scripts/ship-pr.sh` (`run_rebase_rebump`). Do not treat former steps as operative until Phase 5 deletes this file.

**When to load**: Never for implementation. Trace #3364 retirement or `conflict-resolution.md` cross-links only.

---

**Retired in Phase 1 (#3364).** No per-PR bumps or CHANGELOG on the ship path. Use `run_rebase_rebump` in `ship-pr.sh`. Phase 5 deletes standalone bump/CHANGELOG scripts and this stub.
