### [Plan Review] FINDING_10

### FINDING_10: Concurrent upgrade-larch runs can race across shared install, stamp, and prune state
- **Reviewer(s)**: Cursor-dyn-concurrent-prune-race, Codex-dyn-concurrent-prune-race
- **Severity**: important
- **Concern**: The plan leaves upgrade/prune un-serialized while mutating shared plugin state and version cache, allowing one runner to prune another runner’s in-flight unstamped target.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-concurrent-prune-race: Add a small portable shared mutex in skills/upgrade-larch/scripts/upgrade-larch.sh around the mutating install/stamp/prune path, using a lock under shared state such as $LARCH_CACHE_DIR/.upgrade-larch.lock.d with trap cleanup; after acquiring it, re-check the installed version or proceed serialized, and cover contention in test-upgrade-larch-prune.sh.
  - From Codex-dyn-concurrent-prune-race: Add a small portable shared mutex in skills/upgrade-larch/scripts/upgrade-larch.sh around the mutating install/stamp/prune path, using a lock under shared state such as $LARCH_CACHE_DIR/.upgrade-larch.lock.d with trap cleanup; after acquiring it, re-check the installed version or proceed serialized, and cover contention in test-upgrade-larch-prune.sh.

