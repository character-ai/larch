### FINDING_1: stat_mtime accepts GNU filesystem output
- **Reviewer(s)**: Cursor-Arch, Codex-Edge, Cursor-Pragmatic, Cursor-Innovation
- **Severity**: important
- **Concern**: The proposed `stat_mtime` probes BSD `stat -f` before GNU `stat -c` and accepts any non-empty output, so GNU/Linux can treat `-f` as filesystem-info mode and feed non-numeric text into mtime sorting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Codex-Edge, Cursor-Pragmatic: Mirror scripts/lib-external-launcher-common.sh:103-106 — try stat -c %Y then stat -f %m; accept only when value matches ^[0-9]+$; else fall through to 0
  - From Cursor-Innovation: Mirror repo convention: GNU first, then BSD, require `^[0-9]+$` before accepting output (as in `scripts/check-reviewers.sh:93-97`)

### FINDING_2: mtime refresh misses non-implement session paths
- **Reviewer(s)**: Codex-Arch, Cursor-Edge, Codex-Innovation, Codex-Pragmatic
- **Severity**: important
- **Concern**: Wiring the cache mtime refresh only through `write-session-env.sh` misses session starts that call `session-setup.sh` without `--write-session-env`, use `write-design-current-env.sh`, or only run `/design`, `/review`, `/research`, or chat. Active cache versions can therefore still age out and be pruned.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Put the refresh in a common session-boot path such as session-setup.sh, or factor a shared helper invoked by both write-session-env.sh and write-design-current-env.sh; add coverage for the /design writer/session path
  - From Cursor-Edge: Add the same best-effort touch to write-design-current-env.sh after CLAUDE_PLUGIN_ROOT validation, and/or a tiny SessionStart hook (or extend sessionstart-health.sh) that touches the executing numeric cache root; align upgrade-larch.md wording with the real trigger surfaces
  - From Codex-Innovation: Move the touch into a shared session-boot path such as session-setup.sh, or a small helper invoked by session-setup.sh plus write-design-current-env.sh/write-session-env.sh; add a test for session-setup without --write-session-env.
  - From Codex-Pragmatic: Move the best-effort numeric-basename touch to the common session-start path in session-setup.sh, or share a helper and call it from write-session-env.sh plus write-design-current-env.sh and review setup paths; add coverage for a session-setup path that does not write session-env

### FINDING_3: mtime refresh can happen before validation failure
- **Reviewer(s)**: Codex-Arch
- **Severity**: latent
- **Concern**: The proposed touch placement can mark a cache version as recently used before all writer inputs are validated, so failed invocations can still mutate cache retention state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Move the mtime refresh after every validation block and preferably after a successful session-env write, or centralize it in a validated session-setup helper

### FINDING_4: mtime cap-prune test is masked by newer-than-stable pruning
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Codex-Innovation, Codex-Pragmatic, Cursor-dyn-test-fixture-version-boundary, Codex-dyn-test-fixture-version-boundary
- **Severity**: important
- **Concern**: The proposed `mtime-asc-evicts-oldest-touched` fixture seeds versions newer than the verified stable/install version, so the newer-than-stable prune pass removes the target entries before cap trimming can exercise mtime ordering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Use a latest/install version above every fixture cache entry, for example install 42.0.10 with cached 42.0.1 through 42.0.9, then set 42.0.9 oldest and assert cap trimming removes it while retaining 42.0.1
  - From Codex-Edge: Make all fixture versions <= LATEST_STABLE and set INSTALL_RESULT_VERSION to that stable version, e.g. stable/install 42.0.9, make 42.0.8 the oldest mtime and 42.0.1 newest, then assert cap trim evicts 42.0.8 while retaining 42.0.1
  - From Codex-Innovation: Set the verified stable/install version above all seeded cache versions, or seed only versions <= LATEST_STABLE, then assert the removal comes from the cap loop and would fail under semver ordering.
  - From Codex-Pragmatic: Make the verified install target higher than all mtime candidates, for example install 42.0.10 and seed 42.0.9 as oldest, then assert the high-but-not-newer candidate is pruned while the low-but-recent candidate survives
  - From Cursor-dyn-test-fixture-version-boundary: Mirror `cap-prune-trims-to-eight` (`test-upgrade-larch-prune.sh:331-346`): seed `42.0.1`–`42.0.9`, set `GH_OUTPUT=$'42.0.10\n'`, `INSTALL_RESULT_VERSION=42.0.10`, and assert two cap evictions with `42.0.9` (oldest mtime) removed while `42.0.1` (newest mtime) remains.
  - From Codex-dyn-test-fixture-version-boundary: Change the test to install a fresh latest stable such as 42.0.10 and set GH_OUTPUT to 42.0.10, with the initial cache at 42.0.1-42.0.9. Then all ten entries survive newer-than-stable sanitization and cap trim must evict by mtime

### FINDING_5: equal-mtime tiebreaker contract is not implemented
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Codex-Pragmatic, Codex-Requirements, Cursor-dyn-mtime-sort-secondary-key, Codex-dyn-mtime-sort-secondary-key
- **Severity**: important
- **Concern**: The plan adds or describes deterministic equal-mtime behavior, but `sort -k1,1n` does not guarantee cache iteration order for equal keys. Tests that assert stable tie ordering can be flaky or encode platform-specific behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Either use sort -s -k1,1n and document the traversal order, or drop deterministic tie-break assertions and test only that equal-second mtimes keep the cache within the cap
  - From Codex-Edge: Either add sort -s -k1,1n and document cache/glob order as the tiebreaker, or remove the cache-order assertion and test only the accepted contract that equal-mtime eviction is unspecified but remains capped and safe
  - From Codex-Pragmatic: Drop the deterministic tie-breaker assertion, or make the implementation explicit with stable sorting such as sort -s -k1,1n and document the intended secondary behavior before testing it
  - From Codex-Requirements: Either drop the deterministic tie-breaker test and document ties as intentionally unspecified, or make the implementation deterministic with stable sort or an explicit secondary key and test that contract
  - From Cursor-dyn-mtime-sort-secondary-key: Change proposed pipeline to `sort -k1,1n -k2,2` (mtime then lexicographic version basename); drop reliance on GNU stable sort / BSD `-s`
  - From Codex-dyn-mtime-sort-secondary-key: Add a deterministic secondary key such as sort -k1,1n -k2,2 and update the tiebreaker test to assert lexicographic version-name tie order, or explicitly skip/loosen that test on platforms without stable equal-key ordering

### FINDING_6: security and install docs omit new mtime retention semantics
- **Reviewer(s)**: Codex-Innovation, Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: The plan changes cache retention behavior and adds a filesystem touch side effect, but does not update the security model and user-facing installation documentation accordingly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Update SECURITY.md to document mtime as a same-UID local signal and the bounded touch behavior; update docs/installation-and-setup.md to state that cap pruning keeps the most recently touched cache dirs.
  - From Cursor-Requirements: Add docs/installation-and-setup.md to Files to modify: state cap-trim evicts oldest cache-dir mtime first and that write-session-env.sh refreshes mtime on session boot for numeric cache roots
  - From Codex-Requirements: Add SECURITY.md coverage for the best-effort numeric-basename touch, its trusted environment assumptions, its no-source/no-eval boundary, and failure behavior alongside the existing Plugin-root rehydration section

### FINDING_7: missing idempotency validation for unchanged mtimes
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The plan does not add the required idempotency test showing that an already-at-latest `/upgrade-larch` run leaves cache mtimes unchanged when install state does not change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add a test case, likely in skills/upgrade-larch/scripts/test-upgrade-larch.sh, that seeds the executing cache dir mtime, runs the already-at-latest path, and asserts no install/prune occurs and the cache dir mtime is unchanged

### FINDING_8: existing prune fixtures keep nondeterministic mkdir mtimes
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: Existing prune fixtures still rely on directory creation time instead of explicit mtime seeding, so same-second mtimes can let tests pass for the wrong ordering behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Update affected existing cases such as cap-prune-trims-to-eight, multi-pinned-oldest-still-trims-to-eight, and cap-prune-rm-failure-skips-retry to set explicit touch -t mtimes matching the intended retention story

### FINDING_9: mtime fixture assumes mkdir refreshes an existing install dir
- **Reviewer(s)**: Codex-dyn-test-fixture-version-boundary
- **Severity**: important
- **Concern**: The proposed test assumes installing an already-existing cache version refreshes that directory's mtime, but the stub uses `mkdir -p`, which is a no-op for existing directory mtimes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-test-fixture-version-boundary: Use a freshly-created install target such as 42.0.10 or change the stub/test setup to explicitly touch the installed directory, but prefer the fresh 42.0.10 fixture because it also avoids the newer-than-stable pre-prune issue

### FINDING_10: stat failure test lacks a stat stub design
- **Reviewer(s)**: Cursor-dyn-stat-stub-completeness, Codex-dyn-stat-stub-completeness
- **Severity**: important
- **Concern**: The proposed `stat-fallback-mtime-zero` coverage requires forcing both stat branches to fail for one cache directory, but the plan does not define or wire a `stat` PATH stub into the prune harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-stat-stub-completeness: Add write_stub_stat (mirror write_stub_rm: target="${*: -1}", STAT_FAIL_VERSION env, fail exit 1 when target matches */$STAT_FAIL_VERSION and argv is mtime extraction with -f or -c, else exec /usr/bin/stat "$@"); call it from run_case; pass STAT_FAIL_VERSION in the upgrade-larch.sh invocation env like RM_FAIL_VERSION
  - From Codex-dyn-stat-stub-completeness: Add a concrete write_stub_stat helper, call it from run_case, pass STAT_FAIL_VERSION or similar through the SCRIPT environment, and have the stub inspect the final target argument, fail only for that version, and exec a captured real stat binary for all other invocations
