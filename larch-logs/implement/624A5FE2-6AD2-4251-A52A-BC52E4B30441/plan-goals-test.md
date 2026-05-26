## Goal
Fix ship-pr.sh stall at force-push-gate when CHANGELOG.md is in the bump commit by separating CHANGELOG into its own commit and adding --allow-changelog-only flag to drop-bump-commit.sh

## Implementation Plan
## Plan

# Plan — fix #2852: ship-pr.sh exits 4 (stall) at force-push-gate when CHANGELOG.md is in the bump commit

## Approach

The user chose a **hybrid** fix in Step 1c/1d:

- **Primary (Option 2)**: refactor CHANGELOG.md updates to land as a SEPARATE commit instead of being amended into the preceding bump commit. The bump commit stays `plugin.json`-only across all of implement's lifecycle.
- **Secondary defense (Option 1, gated)**: add a `--allow-changelog-only` opt-in flag to `scripts/drop-bump-commit.sh`. When set, accept a bump-pattern commit whose diff is exactly `CHANGELOG.md`.

### Where the drop-bump-commit / amend calls actually live (corrected)

Plan review (FINDINGs 11, 15, 16, 19, 26, 29, 31, 34, 35, 38, 39, 40) corrected a major gap in my original plan: the active Step 10/12 rebase + re-bump path is NOT the Markdown sub-procedure; it lives in `scripts/ship-pr.sh` `run_rebase_rebump()` and `_run_rebase_rebump_from_step3()`. The Markdown sub-procedure is only reached from Step 8b. The fix must touch BOTH paths.

Per FINDING_37, the original bug body's reference to "force-push-gate" is misleading post-#2707 — that gate no longer calls drop-bump-commit directly. The actual drop-bump call sites are:

1. `scripts/ship-pr.sh:2434-2439` (line range approximate; pin by symbol `run_rebase_rebump`) — Step 10/12 path.
2. `skills/implement/references/rebase-rebump-subprocedure.md` step 1 — Step 8b path (Markdown orchestration; the actual Bash call site is in the prompt-side orchestrator).

Both must receive `--allow-changelog-only` from the new caller flag and must call `commit-changelog.sh` after `apply-bump.sh` instead of the current amend pattern.

### New helper: `scripts/commit-changelog.sh`

Creates a separate commit with subject `Update CHANGELOG for <version>`. Implementation:

- Use the repo's `scripts/git-commit.sh` primitive (FINDING_12) — `scripts/git-commit.sh -m "Update CHANGELOG for $version" --only CHANGELOG.md` (with the `--only` flag scoping to CHANGELOG.md if the primitive supports it; otherwise a tightly-scoped `git add CHANGELOG.md && git commit -m "..."` wrapped in the primitive's trailer policy).
- Clean-tree check uses `git status --porcelain --untracked-files=no` (FINDING_7) — parity with `drop-bump-commit.sh` Guard 1.
- The clean-tree check tolerates an unstaged or staged change to `CHANGELOG.md` (since that is what we are about to commit); any other dirty tracked file fails the script (`COMMITTED=false`, `ERROR=...`).
- Accept `--version <X.Y.Z>` (required, semver-validated).
- Emit `COMMITTED=true|false` and `COMMIT_SHA=<sha>` on stdout. Exit 0 on success or expected no-op (no CHANGELOG.md change to commit), 1 on error.

The subject `Update CHANGELOG for <version>` is INTENTIONALLY distinct from `Bump version to <version>` so `drop-bump-commit.sh`'s Guard 2 regex never matches a CHANGELOG commit.

### drop-bump-commit `--allow-changelog-only` semantics

Add a `--allow-changelog-only` flag parsed alongside `--max-depth`. When set, inside Guard 4 (both default path and `LARCH_BUMP_FILES` custom path): if `CHANGED_FILES` is exactly `CHANGELOG.md` (single-file diff) AND Guard 2's subject regex matched, accept the commit as droppable. The flag is OFF by default — Tests 4 and 15 (CHANGELOG-only rejected) keep passing.

### classify-bump idempotency fix

FINDING_20: `classify-bump.sh` HEAD-only idempotency check assumes HEAD is the bump. After the refactor, HEAD may be `Update CHANGELOG for <version>` instead. Update `classify-bump.sh` to walk past any commit whose subject matches `^Update CHANGELOG for [0-9]+\.[0-9]+\.[0-9]+$` when checking for an existing bump at HEAD. The walk is bounded (1-3 commits) and only treats the new CHANGELOG-commit subject as transparent.

### HEAD ordering with refresh-run-logs interleaving

FINDINGs 41, 42: `scripts/refresh-run-logs.sh` commits between the bump and the next operation in some paths. The actual history shapes after a `commit-changelog.sh` may be:

- Step 8a (initial bump): HEAD = `Update CHANGELOG for X.Y.Z`, HEAD~1 = `Bump version to X.Y.Z`, HEAD~2 = pre-bump-base.
- Step 8a with intervening log refresh: HEAD = `Update CHANGELOG ...`, HEAD~1 = `chore(larch-logs): ...`, HEAD~2 = `Bump version ...`.
- Step 10/12 (`run_rebase_rebump`): refresh-run-logs runs after re-bump; HEAD = `chore(larch-logs): ...`, HEAD~1 = `Update CHANGELOG ...`, HEAD~2 = `Bump version ...`. (Or with the commit-changelog call inserted before refresh-run-logs, the order is HEAD = `Update CHANGELOG ...`, HEAD~1 = `Bump version ...`, then refresh-run-logs adds one on top.)

`drop-bump-commit.sh`'s existing walk-back search (default `--max-depth 10`) handles `FOUND_AT >= 1` correctly via `git rebase --onto`. The plan tests both `FOUND_AT=1` (HEAD=CHANGELOG over Bump) and `FOUND_AT=2` (HEAD=log-refresh over CHANGELOG over Bump) walk-back shapes (FINDINGs 9, 22).

For the latent depth-exhaustion edge case (FINDING_42 — after ~10 CI fix commits, the bump can fall past `--max-depth 10`), bump the default invocation in `ship-pr.sh run_rebase_rebump` and the Markdown sub-procedure step 1 to `--max-depth 20` (the script already supports the flag; ship-pr.sh just needs to pass it). Standalone callers retain the default 10.

### CHANGELOG content management across CI iterations

FINDING_25: when Step 12 CI loops re-bump from X.Y.Z to X.Y.(Z+1), the prior iteration's `Update CHANGELOG for X.Y.Z` commit is replayed by drop-bump-commit's `git rebase --onto`. Its CHANGELOG.md content (the `## [X.Y.Z]` entry) persists; the new iteration's `maybe_update_changelog` inserts `## [X.Y.(Z+1)]` ABOVE the stale `## [X.Y.Z]` entry. Both entries survive into the merged history, but only one version was actually released.

**Resolution**: enhance `write_changelog_entry` in `scripts/implement-finalize.sh` to optionally remove a stale entry. Add a `--replaces-version <X.Y.Z>` flag to `commit-changelog.sh`; when present, pass it through to the awk in `write_changelog_entry` so the entry for `<X.Y.Z>` is dropped before the new entry is composed. Callers determine the stale version from `drop-bump-commit.sh`'s `OLD_BUMP_SHA` (parse the commit subject via `git log -1 --format=%s <sha>` for the version). The flag is optional — Step 8a (initial bump) does NOT pass it; only re-bump callers (sub-procedure step 4a, ship-pr.sh `run_rebase_rebump`) pass it after extracting the version from the dropped commit.

### History accumulation tradeoff (documented, mitigated for stale CHANGELOG entries)

After the refactor, each Step 12 CI iteration adds two commits (bump + CHANGELOG) where today it adds one. drop-bump-commit handles the deeper walk-back via `git rebase --onto`. With `--replaces-version` removing stale entries, the merged CHANGELOG.md contains only the final-version entry. Git history still shows the intermediate `Update CHANGELOG for X.Y.Z` commits, but their CHANGELOG.md effect is overridden by the next iteration's `--replaces-version` removal. Operators may squash before merge if desired.

### conflict-resolution.md trivial-file class

FINDING_17: `skills/implement/references/conflict-resolution.md` does NOT currently list `CHANGELOG.md` as a trivial-file class. Add it so Phase 1's trivial-file recovery handles `CHANGELOG.md` conflicts during rebase (consistent with the existing `plugin.json`-trivial behavior). This makes the `commit-changelog.sh` commit safely replayable under Phase 1–4 recovery.

### Force-push-gate clarification (FINDING_37)

The original bug body mentions a "second drop-bump-commit.sh call inside force-push-gate" but post-#2707 the force-push-gate phase only calls `check-remote-branch.sh` and `git-force-push.sh`; it does NOT call `drop-bump-commit.sh`. The reported failure trace from issue #2852 was almost certainly recorded against an earlier code state. The fix targets the still-extant drop-bump-commit call sites (sub-procedure step 1 + `ship-pr.sh run_rebase_rebump`), not force-push-gate directly. Acknowledge this in the sub-procedure prose so future readers do not chase a phantom call.

## Files to modify/create

### NEW: `scripts/commit-changelog.sh`

Shell primitive that creates a CHANGELOG-only commit with subject `Update CHANGELOG for <version>`. Uses `scripts/git-commit.sh` for trailer/scoping consistency (FINDING_12). Clean-tree check uses `--untracked-files=no` (FINDING_7). Accepts `--version <X.Y.Z>` (required) and `--replaces-version <X.Y.Z>` (optional, for CI re-bump iterations — passed through to the CHANGELOG writer to strip the stale entry).

### NEW: `scripts/commit-changelog.md`

Sibling doc per `.claude/rules/script-md-siblings.md`. Documents purpose, primary callers (Step 8a `maybe_update_changelog`, sub-procedure step 4a, `ship-pr.sh run_rebase_rebump`), invariants ("subject MUST NOT match bump pattern", `--replaces-version` semantics), edit-in-sync with `drop-bump-commit.md`, `implement-finalize.md`, `rebase-rebump-subprocedure.md`, and `conflict-resolution.md`.

### NEW: `scripts/test-commit-changelog.sh`

Offline regression harness in the style of `test-drop-bump-commit.sh`: isolated `git init` temp repos. Covers: happy path (COMMITTED=true, subject byte-exact `Update CHANGELOG for X.Y.Z`); skipped no-change path (CHANGELOG.md not modified); error paths (missing file, dirty non-CHANGELOG, invalid version); `--replaces-version` removes prior-iteration entry without adding empty lines; clean-tree check passes despite an untracked file (parity with drop-bump-commit Guard 1).

### NEW: `scripts/test-commit-changelog.md`

Sibling stub naming the harness primary (`commit-changelog.sh`).

### UPDATED: `scripts/drop-bump-commit.sh`

1. Add `--allow-changelog-only` flag parsing alongside `--max-depth` (boolean, default false).
2. Inside Guard 4 (both default path and `LARCH_BUMP_FILES` custom path), when the flag is set: if `CHANGED_FILES` is exactly the single line `CHANGELOG.md` AND Guard 2's subject regex matched, accept the commit as droppable.
3. Preserve all Guard 1/2/3 behavior, all `WARN: ...` stderr lines, the `DROPPED=true|false` output contract, exit codes, and the existing walk-back / `git rebase --onto` drop mechanism.

### UPDATED: `scripts/drop-bump-commit.md`

Document the new `--allow-changelog-only` flag under Guard 4. Clarify the gating contract: off by default; Guard 2's subject regex still applies; LARCH_BUMP_FILES + CHANGELOG.md-only is also gated by the flag. Add an Edit-in-sync entry referencing `commit-changelog.md`. Update OOS_2's concern (conflict-resolution.md trivial-files cross-reference) into the edit-in-sync list.

### UPDATED: `scripts/test-drop-bump-commit.sh`

Add new tests AFTER existing Test 20 (NOT 15 — the original plan was wrong about the highest existing test number per FINDINGs 1/14/18):

- Test 21 (default path): CHANGELOG.md-only diff + bump subject + `--allow-changelog-only` → DROPPED=true.
- Test 22 (default path): CHANGELOG.md-only diff + bump subject + NO flag → DROPPED=false (existing invariant preserved).
- Test 23 (custom path, `LARCH_BUMP_FILES=version.go`): CHANGELOG.md-only diff + bump subject + `--allow-changelog-only` → DROPPED=true.
- Test 24 (default path): CHANGELOG.md-only diff + NON-bump subject + `--allow-changelog-only` → DROPPED=false (Guard 2 subject regex still rejects).
- Test 25 (default path): HEAD = `Update CHANGELOG for X.Y.Z` (CHANGELOG.md-only, non-bump subject), HEAD~1 = bump (plugin.json-only); walk-back finds bump at FOUND_AT=1 and drops it; new HEAD = CHANGELOG commit (FINDING_9).
- Test 26 (default path): HEAD = log-refresh (non-bump, non-CHANGELOG subject), HEAD~1 = `Update CHANGELOG ...`, HEAD~2 = bump; walk-back finds bump at FOUND_AT=2 (FINDING_22 + FINDING_41 interleaved shape).

Tests 1-20 unchanged.

### UPDATED: `scripts/implement-finalize.sh`

1. In `maybe_update_changelog()` (Step 8a Phase 2), replace `out=$("$SCRIPT_DIR/git-amend-add.sh" CHANGELOG.md 2>&1)` (line ~761) with `out=$("$SCRIPT_DIR/commit-changelog.sh" --version "$new_version" 2>&1)`. Step 8a is the INITIAL bump; no `--replaces-version` passed here.
2. Rename error-handling envelope strings (FINDING_10): `Step 8a changelog amend failed` → `Step 8a changelog commit failed`; `Step 8a changelog remained dirty after amend` → `Step 8a changelog remained dirty after commit`; the `**⚠ Step 8a: changelog amend failed.**` warn line → `**⚠ Step 8a: changelog commit failed.**` (preserves operator log clarity).
3. Optional refinement: `write_changelog_entry` accepts a new `--replaces-version <X.Y.Z>` parameter that the awk uses to skip the entry for the named version. Default behavior unchanged. Step 8a does NOT use this flag; only the new `commit-changelog.sh` (invoked from re-bump callers) passes it through.

### UPDATED: `scripts/implement-finalize.md`

Update Phase 2 description to note that the CHANGELOG update is now committed as a SEPARATE commit on top of the bump commit, not amended into it. Document the new `commit-changelog.sh` primary-caller relationship. Update Edit-in-sync to cross-reference `commit-changelog.md`. Note that error strings reference "commit" (not "amend") per the renaming.

### UPDATED: `scripts/ship-pr.sh`

1. `run_rebase_rebump()` (around the function body `scripts/ship-pr.sh:2274-2387`, pinned by function name not line):
   - Drop-bump invocation: pass `--allow-changelog-only --max-depth 20` (the `--max-depth` raise addresses FINDING_42's latent depth exhaustion under 10+ CI fix attempts).
   - After `apply-bump.sh` succeeds and emits `APPLIED=true COMMIT_SHA=<sha>`, capture `OLD_BUMP_SHA` from the prior `drop-bump-commit.sh` invocation, extract the prior version via `git log -1 --format=%s "$OLD_BUMP_SHA" | sed 's/^Bump version to //'`, and invoke `${CLAUDE_PLUGIN_ROOT}/scripts/commit-changelog.sh --version "$NEW_VERSION" --replaces-version "$OLD_VERSION"`. Treat `COMMITTED=false` as non-fatal (best-effort; mirrors the existing maybe_update_changelog tolerance).
   - This addresses FINDINGs 11, 15, 16, 19, 26, 29, 31, 34, 35, 38, 39, 40.
2. `_run_rebase_rebump_from_step3()` (the supporting helper, same file): apply the same two changes (drop-bump flags, commit-changelog call). FINDING_15 explicitly identifies this helper.
3. Acknowledge in a comment near the drop-bump call that the `--allow-changelog-only` flag is intentionally enabled here as defense-in-depth (the primary fix makes CHANGELOG-only bump commits impossible-by-construction in the happy path).

### UPDATED: `scripts/ship-pr.md`

Document the new `run_rebase_rebump` / `_run_rebase_rebump_from_step3` shape (drop-bump flags + commit-changelog call). Update Edit-in-sync to require touching `commit-changelog.md`, `drop-bump-commit.md`, and `rebase-rebump-subprocedure.md` together with any behavioral change to the rebase-rebump path.

### UPDATED: `scripts/test-ship-pr.sh`

Add a new test case (REQUIRED per FINDING_32; the original plan's "optional" wording is dropped) exercising `ship-pr.sh --resume-phase ship-pr-rrr-phase14` (or equivalent Step 10/12 entrypoint) under the new commit shape: simulated bump + CHANGELOG commits, drop-bump-commit walk-back finds bump at HEAD~1, the script proceeds without stall, the resulting branch contains a fresh bump + fresh CHANGELOG with the stale-entry removed from CHANGELOG.md content.

### UPDATED: `scripts/test-implement-finalize.sh`

Add a `commit-changelog.sh` stub in the sandbox setup alongside the existing `git-amend-add.sh` stub (FINDINGs 4, 27, 33, 36). The stub mirrors the new helper's contract (emit `COMMITTED=true COMMIT_SHA=<sha>` and return 0; or `COMMITTED=false ERROR=...` and return 1 in failure-injection tests). Update any existing assertions that reference `git-amend-add.sh` error semantics to reference `commit-changelog.sh` semantics (FINDING_33).

### UPDATED: `skills/implement/scripts/test-step-8a-changelog.sh`

Add a `commit-changelog.sh` stub alongside the existing `git-amend-add.sh` stub (FINDINGs 3, 13, 23, 36). Same contract as `test-implement-finalize.sh`. Update assertions to validate the new commit boundary (subject `Update CHANGELOG for X.Y.Z`, separate from the bump commit).

### UPDATED: `skills/implement/references/rebase-rebump-subprocedure.md`

1. Rewrite step 4a body. Replace `... amend the bump commit via ${CLAUDE_PLUGIN_ROOT}/scripts/git-amend-add.sh CHANGELOG.md.` with `... commit the CHANGELOG entry as a separate commit via ${CLAUDE_PLUGIN_ROOT}/scripts/commit-changelog.sh --version "$NEW_VERSION" --replaces-version "$OLD_VERSION". $OLD_VERSION is parsed from the dropped bump commit's subject via $(git log -1 --format=%s "$OLD_BUMP_SHA" | sed 's/^Bump version to //').`
2. Update step 1's `drop-bump-commit.sh` invocation to pass `--allow-changelog-only --max-depth 20`.
3. Add a note acknowledging that `scripts/ship-pr.sh run_rebase_rebump` is the parallel shell implementation of this sub-procedure for Step 10/12 and the same behavioral updates apply there.
4. Add a note clarifying that the original bug body's "force-push-gate" reference is post-#2707 misleading (FINDING_37); the actual drop-bump call sites are this sub-procedure's step 1 and `ship-pr.sh run_rebase_rebump`.

### UPDATED: `skills/implement/references/bump-verification.md`

Update Block β where it describes the shape of the bump commit. Note that the bump commit is now `plugin.json`-only and `CHANGELOG.md` may appear as a separate commit at HEAD with subject `Update CHANGELOG for <version>`. No semantic change to `check-bump-version.sh` (commit-delta counting is unaffected because the new CHANGELOG commit is a non-bump commit by Guard 2 regex; the existing post-check counter still works as today).

### UPDATED: `skills/implement/references/conflict-resolution.md`

Add `CHANGELOG.md` to the Phase 1 trivial-file class so rebase conflicts on the new separate CHANGELOG commit are auto-resolved by the `ours` policy (FINDING_17). The Phase 1 logic operates on file paths, not commit subjects, so the addition is direct.

### UPDATED: `skills/implement/SKILL.md`

Update Step 8 / 8a prose where it references CHANGELOG amend semantics (FINDING_8). Replace `amend` references with `commit` where the prose describes the post-bump CHANGELOG update. Cross-reference the new `commit-changelog.sh` primitive. The script-md-siblings rule's `paths:` covers this file.

### UPDATED: `.claude/skills/bump-version/scripts/classify-bump.sh`

Fix the HEAD-only idempotency check (FINDING_20) so a CHANGELOG-at-HEAD does not cause double-classify. Specifically: when checking for an existing bump at HEAD, walk past commits whose subject matches `^Update CHANGELOG for [0-9]+\.[0-9]+\.[0-9]+$` (bounded walk of 1-3 commits) before treating HEAD as "not-yet-bumped". This is a narrow change; the script's other code paths are untouched.

### UPDATED: `.claude/skills/bump-version/scripts/classify-bump.md`

Document the CHANGELOG-walk-past behavior under the idempotency section. Add edit-in-sync entries referencing `commit-changelog.md` and the new commit shape. Address OOS_1 by noting that drop-bump's walk-back semantics interoperate with the new shape (the existing apply-bump.md note at lines 40-41 may need a parallel update).

### UPDATED: `scripts/git-amend-add.sh`

Update the header comment: remove CHANGELOG references from the primary-callers list. If no remaining callers exist after the refactor, annotate the script as `currently no callers; retained for future amend use cases` rather than deleting (risk-averse per Round 1).

### UPDATED: `scripts/git-amend-add.md`

Strike the CHANGELOG-related primary-callers prose. Update Edit-in-sync to remove the `implement-finalize.sh` Step 8a and `rebase-rebump-subprocedure.md` step 4a references.

### UPDATED: `docs/configuration-and-permissions.md`

In the `LARCH_BUMP_FILES` section, add a short note that the new `--allow-changelog-only` flag in `drop-bump-commit.sh` is independent of `LARCH_BUMP_FILES` (the flag gates CHANGELOG-only acceptance; LARCH_BUMP_FILES gates the configured-bump-file set).

### UPDATED: `agent-lint.toml`

Add allowlist entries for the new script family (FINDINGs 5, 24, 28): `commit-changelog.sh`, `commit-changelog.md`, `test-commit-changelog.sh`, `test-commit-changelog.md`. Mirror the pattern already used for `drop-bump-commit.sh` and its harness.

### UPDATED: `Makefile`

Register a new `test-commit-changelog` target. Wire it into BOTH the `test-harnesses` aggregate AND the specific `test-harnesses-N` shard that covers `test-drop-bump-commit` so shard coverage stays balanced (FINDING_6). Verify with `make test-harness-shards-coverage`.

### UPDATED: `CHANGELOG.md`

A new entry for the next version bump under `## [Unreleased]` summarizing the fix. The `/implement` workflow's Step 8a (now `commit-changelog.sh`) writes this entry automatically.

## Edge cases

- **No CHANGELOG.md in repo**: `check-changelog-present.sh` returns false; Step 8a sets `CHANGELOG_STATUS=skipped-absent` and never calls `commit-changelog.sh`. Sub-procedure step 4a's existing Read-check skips the same way. ship-pr.sh's `run_rebase_rebump` should also skip when CHANGELOG.md is absent.
- **Empty bump or apply-bump no-op**: with Option 2, the bump commit (plugin.json-only) cannot be confused with a CHANGELOG-only commit. With `--allow-changelog-only` set from the sub-procedure / ship-pr.sh, even if the bug recurs due to apply-bump no-op, drop-bump succeeds.
- **No bullets / fallback CHANGELOG entry**: existing `maybe_update_changelog` fallback to `Closed: #<issue>` continues to work; `commit-changelog.sh` does not care about content, only that CHANGELOG.md was modified.
- **Pre-fix in-flight branches**: branches with legacy amended bump commits (plugin.json + CHANGELOG.md) hit the existing Guard 4 default path that already allows that two-file shape. Tests 2, 6, 14 keep passing. Backwards compatible.
- **Standalone `drop-bump-commit.sh` invocation**: operators calling the script directly without `--allow-changelog-only` see no behavior change. Tests 4, 15 (CHANGELOG-only rejected) keep passing.
- **CHANGELOG commit subject collision**: subject `Update CHANGELOG for <version>` never matches `^Bump version to ...$`; drop-bump-commit's Guard 2 search will skip it and continue walking back.
- **HEAD ordering with refresh-run-logs**: per FINDING_41, history can be HEAD=CHANGELOG / HEAD~1=Bump (Step 8a, no intervening log refresh) OR HEAD=CHANGELOG / HEAD~1=log-refresh / HEAD~2=Bump (with refresh) OR HEAD=log-refresh / HEAD~1=CHANGELOG / HEAD~2=Bump (Step 10/12 with refresh after re-bump). drop-bump-commit's existing walk-back handles all three within `--max-depth 20` (raised from default 10). Tests 25, 26 cover the explicit two-commit and three-commit shapes.
- **CI-iteration depth exhaustion**: per FINDING_42, with `ci-decide.sh` allowing up to ~10 fix attempts plus log commits, the bump can fall past depth 10. Mitigated by passing `--max-depth 20` from `ship-pr.sh run_rebase_rebump` and from the Markdown sub-procedure step 1.
- **classify-bump HEAD-only check**: per FINDING_20, when HEAD is a CHANGELOG commit, classify-bump walks past it (bounded 1-3 commits) so the existing idempotency invariant holds for the new shape.
- **conflict during CHANGELOG commit replay**: per FINDING_17, adding `CHANGELOG.md` to `conflict-resolution.md` Phase 1 trivial-files lets the `ours` policy auto-resolve any conflict on the CHANGELOG commit during a rebase. Without this addition, CHANGELOG conflicts would escalate to user resolution.

## Failure modes

1. **CHANGELOG conflict during rebase becomes more frequent**: today CHANGELOG.md changes are absorbed into the bump commit. After the refactor, both the bump commit and the separate CHANGELOG commit can encounter conflicts. **Mitigation**: add `CHANGELOG.md` to `conflict-resolution.md` Phase 1 trivial-file class (FINDING_17) so the `ours` policy auto-resolves. Earliest warning signal: `rebase-push.sh --no-push --keep-on-conflict` emitting CONFLICT_FILES that includes `CHANGELOG.md` AFTER the bump-only conflict resolved.

2. **drop-bump-commit's `--allow-changelog-only` accidentally drops a legitimate non-bump CHANGELOG commit**: extremely low risk because Guard 2's subject regex `^Bump version to [0-9]+\.[0-9]+\.[0-9]+$` is strict. The new `commit-changelog.sh` deliberately uses a different subject (`Update CHANGELOG for ...`) that never matches Guard 2. **Mitigation**: keep the flag off-by-default; only the sub-procedure and `ship-pr.sh run_rebase_rebump` pass it; document in `drop-bump-commit.md` that it MUST NOT be set globally.

3. **Step 10/12 CI re-bump still stalls if `ship-pr.sh` is not updated**: this WAS the primary gap in the first plan version (FINDINGs 11, 15, 16, 19, 26, 29, 31, 34, 35, 38, 39, 40). Resolved by adding `scripts/ship-pr.sh` to UPDATED and threading both the `--allow-changelog-only` flag and the `commit-changelog.sh` call into `run_rebase_rebump` and `_run_rebase_rebump_from_step3`. Earliest warning signal: a Step 12 CI loop that re-runs `ship-pr.sh --resume-phase ship-pr-rrr-phase14` and stalls.

4. **Stale CHANGELOG entries from prior CI iterations survive into merged history**: per FINDING_25 — addressed by the new `--replaces-version` flag on `commit-changelog.sh` and the corresponding awk update in `write_changelog_entry`. Re-bump callers (sub-procedure step 4a, `ship-pr.sh run_rebase_rebump`) parse the prior version from `OLD_BUMP_SHA` and pass it. Earliest warning signal: a merged PR whose CHANGELOG.md contains entries for versions that never reached origin/main.

5. **classify-bump double-bump after a CHANGELOG-at-HEAD state**: addressed by walking past CHANGELOG-subject commits in classify-bump's HEAD-only idempotency check (FINDING_20). Earliest warning signal: `apply-bump.sh` running on a branch that already has a bump commit two below HEAD, producing a second bump.

6. **agent-lint / Makefile shard coverage failures on landing**: addressed by FINDINGs 5/6/28 — agent-lint allowlist entries for the new script family, Makefile shard registration. Earliest warning signal: `make lint` or `make test-harness-shards-coverage` failing in CI.

7. **Test harness regression on landing**: addressed by FINDINGs 3/4/13/23/27/33/36 — `commit-changelog.sh` stub additions in both `scripts/test-implement-finalize.sh` and `skills/implement/scripts/test-step-8a-changelog.sh`. Earliest warning signal: `make test-implement-finalize` or `make test-step-8a-changelog` failing in CI.

## Testing strategy

1. **New harness**: `scripts/test-commit-changelog.sh` covers the new primitive (happy path, skipped no-change path, error paths, `--replaces-version` stale-entry removal, subject byte assertion, `--untracked-files=no` parity). Wired into `make test-harnesses` AND the appropriate `test-harnesses-N` shard (FINDING_6).
2. **Extended harness**: `scripts/test-drop-bump-commit.sh` Tests 21-24 cover the `--allow-changelog-only` flag (default + custom paths, with-flag and without-flag variants, bump-subject and non-bump-subject variants). Tests 25-26 cover the new walk-back shapes (HEAD=CHANGELOG / HEAD~1=Bump and HEAD=log-refresh / HEAD~1=CHANGELOG / HEAD~2=Bump). Tests 1-20 unchanged.
3. **Existing harness updates**: `scripts/test-implement-finalize.sh` and `skills/implement/scripts/test-step-8a-changelog.sh` gain a `commit-changelog.sh` stub alongside the existing `git-amend-add.sh` stub. Existing amend-specific assertions are updated to commit-specific assertions.
4. **ship-pr regression**: `scripts/test-ship-pr.sh` adds a REQUIRED test case (FINDING_32) for `--resume-phase ship-pr-rrr-phase14` under the new commit shape (bump + CHANGELOG with stale-entry removal).
5. **Repo-wide checks**: run `make lint` (covers `lint-bash32`, `lint-foreground-markers`, script-md-siblings, agent-lint) and `make test-harnesses` post-edit. Verify no regression in `test-drop-bump-commit`, `test-implement-finalize`, `test-step-8a-changelog`, `test-ship-pr`, and any harness touching the sub-procedure.
6. **Manual verification (operator)**: run `/implement` against a feature where a Step 12 CI loop is forced; confirm `ship-pr.sh --resume-phase ship-pr-rrr-phase14` completes without stall after the new commit shape lands, and that the merged CHANGELOG.md contains only the final-version entry.

## Acceptance

The fix is complete when ALL of the following hold:

1. **drop-bump-commit.sh accepts CHANGELOG-only bump commits behind the `--allow-changelog-only` flag** — `make test-drop-bump-commit` passes with the new Tests 21-24 covering the flag (default-path + custom-path + with/without flag + bump/non-bump subject) and Tests 25-26 covering walk-back over CHANGELOG / CHANGELOG-over-log-refresh shapes. Existing Tests 1-20 keep passing as before.
2. **`scripts/commit-changelog.sh` exists** and `make test-commit-changelog` passes (happy path, no-change skip, error paths, `--replaces-version` stale-entry removal, subject byte assertion, `--untracked-files=no` parity). The helper uses `scripts/git-commit.sh` for trailer / scoping consistency.
3. **Step 8a in `implement-finalize.sh` calls `commit-changelog.sh`** instead of `git-amend-add.sh CHANGELOG.md`. `make test-implement-finalize` and `make test-step-8a-changelog` pass with their respective `commit-changelog.sh` stubs in the sandbox, and the bump commit at HEAD~1 contains only `plugin.json` (CHANGELOG entry sits at HEAD as a separate commit with subject `Update CHANGELOG for <version>`).
4. **The Markdown sub-procedure step 4a** (`skills/implement/references/rebase-rebump-subprocedure.md`) uses `commit-changelog.sh --version $NEW_VERSION --replaces-version $OLD_VERSION` after re-bump, and step 1 passes `--allow-changelog-only --max-depth 20` to drop-bump-commit.
5. **`scripts/ship-pr.sh run_rebase_rebump()` and `_run_rebase_rebump_from_step3()`** pass `--allow-changelog-only --max-depth 20` to drop-bump-commit AND invoke `commit-changelog.sh` after `apply-bump.sh` with the prior version parsed from `OLD_BUMP_SHA`. `make test-ship-pr` passes with the new mandatory regression case for the `ship-pr-rrr-phase14` resume path.
6. **classify-bump.sh** walks past `^Update CHANGELOG for X.Y.Z$` commits in its HEAD-only idempotency check (bounded 1-3 commits); double-bump after a CHANGELOG-at-HEAD state is no longer possible.
7. **conflict-resolution.md** lists `CHANGELOG.md` in the Phase 1 trivial-file class; `ours` policy auto-resolves replayed CHANGELOG conflicts during rebase recovery.
8. **agent-lint allowlist** includes `commit-changelog.sh`, `commit-changelog.md`, `test-commit-changelog.sh`, and `test-commit-changelog.md`; `make lint` passes.
9. **Makefile shard coverage** registers `test-commit-changelog` in BOTH the `test-harnesses` aggregate AND the appropriate `test-harnesses-N` shard alongside `test-drop-bump-commit`; `make test-harness-shards-coverage` passes.
10. **Repository-wide checks** pass: `make lint`, `make test-harnesses`. No regression in any harness that touches drop-bump-commit, implement-finalize, ship-pr, classify-bump, or the rebase-rebump sub-procedure.
11. **Sibling .md updates** land in the same PR as every .sh / .toml change per `.claude/rules/script-md-siblings.md`: `drop-bump-commit.md`, `commit-changelog.md`, `test-commit-changelog.md`, `implement-finalize.md`, `ship-pr.md`, `git-amend-add.md`, `classify-bump.md`, `apply-bump.md` (OOS_1 callout), `rebase-rebump-subprocedure.md`, `bump-verification.md`, `conflict-resolution.md`, `SKILL.md` (`skills/implement/SKILL.md`).
12. **Followup OOS issues** #2858, #2859, #2860 are recorded as blocked-by #2852 (already filed by Step 5b); operators may close them as already-addressed once the PR lands if the in-scope plan covers their concerns.

diff_lines: 440

## Test plan
(no test plan section in plan-file)
