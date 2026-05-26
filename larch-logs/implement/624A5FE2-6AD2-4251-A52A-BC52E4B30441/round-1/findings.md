### FINDING_1: code-quality: scripts/implement-finalize.sh:563-623
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] write_changelog_entry --replaces-version awk is never invoked; only caller uses three-arg form Re-bump stale CHANGELOG logic lives only in commit-changelog.sh; plan pass-through to write_changelog_entry was not implemented Remove dead replaces_version path or wire commit-changelog.sh to shared write_changelog_entry helper
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: scripts/commit-changelog.sh:79-116 scripts/implement-finalize.sh:614-623
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Duplicate stale-version CHANGELOG awk in two scripts Heading or stale-entry rule changes require two edits; behavior can drift Consolidate into one shared function used by commit-changelog.sh
- **Suggested revision**: Address the concern above.

### FINDING_3: correctness: .claude/skills/bump-version/scripts/classify-bump.sh:88-113
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Idempotency walk skips CHANGELOG commits but not larch-log refresh on HEAD After Step 8a with refresh-run-logs on top classify-bump may apply a second bump Extend bounded HEAD walk to skip log-refresh (and similar) commits before bump check
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: .claude/skills/bump-version/scripts/classify-bump.sh:88-113
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] No harness tests CHANGELOG-at-HEAD idempotency despite plan acceptance #6 Regression in classify walk could ship without direct signal Add minimal test-classify-bump.sh fixture for Bump+CHANGELOG(+optional log) stack
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: scripts/ship-pr.sh:512-534
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] commit-changelog failure after apply-bump is warn-only Re-bump can push new plugin.json while CHANGELOG heading still shows OLD_VERSION Document or emit execution-issue when COMMITTED=false after re-bump
- **Suggested revision**: Address the concern above.

### FINDING_6: correctness: .claude/skills/bump-version/scripts/classify-bump.sh:88-113
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Idempotency walk skips only Update CHANGELOG commits not chore(larch-logs) above bump HEAD=log flush HEAD~1=CHANGELOG HEAD~2=Bump then --resume-phase bump may classify again and apply second bump Extend transparent walk for larch-log subjects or forbid bump resume on that stack
- **Suggested revision**: Address the concern above.

### FINDING_7: correctness: scripts/ship-pr.sh:512-536
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] commit-changelog omits --replaces-version when drop-bump returned DROPPED=false Drop no-op plus apply-bump leaves duplicate CHANGELOG version headings Treat DROPPED=false as degraded or infer replaces-version without OLD_BUMP_SHA
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: scripts/implement-finalize.sh:563-623
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] write_changelog_entry --replaces-version is never called Dead duplicate logic versus commit-changelog awk Wire through write_changelog_entry or remove unused flag path
- **Suggested revision**: Address the concern above.

### FINDING_9: risk-integration: .claude/skills/bump-version/scripts/classify-bump.sh:199-211
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] No offline test for CHANGELOG-at-HEAD idempotency walk (plan acceptance #6) After separate CHANGELOG commits, classify-bump may return NONE when a new bump is needed or classify when HEAD is already bumped; resume path skips drop-bump and relies on classify-bump Add isolated-git harness with HEAD=CHANGELOG over bump (NONE) and HEAD=CHANGELOG over feature (non-NONE); wire into Makefile
- **Suggested revision**: Address the concern above.

### FINDING_10: risk-integration: scripts/test-ship-pr.sh:2346-2375
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Plan-required ship-pr-rrr-phase14 resume test with new commit shape not present rebump_changelog_commit_shape uses ci-initial only; phase14 resume still stubs bump/changelog helpers so resume+new-shape stall is unguarded Add phase14 scenario with real scripts, bump+CHANGELOG history, stall then --resume-phase ship-pr-rrr-phase14 asserting exit 0 and fresh commits
- **Suggested revision**: Address the concern above.

### FINDING_11: risk-integration: scripts/test-ship-pr.sh:3729-3741
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] phase14 rebump tests noop drop-bump-commit and commit-changelog Resume/stall contract passes while Guard 4 or replaces-version regressions on resume would not fail CI Use real drop-bump/commit-changelog in at least one phase14 resume case
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: docs/linting.md
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Missing harness table row for test-commit-changelog Operators may not discover make test-commit-changelog despite Makefile registration Add docs/linting.md row mirroring test-drop-bump-commit style
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: scripts/test-commit-changelog.sh:43-54
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Happy path does not assert COMMIT_SHA output Callers parsing COMMIT_SHA get no regression signal if emission breaks Add grep for non-empty COMMIT_SHA= in Test 1
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: scripts/implement-finalize.sh:563-583
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] write_changelog_entry --replaces-version is untested and unused on re-bump path Duplicate awk in commit-changelog.sh can diverge; stale-entry removal in implement-finalize path unverified Wire commit-changelog through write_changelog_entry or remove dead code and test the live path
- **Suggested revision**: Address the concern above.

### FINDING_15: security: .claude/skills/bump-version/scripts/classify-bump.sh:88-99
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Idempotency walk trusts CHANGELOG commit subjects without verifying CHANGELOG-only diffs. A contributor pushes a commit titled Update CHANGELOG for 9.9.9 that also modifies skills/** above an existing bump; classify-bump walks past it, returns BUMP_TYPE=NONE, and apply-bump is skipped while plugin-surface changes ship without a new version bump. Require git diff --name-only to equal CHANGELOG.md for each transparent commit before walking past it (same discipline as drop-bump-commit Guard 4).
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: scripts/ship-pr.sh:2474-2407
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Drop-bump is non-fatal and DROPPED is ignored; BUMP_TYPE=NONE skips apply and commit-changelog but still force-pushes. After drop-bump returns DROPPED=false, classify-bump returns NONE while a stale bump remains; ship-pr pushes without re-bump or CHANGELOG refresh—silent regression of the #2852 failure class without exit 4. Inspect DROPPED after drop; stall or retry when a bump-shaped commit remains; align shell Step 10/12 with bump-verification Block β hard-fail on zero new commits.
- **Suggested revision**: Address the concern above.

### FINDING_17: correctness: scripts/ship-pr.sh:512-533
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Re-bump CHANGELOG update relies only on --replaces-version retitle, not full entry composition. CHANGELOG rebase conflict resolved to upstream removes the old ## [X.Y.Z] heading; commit-changelog exits COMMITTED=false and ship-pr continues—merged PR may lack an entry for NEW_VERSION. Fallback to write_changelog_entry/maybe_update_changelog when replace fails, or fail closed on missing CHANGELOG commit before force-push.
- **Suggested revision**: Address the concern above.

### FINDING_18: correctness: scripts/commit-changelog.sh:79-115
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] --replaces-version cannot create a section when the old heading is missing. Same upstream-wins conflict path: no heading to retitle, no diff to commit, operator sees only a WARN in failure logs. On awk exit 3, insert a new ## [NEW] section via write_changelog_entry instead of no-op exit 0.
- **Suggested revision**: Address the concern above.

### FINDING_19: architecture: scripts/implement-finalize.sh:563-677
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Duplicate stale-entry logic: write_changelog_entry --replaces-version is unused; commit-changelog.sh has its own awk. Future edits to one path will not update the other, risking divergent CHANGELOG behavior between Step 8a and re-bump. Unify through one helper or delete the unused write_changelog_entry flag.
- **Suggested revision**: Address the concern above.

### FINDING_20: risk-integration: scripts/drop-bump-commit.sh:59
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] --max-depth 20 may be insufficient with doubled bump+CHANGELOG commits per CI loop. Long Step 12 CI history leaves bump beyond depth 20; DROPPED=false and the ship-pr silent-continue path above compound. Dynamic depth, explicit stall on exhaustion, or operator documentation to squash before merge.
- **Suggested revision**: Address the concern above.

### FINDING_21: correctness: .claude/skills/bump-version/scripts/classify-bump.sh:88-98
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Idempotency walk skips only CHANGELOG subjects (max 3), not log-flush commits. Rare malformed HEAD stacks could mis-classify; mitigated because ship-pr drops before classify. Extend walk patterns or document the cap in classify-bump.md.
- **Suggested revision**: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] code-quality: skills/implement/scripts/test-step-7a.md
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Harness markdown stale vs 21-case shell harness. Operator confusion when debugging Step 7a; tracked as #2862. Update test-step-7a.md in a docs-only follow-up.
- **Suggested revision**: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] code-quality: docs/linting.md
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Inventory row omits rebase-failure flush-skip note. Operators must read harness source for that edge. Add one sentence to the inventory row when touching linting docs.
- **Suggested revision**: Address the concern above.

### FINDING_24: correctness: scripts/commit-changelog.sh:79-115
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] --replaces-version uses a standalone retitle awk instead of delegating to write_changelog_entry as the plan required. write_changelog_entry's --replaces-version branch is dead; Step 8a full-section removal and re-bump retitle-only logic can diverge on stale CHANGELOG handling. Wire commit-changelog.sh to write_changelog_entry --replaces-version or extract one shared helper used by both paths.
- **Suggested revision**: Address the concern above.

### FINDING_25: correctness: scripts/test-ship-pr.sh:2346-2437
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Mandatory ship-pr-rrr-phase14 resume regression under the new commit shape is missing. Phase-14 resume can regress (stall, wrong drop depth, stale headings) while ci-initial rebump_changelog_commit_shape still passes. Add a phase14 stall+--resume-phase ship-pr-rrr-phase14 test with bump+CHANGELOG fixtures and content assertions.
- **Suggested revision**: Address the concern above.

### FINDING_26: architecture: docs/linting.md
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Missing harness inventory row for make test-commit-changelog. Operators and CI docs omit the new target despite Makefile registration. Add a test-commit-changelog row to the harness table per implement-finalize.md edit-in-sync.
- **Suggested revision**: Address the concern above.

### FINDING_27: correctness: scripts/test-implement-finalize.sh:2584-2593
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] test-implement-finalize does not assert separate CHANGELOG-over-bump commit shape. Acceptance #3 is only half-covered; regressions swapping back to amend could slip through finalize harness. Assert git log subjects/order in a happy-path postbump fixture with real commits.
- **Suggested revision**: Address the concern above.

### FINDING_28: [OUT_OF_SCOPE] architecture: scripts/ship-pr.sh:2437-2441
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] phase14 resume skips drop-bump and depends on persisted RRR_OLD_BUMP_VERSION. If state is lost between legs, --replaces-version may be omitted on resume. Document invariant or add resume-path test (see in-scope ship-pr finding).
- **Suggested revision**: Address the concern above.

### FINDING_29: [OUT_OF_SCOPE] correctness: .claude/skills/bump-version/scripts/classify-bump.sh:84-85
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Idempotency walk passes only CHANGELOG commits, not larch-log refresh commits. HEAD=log over CHANGELOG over bump intentionally triggers a fresh bump per comment; behavior predates this fix scope. No change unless plan expands transparent-commit walk to log commits.
- **Suggested revision**: Address the concern above.

