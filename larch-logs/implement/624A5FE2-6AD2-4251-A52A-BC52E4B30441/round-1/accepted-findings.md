### FINDING_10: risk-integration: scripts/test-ship-pr.sh:2346-2375
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Plan-required ship-pr-rrr-phase14 resume test with new commit shape not present rebump_changelog_commit_shape uses ci-initial only; phase14 resume still stubs bump/changelog helpers so resume+new-shape stall is unguarded Add phase14 scenario with real scripts, bump+CHANGELOG history, stall then --resume-phase ship-pr-rrr-phase14 asserting exit 0 and fresh commits
- **Suggested revision**: Address the concern above.


### FINDING_17: correctness: scripts/ship-pr.sh:512-533
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Re-bump CHANGELOG update relies only on --replaces-version retitle, not full entry composition. CHANGELOG rebase conflict resolved to upstream removes the old ## [X.Y.Z] heading; commit-changelog exits COMMITTED=false and ship-pr continues—merged PR may lack an entry for NEW_VERSION. Fallback to write_changelog_entry/maybe_update_changelog when replace fails, or fail closed on missing CHANGELOG commit before force-push.
- **Suggested revision**: Address the concern above.


### FINDING_18: correctness: scripts/commit-changelog.sh:79-115
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] --replaces-version cannot create a section when the old heading is missing. Same upstream-wins conflict path: no heading to retitle, no diff to commit, operator sees only a WARN in failure logs. On awk exit 3, insert a new ## [NEW] section via write_changelog_entry instead of no-op exit 0.
- **Suggested revision**: Address the concern above.


### FINDING_25: correctness: scripts/test-ship-pr.sh:2346-2437
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Mandatory ship-pr-rrr-phase14 resume regression under the new commit shape is missing. Phase-14 resume can regress (stall, wrong drop depth, stale headings) while ci-initial rebump_changelog_commit_shape still passes. Add a phase14 stall+--resume-phase ship-pr-rrr-phase14 test with bump+CHANGELOG fixtures and content assertions.
- **Suggested revision**: Address the concern above.


### FINDING_27: correctness: scripts/test-implement-finalize.sh:2584-2593
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] test-implement-finalize does not assert separate CHANGELOG-over-bump commit shape. Acceptance #3 is only half-covered; regressions swapping back to amend could slip through finalize harness. Assert git log subjects/order in a happy-path postbump fixture with real commits.
- **Suggested revision**: Address the concern above.


### FINDING_4: code-quality: .claude/skills/bump-version/scripts/classify-bump.sh:88-113
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] No harness tests CHANGELOG-at-HEAD idempotency despite plan acceptance #6 Regression in classify walk could ship without direct signal Add minimal test-classify-bump.sh fixture for Bump+CHANGELOG(+optional log) stack
- **Suggested revision**: Address the concern above.


### FINDING_5: code-quality: scripts/ship-pr.sh:512-534
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] commit-changelog failure after apply-bump is warn-only Re-bump can push new plugin.json while CHANGELOG heading still shows OLD_VERSION Document or emit execution-issue when COMMITTED=false after re-bump
- **Suggested revision**: Address the concern above.


### FINDING_9: risk-integration: .claude/skills/bump-version/scripts/classify-bump.sh:199-211
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] No offline test for CHANGELOG-at-HEAD idempotency walk (plan acceptance #6) After separate CHANGELOG commits, classify-bump may return NONE when a new bump is needed or classify when HEAD is already bumped; resume path skips drop-bump and relies on classify-bump Add isolated-git harness with HEAD=CHANGELOG over bump (NONE) and HEAD=CHANGELOG over feature (non-NONE); wire into Makefile
- **Suggested revision**: Address the concern above.


