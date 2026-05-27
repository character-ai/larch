### FINDING_1:
- **Reviewer(s)**: Cursor-Arch, Codex-Edge, Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/upgrade-larch/scripts/upgrade-larch.sh:24-39
- **Concern**: Proposed stat_mtime tries BSD stat -f before GNU stat -c and only checks non-empty output. Scenario: On Linux GNU stat treats -f as --file-system; multi-line non-numeric output can be accepted as mtime and break sort -k1,1n cap-trim order
- **Proposed resolution**: Mirror scripts/lib-external-launcher-common.sh:103-106 — try stat -c %Y then stat -f %m; accept only when value matches ^[0-9]+$; else fall through to 0

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md:127-169
- **Concern**: FINDING_1: mtime refresh is wired only through write-session-env.sh but /design session boot does not use that writer. Scenario: Design Step 0 runs session-setup.sh without --write-session-env and then writes CLAUDE_PLUGIN_ROOT through write-design-current-env.sh, so a user who actively uses an older cached plugin only via /design will not refresh that cache dir mtime and /upgrade-larch can still prune it as stale
- **Proposed resolution**: Put the refresh in a common session-boot path such as session-setup.sh, or factor a shared helper invoked by both write-session-env.sh and write-design-current-env.sh; add coverage for the /design writer/session path

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: scripts/write-session-env.sh:136-152
- **Concern**: FINDING_2: proposed touch placement mutates cache state before all writer inputs are validated. Scenario: The plan inserts touch immediately after CLAUDE_PLUGIN_ROOT validation but before --dynamic-archetypes validation; an invalid writer invocation can still mark a plugin version as recently used even though session-env writing fails
- **Proposed resolution**: Move the mtime refresh after every validation block and preferably after a successful session-env write, or centralize it in a validated session-setup helper

### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh:331-346
- **Concern**: FINDING_3: the proposed mtime eviction test is masked by the newer-than-stable prune branch. Scenario: The plan's mtime-asc-evicts-oldest-touched fixture uses cached 42.0.1 through 42.0.9 with INSTALL_RESULT_VERSION=42.0.5; verified prune removes 42.0.6 through 42.0.9 as newer than LATEST_STABLE before cap trimming, so evicting 42.0.9 would not prove mtime-based cap behavior
- **Proposed resolution**: Use a latest/install version above every fixture cache entry, for example install 42.0.10 with cached 42.0.1 through 42.0.9, then set 42.0.9 oldest and assert cap trimming removes it while retaining 42.0.1

### FINDING_5:
- **Reviewer(s)**: Codex-Arch
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/upgrade-larch/scripts/upgrade-larch.sh:102-113
- **Concern**: FINDING_4: proposed tie-breaker contract relies on stable sort but the planned command is not stable. Scenario: The new test description says equal-mtime entries use cache iteration order, but the planned helper uses sort -k1,1n; standard sort can apply a last-resort full-line comparison unless -s is used, so ties may resolve by version text instead of traversal order
- **Proposed resolution**: Either use sort -s -k1,1n and document the traversal order, or drop deterministic tie-break assertions and test only that equal-second mtimes keep the cache within the cap

### FINDING_6:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/write-session-env.sh:136-145 (proposed)
- **Concern**: Decision 3 "session boot" mtime refresh is wired only to write-session-env.sh, which runs on /implement Step 0 (implement-bootstrap.sh:330), not on Claude SessionStart. Scenario: hooks/hooks.json:58-68 runs sessionstart-health.sh only; /design Step 0 calls write-design-current-env.sh (skills/design/SKILL.md:158-169) without write-session-env; /review and /research call session-setup.sh without --write-session-env (scripts/session-setup.sh:471). A user who runs Claude daily on a cached version but only uses /design, /review, /research, or chat without /implement never refreshes that cache dir's mtime, so /upgrade-larch can still evict the version they actually use
- **Proposed resolution**: Add the same best-effort touch to write-design-current-env.sh after CLAUDE_PLUGIN_ROOT validation, and/or a tiny SessionStart hook (or extend sessionstart-health.sh) that touches the executing numeric cache root; align upgrade-larch.md wording with the real trigger surfaces

### FINDING_7:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh:123-219
- **Concern**: The proposed mtime-asc-evicts-oldest-touched fixture cannot exercise cap pruning as written. Scenario: If INSTALL_RESULT_VERSION is 42.0.5, verification requires LATEST_STABLE=42.0.5, so 42.0.6 through 42.0.9 are removed by the newer-than-stable branch before the cap-trim loop; if LATEST_STABLE is higher, verification fails and prune is skipped
- **Proposed resolution**: Make all fixture versions <= LATEST_STABLE and set INSTALL_RESULT_VERSION to that stable version, e.g. stable/install 42.0.9, make 42.0.8 the oldest mtime and 42.0.1 newest, then assert cap trim evicts 42.0.8 while retaining 42.0.1

### FINDING_8:
- **Reviewer(s)**: Codex-Edge
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/upgrade-larch/scripts/upgrade-larch.sh:102-112
- **Concern**: The planned equal-mtime tiebreaker test relies on sort stability that the implementation does not request. Scenario: sort -k1,1n without -s may fall back to comparing the full line for equal keys, so eviction on equal mtimes follows version text or platform behavior rather than cache iteration order; the proposed mtime-tiebreaker-uses-cache-order case can fail or encode a false contract
- **Proposed resolution**: Either add sort -s -k1,1n and document cache/glob order as the tiebreaker, or remove the cache-order assertion and test only the accepted contract that equal-mtime eviction is unspecified but remains capped and safe

### FINDING_9:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/upgrade-larch/scripts/upgrade-larch.sh:22-40
- **Concern**: Proposed `stat_mtime` tries BSD `stat -f '%m'` before GNU `stat -c '%Y'` with only a non-empty check. Scenario: On Linux (CI / primary harness lane), GNU `stat -f` enters filesystem-info mode and can emit non-numeric stdout; `list_cached_versions_by_mtime` then ranks cache dirs incorrectly or unpredictably (see `skills/implement/scripts/lib-resolve-implement-tmpdir.sh:73-83`)
- **Proposed resolution**: Mirror repo convention: GNU first, then BSD, require `^[0-9]+$` before accepting output (as in `scripts/check-reviewers.sh:93-97`)

### FINDING_10:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/review/SKILL.md:24-28; skills/research/SKILL.md:120-126; skills/design/SKILL.md:115-130
- **Concern**: The plan puts the mtime refresh only in write-session-env.sh, but several standalone session boots run session-setup without --write-session-env or use write-design-current-env.sh.. Scenario: Active users of /review, /research, or /design will not refresh the executing cache dir mtime, so a regularly used version can still age out and be pruned once no live session pin exists.
- **Proposed resolution**: Move the touch into a shared session-boot path such as session-setup.sh, or a small helper invoked by session-setup.sh plus write-design-current-env.sh/write-session-env.sh; add a test for session-setup without --write-session-env.

### FINDING_11:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/upgrade-larch/scripts/upgrade-larch.sh:290-309
- **Concern**: The proposed mtime-asc-evicts-oldest-touched test uses INSTALL_RESULT_VERSION=42.0.5 while cache contains 42.0.6 through 42.0.9, so the newer-than-LATEST_STABLE branch removes 42.0.9 before the cap trim.. Scenario: The test can pass even if cap pruning is still semver-based, because 42.0.9 is removed for being newer than stable rather than oldest by mtime.
- **Proposed resolution**: Set the verified stable/install version above all seeded cache versions, or seed only versions <= LATEST_STABLE, then assert the removal comes from the cap loop and would fail under semver ordering.

### FINDING_12:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: latent
- **Focus area**: security
- **Location**: SECURITY.md:171-175; docs/installation-and-setup.md:38-40
- **Concern**: The plan changes prune trust/retention semantics and adds a filesystem touch side effect, but omits SECURITY.md and the user-facing installation docs from the update set.. Scenario: The shipped trust model will still describe only session-env parsing, and user docs will not explain mtime retention or the session-start touch behavior.
- **Proposed resolution**: Update SECURITY.md to document mtime as a same-UID local signal and the bounded touch behavior; update docs/installation-and-setup.md to state that cap pruning keeps the most recently touched cache dirs.

### FINDING_13:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/session-setup.sh:469-506, skills/design/SKILL.md:127-130
- **Concern**: Mtime refresh is wired only to write-session-env.sh, but several session starts do not call that writer. Scenario: /design and /review run session-setup without --write-session-env, and /design writes via write-design-current-env.sh, so a version actively used only through those flows keeps an old cache mtime and can still be cap-pruned after sessions end
- **Proposed resolution**: Move the best-effort numeric-basename touch to the common session-start path in session-setup.sh, or share a helper and call it from write-session-env.sh plus write-design-current-env.sh and review setup paths; add coverage for a session-setup path that does not write session-env

### FINDING_14:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh:331-345
- **Concern**: Proposed mtime-asc test verifies 42.0.5 while cache includes 42.0.6 through 42.0.9. Scenario: The prune code first removes every version newer than LATEST_STABLE, so 42.0.9 would be removed by the newer-than-stable branch rather than by mtime cap trimming; a semver-trim regression could still pass the test
- **Proposed resolution**: Make the verified install target higher than all mtime candidates, for example install 42.0.10 and seed 42.0.9 as oldest, then assert the high-but-not-newer candidate is pruned while the low-but-recent candidate survives

### FINDING_15:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: skills/upgrade-larch/scripts/upgrade-larch.sh:102-113
- **Concern**: The proposed tie-breaker test expects cache iteration order, but the proposed helper uses sort -k1,1n without stable sorting. Scenario: Equal-mtime entries can be reordered by sort's fallback comparison, making the test encode accidental platform behavior or fail despite acceptable production behavior
- **Proposed resolution**: Drop the deterministic tie-breaker assertion, or make the implementation explicit with stable sorting such as sort -s -k1,1n and document the intended secondary behavior before testing it

### FINDING_16:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: docs/installation-and-setup.md:40
- **Concern**: Plan omits user-facing install doc despite edit-in-sync on upgrade-larch.md and test-upgrade-larch-prune.md. Scenario: Operators still read semver-ordered "prune older cached versions" wording after mtime-based retention lands
- **Proposed resolution**: Add docs/installation-and-setup.md to Files to modify: state cap-trim evicts oldest cache-dir mtime first and that write-session-env.sh refreshes mtime on session boot for numeric cache roots

### FINDING_17:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:117-120
- **Concern**: Missing required idempotency validation for mtime stability. Scenario: The Round 1 harness constraint requires covering idempotency where /upgrade-larch runs without changing install state, but the plan only adds mtime eviction/stat tests and relies on existing idempotent-installed coverage that does not assert cache mtimes remain unchanged
- **Proposed resolution**: Add a test case, likely in skills/upgrade-larch/scripts/test-upgrade-larch.sh, that seeds the executing cache dir mtime, runs the already-at-latest path, and asserts no install/prune occurs and the cache dir mtime is unchanged

### FINDING_18:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:116-118
- **Concern**: The plan leaves existing prune fixtures relying on mkdir-created mtimes instead of deterministic mtime seeding. Scenario: Round 1 explicitly required existing version-asc assumptions to be updated with deterministic mtimes; mkdir loops can produce same-second mtimes, so those cases may keep passing due version tie behavior rather than validating mtime-based retention
- **Proposed resolution**: Update affected existing cases such as cap-prune-trims-to-eight, multi-pinned-oldest-still-trims-to-eight, and cap-prune-rm-failure-skips-retry to set explicit touch -t mtimes matching the intended retention story

### FINDING_19:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: latent
- **Focus area**: correctness
- **Location**: plan.txt:119-145
- **Concern**: The planned mtime tie-breaker test conflicts with the stated edge-case contract. Scenario: The plan says ties are indeterminate and acceptable, but also proposes mtime-tiebreaker-uses-cache-order; the helper uses sort -k1,1n without stable mode, so equal-mtime rows are not guaranteed to preserve iteration order across platforms
- **Proposed resolution**: Either drop the deterministic tie-breaker test and document ties as intentionally unspecified, or make the implementation deterministic with stable sort or an explicit secondary key and test that contract

### FINDING_20:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:171
- **Concern**: The plan adds a write side effect to CLAUDE_PLUGIN_ROOT handling but does not update SECURITY.md. Scenario: scripts/write-session-env.sh changes from only persisting LARCH_CLAUDE_PLUGIN_ROOT to touching a filesystem path derived from CLAUDE_PLUGIN_ROOT; the repo instructions require SECURITY.md updates for security-relevant behavior changes and the current trust-model text would become incomplete
- **Proposed resolution**: Add SECURITY.md coverage for the best-effort numeric-basename touch, its trusted environment assumptions, its no-source/no-eval boundary, and failure behavior alongside the existing Plugin-root rehydration section

### FINDING_21:
- **Reviewer(s)**: Cursor-dyn-test-fixture-version-boundary
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/upgrade-larch/scripts/upgrade-larch.sh:190-197,290-309
- **Concern**: Proposed `mtime-asc-evicts-oldest-touched` pairs nine cache dirs `42.0.1`–`42.0.9` with `INSTALL_RESULT_VERSION=42.0.5` but does not set `GH_OUTPUT`; stub `gh` makes the first release line `LATEST_STABLE`. If `GH_OUTPUT` is `42.0.5` (natural pairing), the first-pass loop removes every cached version `version_gt` `42.0.5` (`42.0.6`–`42.0.9`) before `VERSION_COUNT` reaches the cap-trim block at 312, leaving at most five dirs and never exercising mtime-ordered cap eviction. Asserting `42.0.9` was removed would pass for the wrong reason (newer-than-stable purge, not mtime trim).. Scenario: Mtime regression test false-green or fails unpredictably depending on implied `GH_OUTPUT`; core #2958 behavior untested.
- **Proposed resolution**: Mirror `cap-prune-trims-to-eight` (`test-upgrade-larch-prune.sh:331-346`): seed `42.0.1`–`42.0.9`, set `GH_OUTPUT=$'42.0.10\n'`, `INSTALL_RESULT_VERSION=42.0.10`, and assert two cap evictions with `42.0.9` (oldest mtime) removed while `42.0.1` (newest mtime) remains.

### FINDING_22:
- **Reviewer(s)**: Codex-dyn-test-fixture-version-boundary
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:118; skills/upgrade-larch/scripts/upgrade-larch.sh:190-197,243-247,290-312; skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh:96-103
- **Concern**: The proposed mtime-asc fixture can only verify pruning if GH_OUTPUT resolves LATEST_STABLE to the installed version, but with INSTALL_RESULT_VERSION=42.0.5 that makes 42.0.6-42.0.9 newer-than-stable and they are removed before cap trimming. Scenario: The cache starts with 42.0.1-42.0.9. To get VERIFIED_TARGET=true, GH_OUTPUT must list 42.0.5 first because the stub returns INSTALL_RESULT_VERSION as installed. The first prune pass then drops all versions greater than 42.0.5, leaving only 42.0.1-42.0.5 so VERSION_COUNT is 5 and the KEEP_LIMIT=8 loop is never exercised
- **Proposed resolution**: Change the test to install a fresh latest stable such as 42.0.10 and set GH_OUTPUT to 42.0.10, with the initial cache at 42.0.1-42.0.9. Then all ten entries survive newer-than-stable sanitization and cap trim must evict by mtime

### FINDING_23:
- **Reviewer(s)**: Codex-dyn-test-fixture-version-boundary
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:118; skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh:80-83
- **Concern**: The plan assumes installing 42.0.5 makes an existing cache directory newest-by-mtime, but the test stub only runs mkdir -p for install and does not touch existing directories. Scenario: If 42.0.5 already exists, mkdir -p is a no-op for that directory's mtime, so the intended mtime ordering is not produced and the assertion would not prove install-created recency
- **Proposed resolution**: Use a freshly-created install target such as 42.0.10 or change the stub/test setup to explicitly touch the installed directory, but prefer the fresh 42.0.10 fixture because it also avoids the newer-than-stable pre-prune issue

### FINDING_24:
- **Reviewer(s)**: Cursor-dyn-stat-stub-completeness
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:120-121; skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh:107-121
- **Concern**: stat-fallback-mtime-zero requires a PATH stat stub but the plan does not define write_stub_stat and says to reuse write_stub_* as-is. Scenario: Implementer has no spec for the only reliable way to force both stat_mtime branches to fail for one cache dir; the case is underspecified relative to the existing write_stub_rm pattern
- **Proposed resolution**: Add write_stub_stat (mirror write_stub_rm: target="${*: -1}", STAT_FAIL_VERSION env, fail exit 1 when target matches */$STAT_FAIL_VERSION and argv is mtime extraction with -f or -c, else exec /usr/bin/stat "$@"); call it from run_case; pass STAT_FAIL_VERSION in the upgrade-larch.sh invocation env like RM_FAIL_VERSION

### FINDING_25:
- **Reviewer(s)**: Codex-dyn-stat-stub-completeness
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:114-121; skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh:107-142
- **Concern**: Plan requires a stat failure stub but does not specify write_stub_stat or wire it into the harness. Scenario: Current harness only writes claude gh and rm stubs; the proposed stat-fallback-mtime-zero case cannot deliberately fail both stat -f '%m' -- <path> and stat -c '%Y' -- <path> for one cache dir while allowing unrelated stat calls through
- **Proposed resolution**: Add a concrete write_stub_stat helper, call it from run_case, pass STAT_FAIL_VERSION or similar through the SCRIPT environment, and have the stub inspect the final target argument, fail only for that version, and exec a captured real stat binary for all other invocations

### FINDING_26:
- **Reviewer(s)**: Cursor-dyn-mtime-sort-secondary-key
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/upgrade-larch/scripts/upgrade-larch.sh (proposed list_cached_versions_by_mtime)
- **Concern**: Production sort is only `sort -k1,1n`; plan defers tied-mtime determinism to unstable BSD sort on macOS (plan.txt:118-119) while adding `mtime-tiebreaker-uses-cache-order`. Scenario: Equal-mtime pairs sort arbitrarily on macOS; a strict tiebreaker assertion flakes in `make test-upgrade-larch-prune` on the primary dev platform
- **Proposed resolution**: Change proposed pipeline to `sort -k1,1n -k2,2` (mtime then lexicographic version basename); drop reliance on GNU stable sort / BSD `-s`

### FINDING_27:
- **Reviewer(s)**: Codex-dyn-mtime-sort-secondary-key
- **Severity**: latent
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:56,119,145; skills/upgrade-larch/scripts/upgrade-larch.sh:102-113; skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh:146-148,331-387
- **Concern**: Plan leaves equal-mtime ordering to sort -k1,1n while adding a tiebreaker test that expects cache-order stability. Scenario: The proposed mtime-tiebreaker-uses-cache-order case can be flaky on macOS when cache dirs share the same mtime second; the plan has no macOS skip or loosened assertion, and existing fixtures create dirs in a tight loop where second-level mtimes can collide
- **Proposed resolution**: Add a deterministic secondary key such as sort -k1,1n -k2,2 and update the tiebreaker test to assert lexicographic version-name tie order, or explicitly skip/loosen that test on platforms without stable equal-key ordering
