# Rebase + Re-bump Sub-procedure

**Consumer**: No active runtime consumer after Phase 1 (#3364). Historical callers were `/implement` orchestrator steps invoking the Rebase + Re-bump Sub-procedure with `caller_kind` tokens such as `step8b_rebase` and `step12_phase4` before retirement.

**Contract**: Retirement stub only — per-PR version bumps and CHANGELOG writes on the ship path are removed. CI-fix rebase and force-push remain in `scripts/ship-pr.sh` (`run_rebase_rebump`); do not treat this file's former sub-procedure steps as operative contract until Phase 5 deletes standalone bump or CHANGELOG scripts and this file.

**When to load**: Never for implementation work. Load only when tracing Phase 1 #3364 retirement scope from SKILL.md NEVER or invariant removals, or when following `conflict-resolution.md` cross-links to this stub.

---

**Retired in Phase 1 (#3364).** `/implement` no longer performs per-PR version bumps or `CHANGELOG.md` writes on the ship path. The CI-fix rebase + force-push logic lives in `scripts/ship-pr.sh` (`run_rebase_rebump`). Standalone bump/CHANGELOG scripts and this reference doc's historical contract are deleted in Phase 5.
