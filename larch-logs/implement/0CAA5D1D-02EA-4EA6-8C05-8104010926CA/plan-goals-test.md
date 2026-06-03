## Goal
Implement issue #3368: [IMPLEMENTING] Versioning Overhaul Phase 5: Delete dormant version/CHANGELOG machinery\n\n# Versioning Overhaul Phase 5 — Cut over and delete the dormant version/CHANGELOG machinery.

## Implementation Plan
## Plan


## Summary

Physically delete the version/CHANGELOG machinery that Phases 1–4 made dormant, edit the
few live callers to drop their dormant changelog/bump steps (rebase preserved), and sweep
all references clean. Deletions-only: no `ship-pr.sh → Python` cutover (that stays #3240).

## Scope (Round 1, confirmed by operator)

- Deletions-only; keep #3240 separate (its `[DESIGNED]` plan is untouched).
- Full clean deletion: edit live callers, then `git rm` the now-orphaned files.
- Delete `CHANGELOG.md` (the file). History stays in git.

## Hidden constraint discovered (must honor)

`/release` is NOT independent of the bump-version skill. `release-prepare.sh:9` defaults
`CLASSIFY_BUMP` to `.claude/skills/bump-version/scripts/classify-bump.sh`. So `classify-bump.sh`
is a **live** dependency and CANNOT be deleted. The plan **relocates** it into `/release`
(completing the Phase 3 intent) instead of deleting it. `apply-bump.sh` has zero live callers
(`/release` writes versions via its own `release-set-version.sh`) and IS dormant.

## A. Files to DELETE (orphaned after the caller edits in section C)

**Bash scripts + their `.md` siblings + Makefile targets:**
- `scripts/lib-changelog.sh`, `scripts/commit-changelog.sh`, `scripts/auto-resolve-changelog.sh`,
  `scripts/drop-changelog-commit.sh`, `scripts/check-changelog-present.sh`, `scripts/check-bump-version.sh`,
  `scripts/drop-bump-commit.sh` (only callers were `commit-changelog.sh` + `drop-changelog-commit.sh`, both deleted).
- Each script's sibling `.md` contract.

**Test harnesses + their Makefile targets + `.md` siblings:**
- `scripts/test-auto-resolve-changelog.sh`, `scripts/test-check-bump-version.sh`,
  `scripts/test-commit-changelog.sh`, `scripts/test-drop-bump-commit.sh`,
  `scripts/test-drop-changelog-commit.sh`, `scripts/test-apply-bump.sh`, `scripts/test-classify-bump.sh`
  (the relocated copy keeps its test under `/release` — see B), `.claude/skills/bump-version/scripts/test-apply-bump.sh`,
  `.claude/skills/bump-version/scripts/test-classify-bump.sh` (the bump-version copy; relocated test lives under `/release`),
  `skills/implement/scripts/test-step-8a-changelog.sh`.

**bump-version skill (minus the relocated `classify-bump.sh`):**
- `.claude/skills/bump-version/SKILL.md`
- `.claude/skills/bump-version/scripts/apply-bump.sh` + `apply-bump.md` (dormant; zero live callers).
- After B moves `classify-bump.*` out, remove the now-empty `.claude/skills/bump-version/` tree.

**Python (`python/`):**
- `python/changelog.py` + `python/test_changelog.py`.
- `python/bump_worktree.py` — its only consumers are `changelog.py` (deleted) and the drop/rebump
  path in `version_bump.py` (removed in C). Delete after confirming no `from bump_worktree import` remains.

**Docs / contracts:**
- `CHANGELOG.md`.
- `skills/implement/references/rebase-rebump-subprocedure.md`, `skills/implement/references/bump-verification.md`.

## B. Files to RELOCATE (keep `/release` working)

Move the live classifier into `/release` and rewire the default path:
- `git mv .claude/skills/bump-version/scripts/classify-bump.sh   .claude/skills/release/scripts/classify-bump.sh`
- `git mv .claude/skills/bump-version/scripts/classify-bump.md   .claude/skills/release/scripts/classify-bump.md`
- `git mv .claude/skills/bump-version/scripts/test-classify-bump.sh .claude/skills/release/scripts/test-classify-bump.sh`
  (+ its `.md` if present).
- The `test-classify-bump` Makefile target stays; repoint it at the new path.

## C. Files to EDIT (live callers — surgical trims; preserve rebase/force-push/versioning)

### UPDATED: `.claude/skills/release/scripts/release-prepare.sh`
Change the `CLASSIFY_BUMP` default (line 9) from the `bump-version` path to
`$LARCH_ROOT/.claude/skills/release/scripts/classify-bump.sh`. Update `release-prepare.md`
(the `--base` consumer note + dependency list) and `test-release-prepare.sh`:
- **Case 14 (real classify integration):** remove the explicit
  `LARCH_RELEASE_PREPARE_CLASSIFY_BUMP="$REPO_ROOT/.claude/skills/bump-version/scripts/classify-bump.sh"`
  override (line 486) so `release-prepare.sh` line-9 default is exercised after the relocate; keep
  `LARCH_RELEASE_PREPARE_REPO_ROOT` / `LARCH_RELEASE_PREPARE_ORIGIN_REPO` wiring only.
- **Cases 1–13:** unchanged — `run_prepare` may keep injecting the fake `$case_dir/bin/classify-bump.sh` shim.
No behavior change to `release-prepare.sh` itself.

### UPDATED: `scripts/ship-pr.sh`
Remove the dormant changelog/bump limbs while preserving the live rebase path:
- Drop the top-of-file `source "$SCRIPT_DIR/lib-changelog.sh"` + `LARCH_LIB_CHANGELOG_LOADED` sentinel check (lines 21–23).
- Delete `ship_pr_stage_rebump_bullets` (uses `changelog_extract_version_body`) and
  `ship_pr_commit_changelog_after_rebump` (uses `write_changelog_entry`) and their call sites.
- Remove the `auto-resolve-changelog.sh` invocation in the rebase conflict prepass (~line 2775);
  keep the rest of the deterministic prepass (plugin.json etc.).
- Keep `run_rebase_rebump` and all rebase/force-push logic intact (already "rebase, CI-fix, no re-bump").
  Renaming the function is out of scope (avoid churn / contract drift in `ship-pr.md`).

### UPDATED: `scripts/implement-finalize.sh`
The changelog step is already a no-op (`CHANGELOG_STATUS='skipped-phase1'`, line 535). Remove the
dormant plumbing: `--changelog-bullets-file` arg + `CHANGELOG_BULLETS_FILE` var (lines 25, 100–103),
the `CHANGELOG_STATUS` field threaded through `postbump_tail`, and the changelog branch. Preserve
log-write, rebase, and force-push status plumbing. Update `implement-finalize.md`.

### UPDATED: `scripts/test-implement-finalize.sh`
Align the harness with the trimmed `implement-finalize.sh` contract:
- Stop copying `lib-changelog.sh` into the sandbox (`cp` at ~line 158).
- Remove all `assert_contains` expectations on `CHANGELOG_STATUS=skipped-phase1` in postbump
  cases (five lines ~907–961).
- Keep rebase and force-push assertion cases unchanged.

### UPDATED: `scripts/test-verify-skill-called.sh`
Rewrite **Section 5** so it no longer invokes deleted `check-bump-version.sh`:
- Replace the `5a` path that runs `bash "$CHECK_BUMP" --mode pre` with a direct
  `lib-count-commits.sh` source/`count_commits` exercise (preserve the cwd-neutral `5b` case).
- Update the Section 5 header comment and drop the `.claude/skills/bump-version/SKILL.md`
  fixture used only to drive `HAS_BUMP=true` through the deleted gate.
- Sections 1–4 unchanged.

### UPDATED: `skills/implement/SKILL.md` (+ `skills/implement/references/*`)
Remove references to deleted surfaces: `check-changelog-present.sh` (line 1306),
`test-step-8a-changelog.sh` (line 1311), the retired `rebase-rebump-subprocedure.md` /
`bump-verification.md` pointers, and any `--changelog-bullets-file` / changelog-bullets compose
step in the postbump call. Keep the postbump rebase-conflict note (line 85), trimming only changelog wording.

### UPDATED: `python/version_bump.py`
Remove the rebump / same-version-race / version-regression code paths (the drop function near
line 698 and its helpers). Remove the now-unused `from bump_worktree import (...)` block. Keep
`classify_bump` and the core bump helpers. Update `python/test_version_bump.py` to drop the removed-path cases.

### UPDATED: `python/rebase.py`
Remove `import changelog` (line 12) and the `changelog.auto_resolve(...)` branch in
`_deterministic_prepass` (~line 104). Drop the rebump limb of `rebase_and_rebump` (keep rebase).
Update `python/test_rebase.py`.

### UPDATED: `python/test_checks_bash_parity.py`
Remove `lib-changelog.sh` / `auto-resolve-changelog.sh` from the bash↔Python parity arrays (lines 33–34, 46).

### UPDATED: `.github/workflows/ci.yaml`
Remove (or generalize) the `Install gawk for lib-changelog parity tests` step (~line 442) now that
`lib-changelog.sh` and its parity test are gone — keep gawk only if another step needs it.

### UPDATED: `Makefile`
Delete the targets for every removed harness: `test-check-bump-version`, `test-drop-bump-commit`,
`test-drop-changelog-commit`, `test-commit-changelog`, `test-apply-bump`, `test-auto-resolve-changelog`,
`test-step-8a-changelog`. Remove them from the `.PHONY` lists and from their `test-harnesses-N` shard
lines. Keep `test-classify-bump` (repointed in B). Keep `test-release-*`.

### UPDATED: comment-only / doc reference sweep
- `scripts/lib-count-commits.sh`, `scripts/verify-skill-called.sh`, `skills/implement/scripts/hook-stop-fail-close.sh`,
  `scripts/lint-skill-invocations.py`: scrub `check-bump-version` / `/bump-version` mentions in comments/docstrings
  (no live logic depends on them).
- `docs/linting.md`, `docs/configuration-and-permissions.md`, `docs/run-logs.md`, `docs/skills.md`,
  `docs/workflow-lifecycle.md`, `docs/installation-and-setup.md`: remove references to the deleted
  skills/scripts/CHANGELOG.
- `skills/{review,alias,research}` + `skills/shared/subskill-invocation.md`: drop `bump-version` mentions.
- `skills/shared/topology.tsv` + generated `docs/topology.md`: regenerate via `make generate-topology-docs`
  if counts shift; remove any bump-version row.
- `agent-lint.toml` S030 pins: drop any pin naming a deleted path (caught by `make lint`).

## Approach (ordering)

1. Edit live callers first (section C) so no script imports/sources a soon-deleted file.
2. Relocate `classify-bump.*` (section B); rewire `release-prepare.sh` + test + doc.
3. `git rm` the orphaned files (section A), including `CHANGELOG.md`.
4. Sweep references (docs, Makefile, CI, comments, topology).
5. Gate: `grep` clean across `skills/ scripts/ hooks/ .github/ python/ docs/`; `make lint`,
   `make py-lint`, `make py-test` green.

## Edge cases

- `classify-bump.sh` must remain executable and byte-equivalent after the move (git rename, not rewrite).
- `LARCH_RELEASE_PREPARE_CLASSIFY_BUMP` env override must still win over the new default.
- Case 14 must **not** set `LARCH_RELEASE_PREPARE_CLASSIFY_BUMP` — otherwise `make test-release-prepare`
  never reads the line-9 default and a wrong relocate path can pass CI while bare `/release` fails with `dependency-missing`.
- `bump_worktree.py` deletion is conditional: only after the `version_bump.py` trim removes the last import.
- Deleting `CHANGELOG.md` must not break any pre-commit hook that expects it (none remain after `check-changelog-present.sh` deletion — verify).
- Makefile shard lines: removing a target from one `test-harnesses-N` line must not leave a dangling name elsewhere.

## Failure modes (3 most likely)

1. **Broken `/release`** — deleting/mis-pathing `classify-bump.sh`. *Signal:* `release-prepare.sh`
   emits `dependency-missing classify-bump.sh not found`. *Mitigation:* relocate (not delete); run
   `make test-release-prepare` after the rewire.
2. **Dangling source/import** — `ship-pr.sh` still sources `lib-changelog.sh`, or `rebase.py` still
   `import changelog`, after the file is removed. *Signal:* `ship-pr.sh` aborts at startup; `make py-lint`
   import error. *Mitigation:* edit callers before `git rm`; grep-clean gate before commit.
3. **Stale Makefile / CI target** — a deleted harness name remains in `.PHONY` or a shard line, or the
   gawk CI step references a gone parity test. *Signal:* `make <target>` "No rule"; CI step failure.
   *Mitigation:* remove targets from `.PHONY` + shard lines together; run `make lint`.

## Testing strategy

- Run `make lint` / `make py-lint` / `make py-test` — all green.
- Run `make test-release-prepare`, `make test-release-set-version`, `make test-release-finish` to prove
  `/release` survives the `classify-bump.sh` relocation (Case 14 must hit the relocated default with no
  `LARCH_RELEASE_PREPARE_CLASSIFY_BUMP` override; Cases 1–13 keep the fake shim).
- Run `make test-ship-pr-rebase` / `make test-implement-finalize` to prove rebase/force-push survive the
  changelog-limb removal and the finalize harness no longer copies `lib-changelog.sh` or asserts
  `CHANGELOG_STATUS`.
- Run `make test-verify-skill-called` after the Section 5 rewrite (no `check-bump-version.sh` invocation).
- Grep-clean assertion: zero matches for the deleted basenames across `skills/ scripts/ hooks/ .github/ python/ docs/`
  (the `bump-version` / `classify-bump` mentions that remain must point only at the new `/release` location).
- Manual: confirm `ship-pr.sh` (or a dry-run of the `/implement` happy path) runs with no bump/CHANGELOG steps.

## Acceptance

- Named files deleted; `classify-bump.*` relocated; `make lint` / `make py-lint` / `make py-test` green.
- No dangling references (grep clean across `skills/ scripts/ hooks/ .github/ python/ docs/`).
- `/release` and the `/implement` happy path run unchanged (no bump/CHANGELOG steps).
- #3240 untouched; #3339 unaffected (its Phase 7 integration items stay with the cutover).


diff_lines: 15255

## Test plan
(no test plan section in plan-file)
