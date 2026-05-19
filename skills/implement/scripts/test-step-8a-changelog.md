# test-step-8a-changelog.sh

Stub: see `scripts/implement-finalize.md` for the primary contract.

Offline regression harness for the Step 8a changelog fallback logic in `scripts/implement-finalize.sh::maybe_update_changelog()`. Exercises three fixtures:
- Valid manifest → `CHANGELOG_STATUS=updated`
- Empty manifest + `ISSUE_NUMBER` set → fallback `Closed: #N` bullet written to `CHANGELOG.md`
- Empty manifest + no `ISSUE_NUMBER` → `CHANGELOG_STATUS=fail-no-manifest-no-issue` and loud error
