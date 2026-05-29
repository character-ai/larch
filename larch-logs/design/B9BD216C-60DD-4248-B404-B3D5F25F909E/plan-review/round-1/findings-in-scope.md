### FINDING_1: Stale upgrade-larch tests still assert removed prune behavior
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: `test-upgrade-larch.sh` is treated as review-only even though it still asserts Stage-A and sanitize-failure prune behavior that the plan removes, so those cases will fail after the prune rewrite.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an explicit UPDATED entry for test-upgrade-larch.sh: rewrite or drop Stage-A/sanitize cases and align remaining assertions with install-stamp keep-8 semantics (or fold coverage into test-upgrade-larch-prune.sh and trim duplicate cases)

### FINDING_2: Implement bootstrap harness path is wrong and still copies deleted helper
- **Reviewer(s)**: Codex-Arch, Cursor-dyn-symbol-sweep, Codex-dyn-symbol-sweep
- **Severity**: important
- **Concern**: The plan references nonexistent `scripts/test-implement-bootstrap.sh`; the real harness under `skills/implement/scripts/` still copies `scripts/lib-larch-cache-touch.sh`, so deleting that helper will break the bootstrap test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Retarget that plan item to skills/implement/scripts/test-implement-bootstrap.sh and remove the copy there
  - From Cursor-dyn-symbol-sweep: Change the plan entry to skills/implement/scripts/test-implement-bootstrap.sh and remove the cp "$REPO_ROOT/scripts/lib-larch-cache-touch.sh" sandbox line there.
  - From Codex-dyn-symbol-sweep: Change the plan entry to skills/implement/scripts/test-implement-bootstrap.sh and remove the cp "$REPO_ROOT/scripts/lib-larch-cache-touch.sh" sandbox line there.

### FINDING_3: Session env roundtrip harness and contract still assert cache-touch behavior
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-dyn-md-contract-gaps, Codex-dyn-md-contract-gaps
- **Severity**: important
- **Concern**: The plan removes cache-touch behavior but only updates limited markdown references; `scripts/test-session-env-roundtrip.sh` still asserts F/G/H mtime refresh behavior, and the sibling markdown contract can remain stale.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Remove or rewrite the F-H touch assertions in scripts/test-session-env-roundtrip.sh alongside the md update
  - From Cursor-Innovation: Add scripts/test-session-env-roundtrip.sh to the plan and remove or rewrite sections F/G/H that assert numeric CLAUDE_PLUGIN_ROOT mtime touches
  - From Codex-Innovation: Add scripts/test-session-env-roundtrip.sh to the plan and remove or rewrite sections F/G/H that assert numeric CLAUDE_PLUGIN_ROOT mtime touches
  - From Cursor-dyn-md-contract-gaps: Revise the plan to delete or rewrite sections F/G/H in both scripts/test-session-env-roundtrip.sh and scripts/test-session-env-roundtrip.md, keeping only CLAUDE_PLUGIN_ROOT validation and persistence coverage that still applies
  - From Codex-dyn-md-contract-gaps: Revise the plan to delete or rewrite sections F/G/H in both scripts/test-session-env-roundtrip.sh and scripts/test-session-env-roundtrip.md, keeping only CLAUDE_PLUGIN_ROOT validation and persistence coverage that still applies

### FINDING_4: Prune keep set can exceed hard max of 8 when ACTUAL_VERSION is outside selected entries
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Cursor-Innovation, Codex-Innovation, Codex-Requirements
- **Severity**: important
- **Concern**: The proposed prune wording combines “keep first 8” with unconditional ACTUAL_VERSION retention, which can leave 9 cached versions when the target is outside the first 8 after stamp failure or fallback ordering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Build the keep set by seeding ACTUAL_VERSION first, then add newest entries until the set size is 8, and prune all others
  - From Codex-Edge: Build the keep set as ACTUAL_VERSION plus newest remaining entries until size 8, or assign ACTUAL_VERSION an in-memory newest key before sorting
  - From Cursor-Innovation: Build the retained set as ACTUAL_VERSION plus the newest remaining entries up to KEEP_VERSIONS-1, then prune everything else
  - From Codex-Innovation: Build the retained set as ACTUAL_VERSION plus the newest remaining entries up to KEEP_VERSIONS-1, then prune everything else
  - From Codex-Requirements: Specify that ACTUAL_VERSION is forced into the retained set before deletion and, if that makes more than 8 retained entries, the oldest non-ACTUAL_VERSION retained entry is pruned; add a combined test for stamp-write failure or target-outside-top-8 that asserts exactly 8 remain and ACTUAL_VERSION remains

### FINDING_5: New and renamed Makefile test targets are not fully wired into shards and .PHONY
- **Reviewer(s)**: Cursor-Edge, Codex-Edge, Cursor-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: The plan adds `test-cleanup` and renames `test-keepalive-sentinel` but omits complete `test-harnesses-N` shard and `.PHONY` wiring, so `make lint` can fail shard coverage or skip the new harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Add `test-cleanup` to exactly one `test-harnesses-N:` prerequisite list and to `.PHONY` alongside the recipe; rebalance per `docs/linting.md` if needed
  - From Codex-Edge: Update .PHONY, exactly one test-harnesses-N shard, and agent-lint.toml exclusions/comments for test-session-identity plus skills/cleanup/scripts/test-cleanup.{sh,md}
  - From Cursor-Pragmatic: In the Makefile section add: replace test-keepalive-sentinel with test-session-identity on test-harnesses-18; add test-cleanup to one shard; add both names to the .PHONY list
  - From Cursor-Requirements: In the Makefile section, require: add `test-cleanup` to a `test-harnesses-N` line; replace `test-keepalive-sentinel` with `test-session-identity` on `test-harnesses-18` (and any other shard references); update the long `.PHONY` list accordingly
  - From Codex-Requirements: Update the relevant test-harnesses-N prerequisite line, replace the keepalive allowlist entries with session-identity entries, and add the new cleanup harness/sibling contract to agent-lint.toml if agent-lint cannot reach it through runtime references

### FINDING_6: agent-lint metadata is stale for renamed and new Makefile-only harnesses
- **Reviewer(s)**: Codex-Edge, Codex-Pragmatic, Codex-Requirements, Cursor-dyn-symbol-sweep, Codex-dyn-symbol-sweep
- **Severity**: important
- **Concern**: The plan renames `test-keepalive-sentinel` and adds a cleanup harness without updating `agent-lint.toml` exclusions/comments, so dead-script reachability checks can fail or keep stale allowlist entries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Update .PHONY, exactly one test-harnesses-N shard, and agent-lint.toml exclusions/comments for test-session-identity plus skills/cleanup/scripts/test-cleanup.{sh,md}
  - From Codex-Pragmatic: Update agent-lint.toml comments and excluded paths to scripts/test-session-identity.sh and scripts/test-session-identity.md
  - From Codex-Requirements: Update the relevant test-harnesses-N prerequisite line, replace the keepalive allowlist entries with session-identity entries, and add the new cleanup harness/sibling contract to agent-lint.toml if agent-lint cannot reach it through runtime references
  - From Cursor-dyn-symbol-sweep: Add agent-lint.toml to the plan; update the keepalive entries/comment to test-session-identity and add the new cleanup harness entries if agent-lint requires the same Makefile-only exception.
  - From Codex-dyn-symbol-sweep: Add agent-lint.toml to the plan; update the keepalive entries/comment to test-session-identity and add the new cleanup harness entries if agent-lint requires the same Makefile-only exception.

### FINDING_7: Canonical docs are missing new cleanup retention and changed prune contract
- **Reviewer(s)**: Codex-Edge, Codex-Requirements, Cursor-dyn-md-contract-gaps, Codex-dyn-md-contract-gaps
- **Severity**: important
- **Concern**: The plan changes cleanup retention and upgrade pruning but leaves canonical docs stale, including the env-var reference and installation docs that still describe old mtime/session-pin/newer-than-stable behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Add docs/installation-and-setup.md to the upgrade doc updates and document LARCH_CLEANUP_RETENTION_DAYS in docs/configuration-and-permissions.md
  - From Codex-Requirements: Add a short LARCH_CLEANUP_RETENTION_DAYS entry documenting default 7, positive-integer validation, and fallback behavior
  - From Cursor-dyn-md-contract-gaps: Add docs/configuration-and-permissions.md to the plan with a minimal LARCH_CLEANUP_RETENTION_DAYS entry covering default 7, positive integer validation, and invalid-value fallback warning
  - From Codex-dyn-md-contract-gaps: Add docs/configuration-and-permissions.md to the plan with a minimal LARCH_CLEANUP_RETENTION_DAYS entry covering default 7, positive integer validation, and invalid-value fallback warning
  - From Cursor-dyn-md-contract-gaps: Add docs/installation-and-setup.md to the plan and replace the old prune paragraph with the install-stamp path, newest-first fallback ordering, max-8 cap, just-installed retention, and removal of session pins/mtime touch guarantees
  - From Codex-dyn-md-contract-gaps: Add docs/installation-and-setup.md to the plan and replace the old prune paragraph with the install-stamp path, newest-first fallback ordering, max-8 cap, just-installed retention, and removal of session pins/mtime touch guarantees

### FINDING_8: Renaming session sentinel risks breaking in-flight tmpdir resolution
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: Renaming `.larch-keepalive` to `.larch-session` adds rollout risk because existing in-flight session tmpdirs only have the old file, and a resolver that only reads the new name can lose Stop/SessionStart binding.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Keep the filename stable and slim its contents, or make the resolver accept both names for a transition

### FINDING_9: Already-latest upgrade path can skip prune and leave cache over cap
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: The already-latest stable path exits before the proposed max-8 prune runs, so an existing cache with more than 8 version dirs remains in violation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Route the already-latest stable case through the same prune function before exiting, without reinstalling

### FINDING_10: Concurrent upgrade-larch runs can race across shared install, stamp, and prune state
- **Reviewer(s)**: Cursor-dyn-concurrent-prune-race, Codex-dyn-concurrent-prune-race
- **Severity**: important
- **Concern**: The plan leaves upgrade/prune un-serialized while mutating shared plugin state and version cache, allowing one runner to prune another runner’s in-flight unstamped target.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-concurrent-prune-race: Add a small portable shared mutex in skills/upgrade-larch/scripts/upgrade-larch.sh around the mutating install/stamp/prune path, using a lock under shared state such as $LARCH_CACHE_DIR/.upgrade-larch.lock.d with trap cleanup; after acquiring it, re-check the installed version or proceed serialized, and cover contention in test-upgrade-larch-prune.sh.
  - From Codex-dyn-concurrent-prune-race: Add a small portable shared mutex in skills/upgrade-larch/scripts/upgrade-larch.sh around the mutating install/stamp/prune path, using a lock under shared state such as $LARCH_CACHE_DIR/.upgrade-larch.lock.d with trap cleanup; after acquiring it, re-check the installed version or proceed serialized, and cover contention in test-upgrade-larch-prune.sh.
