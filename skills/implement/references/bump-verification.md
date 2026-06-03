# Bump verification

**Consumer**: No active runtime consumer after Phase 1 (#3364). Historical callers were `/implement` Step 8+ post-bump verification via `scripts/check-bump-version.sh` and the Rebase + Re-bump Sub-procedure Block β matrix before retirement.

**Contract**: Retirement stub only — per-PR bump verification is removed from the ship path. Do not treat former Block β or Block γ guidance as operative contract; versioning is operator-driven via `/release` (Phase 3) until Phase 5 deletes standalone bump scripts and this file.

**When to load**: Never for implementation work. Load only when tracing Phase 1 #3364 retirement scope from SKILL.md invariant removals or CHANGELOG archaeology.

---

**Retired in Phase 1 (#3364).** `/implement` no longer runs `check-bump-version.sh` on the ship path. Versioning moves to the operator-run `/release` skill (Phase 3). Standalone bump verification scripts are deleted in Phase 5.
