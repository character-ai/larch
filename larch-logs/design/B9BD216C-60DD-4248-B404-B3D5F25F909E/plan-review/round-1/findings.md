### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/upgrade-larch/scripts/test-upgrade-larch.sh:245-309
- **Concern**: Plan treats test-upgrade-larch.sh as review-only, but it still asserts Stage-A and sanitize-failure prune behavior the plan removes. Scenario: After upgrade-larch.sh drops newer-than-stable sanitization and the sanitize-failure retention loop, cases prune-stray-newer-under-cap, preserve-verified-stable, prune-oldest-after-sanitize, and sanitize-failure-counts-toward-cap will fail even if test-upgrade-larch-prune.sh is rewritten
- **Proposed resolution**: Add an explicit UPDATED entry for test-upgrade-larch.sh: rewrite or drop Stage-A/sanitize cases and align remaining assertions with install-stamp keep-8 semantics (or fold coverage into test-upgrade-larch-prune.sh and trim duplicate cases)

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/test-implement-bootstrap.sh:102
- **Concern**: Plan updates nonexistent scripts/test-implement-bootstrap.sh while actual harness still copies deleted cache-touch helper. Scenario: Deleting scripts/lib-larch-cache-touch.sh leaves make test-implement-bootstrap failing when the harness tries to cp the removed file
- **Proposed resolution**: Retarget that plan item to skills/implement/scripts/test-implement-bootstrap.sh and remove the copy there

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-session-env-roundtrip.sh:13-17,268-409
- **Concern**: Plan says only the markdown contract needs touch-reference removal, but the shell harness still asserts mtime touch behavior. Scenario: After removing lib-larch-cache-touch.sh and its callers, test-session-env-roundtrip fails in sections F through H
- **Proposed resolution**: Remove or rewrite the F-H touch assertions in scripts/test-session-env-roundtrip.sh alongside the md update

### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/upgrade-larch/scripts/upgrade-larch.sh:277-385
- **Concern**: Proposed prune algorithm can violate the hard max-8 contract when ACTUAL_VERSION is outside the first eight. Scenario: Stamp write failure or bad fallback ordering can keep first eight plus ACTUAL_VERSION, leaving nine cached versions
- **Proposed resolution**: Build the keep set by seeding ACTUAL_VERSION first, then add newest entries until the set size is 8, and prune all others

### FINDING_5:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: Makefile:108-109; plan.txt:108-109
- **Concern**: New `test-cleanup` target has no `test-harnesses-N` shard assignment. Scenario: Adding only the recipe leaves `scripts/test-harness-shards-coverage.sh` failing `make lint` (orphan target) and the new age-based harness never runs in CI
- **Proposed resolution**: Add `test-cleanup` to exactly one `test-harnesses-N:` prerequisite list and to `.PHONY` alongside the recipe; rebalance per `docs/linting.md` if needed

### FINDING_6:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:16-18
- **Concern**: Keep-first-8 plus always-keep-target can exceed the hard cap. Scenario: If the install stamp write fails and the just-installed version sorts outside the first 8, the proposed prune can retain 9 dirs despite the max-8 contract
- **Proposed resolution**: Build the keep set as ACTUAL_VERSION plus newest remaining entries until size 8, or assign ACTUAL_VERSION an in-memory newest key before sorting

### FINDING_7:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: Makefile:78-129 agent-lint.toml:1415-1424 agent-lint.toml:1579-1582
- **Concern**: New and renamed harnesses are not fully wired into lint metadata. Scenario: After renaming test-keepalive-sentinel and adding skills/cleanup/scripts/test-cleanup.sh, make lint can either miss the new cleanup harness shard or agent-lint can flag Makefile-only harnesses as dead
- **Proposed resolution**: Update .PHONY, exactly one test-harnesses-N shard, and agent-lint.toml exclusions/comments for test-session-identity plus skills/cleanup/scripts/test-cleanup.{sh,md}

### FINDING_8:
- **Reviewer(s)**: Codex-Edge
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: docs/installation-and-setup.md:38-40 docs/configuration-and-permissions.md:162-289
- **Concern**: Canonical docs are left with the old prune contract and omit the new cleanup env var. Scenario: The shipped docs would still describe mtime touch, active-session pins, newer-than-stable deletion, and no LARCH_CLEANUP_RETENTION_DAYS contract
- **Proposed resolution**: Add docs/installation-and-setup.md to the upgrade doc updates and document LARCH_CLEANUP_RETENTION_DAYS in docs/configuration-and-permissions.md

### FINDING_9:
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-session-env-roundtrip.sh:13-17,268-409
- **Concern**: Plan removes cache-touch behavior but only updates the markdown contract; the shell harness still asserts the removed mtime refresh behavior. Scenario: make lint continues running test-session-env-roundtrip and fails after lib-larch-cache-touch.sh and its call sites are deleted
- **Proposed resolution**: Add scripts/test-session-env-roundtrip.sh to the plan and remove or rewrite sections F/G/H that assert numeric CLAUDE_PLUGIN_ROOT mtime touches

### FINDING_10:
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/upgrade-larch/scripts/upgrade-larch.sh:263-346
- **Concern**: Plan says max 8 is hard but also says always retain ACTUAL_VERSION after selecting the first 8, which can leave 9 retained entries if the target is not in the selected set. Scenario: A failed stamp write or reused old target dir can make ACTUAL_VERSION fall outside the first 8 by fallback mtime; preserving it after the first-8 selection violates the hard cap
- **Proposed resolution**: Build the retained set as ACTUAL_VERSION plus the newest remaining entries up to KEEP_VERSIONS-1, then prune everything else

### FINDING_11:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: Makefile:103;Makefile:192-193;plan.txt:108-109
- **Concern**: Makefile plan omits test-harnesses-N shard wiring for renamed and new targets. Scenario: Adding test-cleanup without assigning exactly one test-harnesses-N prerequisite and leaving test-keepalive-sentinel on test-harnesses-18 after rename makes test-harness-shards-coverage fail and skips the new harness in make lint
- **Proposed resolution**: In the Makefile section add: replace test-keepalive-sentinel with test-session-identity on test-harnesses-18; add test-cleanup to one shard; add both names to the .PHONY list

### FINDING_12:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/session-setup.sh:255-288; skills/implement/scripts/lib-resolve-implement-tmpdir.sh:47-65
- **Concern**: Renaming .larch-keepalive to .larch-session adds rollout risk without being required for age-based cleanup. Scenario: Existing in-flight session tmpdirs written before the PR only have .larch-keepalive, so a new resolver that only reads .larch-session can fail open and lose Stop/SessionStart binding during upgrade rollout
- **Proposed resolution**: Keep the filename stable and slim its contents, or make the resolver accept both names for a transition

### FINDING_13:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/upgrade-larch/scripts/upgrade-larch.sh:230-238
- **Concern**: Already-latest path exits before the proposed max-8 prune can run. Scenario: If larch is already at latest stable and the cache already has more than 8 version dirs, /upgrade-larch reports no-op and leaves the hard maximum violated
- **Proposed resolution**: Route the already-latest stable case through the same prune function before exiting, without reinstalling

### FINDING_14:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: agent-lint.toml:1416-1424
- **Concern**: Renamed session identity harness is not added to agent-lint exclusions. Scenario: The plan renames scripts/test-keepalive-sentinel.sh but leaves the Makefile-only harness exclusion on the old path, so make lint can fail on dead-script reachability for the new harness
- **Proposed resolution**: Update agent-lint.toml comments and excluded paths to scripts/test-session-identity.sh and scripts/test-session-identity.md

### FINDING_15:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: Makefile:4;Makefile:103;Makefile:108-109
- **Concern**: Plan adds `test-cleanup` and renames `test-keepalive-sentinel` but does not require shard/`.PHONY` wiring. Scenario: `scripts/test-harness-shards-coverage.sh` fails `make lint` when a new `test-*` recipe is not in any `test-harnesses-N` prerequisite, and `test-keepalive-sentinel` left on shard 18 after rename breaks the renamed target
- **Proposed resolution**: In the Makefile section, require: add `test-cleanup` to a `test-harnesses-N` line; replace `test-keepalive-sentinel` with `test-session-identity` on `test-harnesses-18` (and any other shard references); update the long `.PHONY` list accordingly

### FINDING_16:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/upgrade-larch/scripts/upgrade-larch.sh:281-382
- **Concern**: The prune plan requires both a hard maximum of 8 cached versions and unconditional retention of ACTUAL_VERSION, but the proposed keep-first-8 plus always-retain wording does not say how to keep the count at 8 when ACTUAL_VERSION falls outside the top 8 after stamp write failure or bad fallback ordering. Scenario: A failed install-stamp write can put the just-installed version outside the first 8 by fallback mtime; naive implementation keeps those 8 plus ACTUAL_VERSION, violating the hard max, or deletes ACTUAL_VERSION, violating the retention invariant
- **Proposed resolution**: Specify that ACTUAL_VERSION is forced into the retained set before deletion and, if that makes more than 8 retained entries, the oldest non-ACTUAL_VERSION retained entry is pruned; add a combined test for stamp-write failure or target-outside-top-8 that asserts exactly 8 remain and ACTUAL_VERSION remains

### FINDING_17:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: docs/configuration-and-permissions.md:189-197
- **Concern**: The plan adds LARCH_CLEANUP_RETENTION_DAYS but omits the repository's canonical env-var documentation. Scenario: Users and reviewers will not find the new cleanup retention override in the env-var/configuration reference, despite AGENTS.md naming this file as the env-var authority
- **Proposed resolution**: Add a short LARCH_CLEANUP_RETENTION_DAYS entry documenting default 7, positive-integer validation, and fallback behavior

### FINDING_18:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: code-quality
- **Location**: Makefile:66-68, agent-lint.toml:1413-1424
- **Concern**: The plan adds and renames Makefile-only harnesses but does not mention updating the test-harness shard list or agent-lint dead-script allowlist. Scenario: After renaming test-keepalive-sentinel to test-session-identity and adding skills/cleanup/scripts/test-cleanup.sh, make lint can fail shard coverage or dead-script checks even if the individual targets exist
- **Proposed resolution**: Update the relevant test-harnesses-N prerequisite line, replace the keepalive allowlist entries with session-identity entries, and add the new cleanup harness/sibling contract to agent-lint.toml if agent-lint cannot reach it through runtime references

### FINDING_19:
- **Reviewer(s)**: Cursor-dyn-symbol-sweep, Codex-dyn-symbol-sweep
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-implement-bootstrap.sh:100-105
- **Concern**: The plan lists nonexistent scripts/test-implement-bootstrap.sh, but the live harness that copies the deleted lib-larch-cache-touch.sh is skills/implement/scripts/test-implement-bootstrap.sh.. Scenario: After scripts/lib-larch-cache-touch.sh is deleted, make test-implement-bootstrap still copies the removed file from the real harness and fails before exercising the change.
- **Proposed resolution**: Change the plan entry to skills/implement/scripts/test-implement-bootstrap.sh and remove the cp "$REPO_ROOT/scripts/lib-larch-cache-touch.sh" sandbox line there.

### FINDING_20:
- **Reviewer(s)**: Cursor-dyn-symbol-sweep, Codex-dyn-symbol-sweep
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: agent-lint.toml:1413-1424
- **Concern**: agent-lint.toml is absent from the change list even though the plan renames scripts/test-keepalive-sentinel.{sh,md} and adds a Makefile-only cleanup harness.. Scenario: make lint can keep checking stale allowlist/comment entries for removed test-keepalive-sentinel paths and may flag the new skills/cleanup/scripts/test-cleanup.{sh,md} as unreferenced.
- **Proposed resolution**: Add agent-lint.toml to the plan; update the keepalive entries/comment to test-session-identity and add the new cleanup harness entries if agent-lint requires the same Makefile-only exception.

### FINDING_21:
- **Reviewer(s)**: Cursor-dyn-concurrent-prune-race, Codex-dyn-concurrent-prune-race
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:15-18; skills/upgrade-larch/scripts/upgrade-larch.sh:247-257,277-381
- **Concern**: The plan keeps upgrade/prune un-serialized while upgrade-larch mutates shared plugin state and the shared version cache. Scenario: Two concurrent /upgrade-larch runs from different worktrees can interleave uninstall/install/stamp/prune; one runner can prune while another has installed but not yet stamped, and the ACTUAL_VERSION guard only protects the current runner's target. Same-dir rm -rf races are mostly benign, but a different in-flight unstamped target can be treated as legacy mtime fallback and deleted by the other pruner.
- **Proposed resolution**: Add a small portable shared mutex in skills/upgrade-larch/scripts/upgrade-larch.sh around the mutating install/stamp/prune path, using a lock under shared state such as $LARCH_CACHE_DIR/.upgrade-larch.lock.d with trap cleanup; after acquiring it, re-check the installed version or proceed serialized, and cover contention in test-upgrade-larch-prune.sh.

### FINDING_22:
- **Reviewer(s)**: Cursor-dyn-md-contract-gaps, Codex-dyn-md-contract-gaps
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-session-env-roundtrip.md:25-33, scripts/test-session-env-roundtrip.sh:13-17,268-409
- **Concern**: Plan says to remove only two lib-larch-cache-touch.md references because the .sh harness does not assert touch behavior, but the current harness has full F/G/H mtime-refresh assertions and the md would still describe those guarantees after only two lines are removed. Scenario: After removing lib-larch-cache-touch.sh and the three touch calls, make test-session-env-roundtrip still expects numeric cache roots to be touched and fails; the sibling md also keeps stale mtime-refresh contracts
- **Proposed resolution**: Revise the plan to delete or rewrite sections F/G/H in both scripts/test-session-env-roundtrip.sh and scripts/test-session-env-roundtrip.md, keeping only CLAUDE_PLUGIN_ROOT validation and persistence coverage that still applies

### FINDING_23:
- **Reviewer(s)**: Cursor-dyn-md-contract-gaps, Codex-dyn-md-contract-gaps
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: docs/configuration-and-permissions.md:156-263
- **Concern**: The plan introduces LARCH_CLEANUP_RETENTION_DAYS but does not add it to the canonical environment-variable documentation. Scenario: Operators can set an invalid retention value without finding the documented positive-integer/default-7/fallback-warning contract in the repo's env-var reference
- **Proposed resolution**: Add docs/configuration-and-permissions.md to the plan with a minimal LARCH_CLEANUP_RETENTION_DAYS entry covering default 7, positive integer validation, and invalid-value fallback warning

### FINDING_24:
- **Reviewer(s)**: Cursor-dyn-md-contract-gaps, Codex-dyn-md-contract-gaps
- **Severity**: latent
- **Focus area**: correctness
- **Location**: docs/installation-and-setup.md:38-40
- **Concern**: The plan rewrites upgrade pruning but omits the canonical upgrade docs that still promise newer-than-stable deletion, most-recently-touched retention, mtime touch protection, and session-env pins. Scenario: After the PR lands, installation docs will contradict the proposed max-8 install-stamp pruning contract and removed active-protection guarantees
- **Proposed resolution**: Add docs/installation-and-setup.md to the plan and replace the old prune paragraph with the install-stamp path, newest-first fallback ordering, max-8 cap, just-installed retention, and removal of session pins/mtime touch guarantees
