### FINDING_10: architecture: scripts/implement-finalize.sh:563-653
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Plan write_changelog_entry --replaces-version not implemented; logic duplicated in commit-changelog.sh Step 8a and re-bump paths diverge on category/Unreleased handling over time Share one CHANGELOG writer or document and test retitle-only re-bump contract
- **Suggested revision**: Address the concern above.



### FINDING_3: code-quality: scripts/implement-finalize.sh:563-653 and scripts/commit-changelog.sh:26-176
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Duplicated Keep-a-Changelog awk for insert and replaces-version instead of plan reuse via write_changelog_entry. Future heading-format fixes must be applied twice; drift risks wrong stale-entry removal on CI re-bump. Extract shared lib-changelog-entry.sh used by write_changelog_entry and commit-changelog.sh.
- **Suggested revision**: Address the concern above.



### FINDING_35: architecture: scripts/implement-finalize.sh:563-653
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Plan required --replaces-version to pass through write_changelog_entry; round 1 removed it and duplicated awk only in commit-changelog.sh. Stale-entry removal no longer shares write_changelog_entry with Step 8a; acceptance failure-mode #4 wording is inaccurate. Restore write_changelog_entry --replaces-version and call it from commit-changelog.sh, or update plan/docs to match the split implementation.
- **Suggested revision**: Address the concern above.



