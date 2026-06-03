# test-step-8a-changelog.sh

Stub: see `scripts/implement-finalize.md` for the primary contract.

Phase 1 (#3364) offline regression harness: `implement-finalize.sh postbump` must not write `CHANGELOG.md` or invoke `commit-changelog.sh` even when a manifest is present (`CHANGELOG_STATUS=skipped-phase1`). See `scripts/implement-finalize.md` for the postbump contract.
