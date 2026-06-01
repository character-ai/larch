## Goal
Implement issue #3317: [IMPLEMENTING] [OOS] python/rebase.py: port bash run_rebase_rebump parity gaps (pre-drop fixup, defer_push/HAS_BUMP, version-guard base)\n\nCombines three out-of-scope review findings that all target parity between the.

## Implementation Plan
## Plan

# Implementation Plan — #3317 python/rebase.py parity gaps (#2 + #3)

SIMPLE tier. Minimum-change parity port. Two new keyword params per function, each
defaulting to today's behavior so existing callers stay untouched; two existing
`test_rebase.py` monkeypatch stubs must widen for the new `apply_bump` kwargs.

**Scope**: gap #2 (`defer_push` / `has_bump` inputs) and gap #3 (`apply_bump` base
reconciliation). Gap #1 (pre-drop `refresh-run-logs` + `larch-logs/` fixup) is
deferred to the Phase 7 `ship.py` driver (#3240 amended) and is NOT in this plan.

## Files to modify/create

### UPDATED: `python/rebase.py`
`rebase_and_rebump` (def at line 478):
- Add two keyword-only params after `max_attempts`: `has_bump: bool = True`,
  `defer_push: bool = False`.
- Gate the re-bump block on `has_bump`. Wrap the existing
  classify → version-regression guard → `apply_bump` → `_commit_changelog_after_rebump`
  block (current lines ~568-608) in `if has_bump:`. Keep `new_version: str | None = None`
  initialized before the block so `has_bump=False` returns `new_version=None`.
- Gate the force-push on `defer_push`. Replace the unconditional
  `_ = _force_push_branch(runner, cwd=cwd)` (line 610) + hardcoded `pushed=True`
  (line 615) with:
  `pushed = False` then `if not defer_push: _ = _force_push_branch(runner, cwd=cwd); pushed = True`,
  and return `RebaseResult(..., pushed=pushed, ...)`.
- Gap #3 caller wiring: change the `apply_bump` call (line 598) to pass base:
  `version_bump.apply_bump(runner, target_version, base_remote=base_remote, base_ref=base_ref, cwd=cwd)`.
- The rebase-side regression guard (lines 573-596) already uses `base_remote`/`base_ref`;
  leave it unchanged.

### UPDATED: `python/version_bump.py`
`apply_bump` (def at line 467):
- Add two keyword-only params after `cwd`: `base_remote: str = "origin"`,
  `base_ref: str = "main"`.
- Replace the hardcoded guard fetch `git.fetch(runner, "origin", "main", cwd=cwd)`
  (line 566) with `git.fetch(runner, base_remote, base_ref, cwd=cwd)`.
- Replace the hardcoded guard read
  `git.show_file(runner, f"origin/main:{config.PLUGIN_JSON_PATH}", cwd=cwd)` (lines 576-580)
  with `f"{base_remote}/{base_ref}:{config.PLUGIN_JSON_PATH}"`.
- Generalize the three error strings that name `origin/main` (lines ~572, ~595, ~604-606)
  to interpolate `{base_remote}/{base_ref}`; keep them inside `_redact_outbound`.
- `classify_bump`'s own `origin/main` fetch is a separate concern (#3311 names only
  `apply_bump`); leave it unchanged.

### UPDATED: `python/test_rebase.py`
**Existing stubs (FINDING_1)** — widen before new tests; production will pass
`base_remote`/`base_ref` into `apply_bump`:
- `test_rebase_result_uses_apply_result_new_version` (`_apply` at lines 552-557): add
  `base_remote: str = "origin"`, `base_ref: str = "main"` (or `**_kwargs`) to the stub
  signature so the monkeypatch accepts the new kwargs; body unchanged.
- `test_version_regression_guard_recomputes_target` (`_apply` at lines 822-827): same
  signature widening.

**New tests**:
- `test_defer_push_skips_force_push`: call with `defer_push=True`; assert no
  `("git", "push", "--force-with-lease", ...)` entry in `runner.calls`; assert
  `result.pushed is False`; classify/apply still run (re-bump unchanged).
- `test_has_bump_false_skips_rebump`: call with `has_bump=False`; assert no
  apply-bump / classify side-effect calls; assert `result.new_version is None`;
  assert it still force-pushes and `result.pushed is True`.
- `test_apply_bump_receives_base` (FINDING_2): **monkeypatch `classify_bump`** to return a
  fixed non-`NONE` classification (same pattern as `test_rebase_result_uses_apply_result_new_version`
  / `test_version_regression_guard_recomputes_target`) so real `classify_bump` does not issue
  `git.fetch(runner, "origin", "main", ...)`. Drive `rebase_and_rebump` with
  `base_remote="upstream"`, `base_ref="main"`; register `upstream/main` handlers; assert
  `apply_bump`'s guard path issues `("git", "fetch", "upstream", "main", "--quiet")` and
  `("git", "show", "upstream/main:...")`, and that **no** `origin`/`main` fetch/show comes from
  the apply guard (classify traffic is excluded by the patch). Do not broaden scope to
  `classify_bump` in this gap.

### UPDATED: `python/test_version_bump.py`
- `test_apply_bump_threads_base`: call `apply_bump(runner, "1.2.3", base_remote="upstream",
  base_ref="main", cwd=...)`; assert it issues `git fetch upstream main --quiet` and reads
  `upstream/main:.claude-plugin/plugin.json` for the guard. Keep an existing/default-base
  case asserting origin/main is still used when params are omitted.

## Approach
- Parity port mirroring bash `_run_rebase_rebump_from_step3`: `HAS_BUMP` gates the
  classify/apply/changelog block; `defer_push` gates the push. Defaults
  (`has_bump=True`, `defer_push=False`) reproduce current behavior.
- Gap #3 removes the Python port's internal base inconsistency: the rebase guard and
  `apply_bump`'s race-retry guard now share `base_remote`/`base_ref`. Default
  `origin`/`main` keeps behavior byte-identical for today's single caller. This is an
  improvement beyond bash `apply-bump.sh`, which still hardcodes origin/main — accepted
  per Round 1.
- Test layer: production signature change requires stub updates in two existing rebump
  tests; other `test_rebase.py` cases need no edits if they do not monkeypatch `apply_bump`.
  Base-threading for `apply_bump` guard git traffic is covered in `test_version_bump.py`;
  rebase→apply kwargs + non-origin guard traffic in `test_apply_bump_receives_base` with
  `classify_bump` mocked.

## Edge cases
- `has_bump=False` while a bump commit exists on-branch: the earlier drop + bullets
  staging still run; the re-bump is skipped and `new_version=None`. Matches bash
  (HAS_BUMP gates only the re-bump block, not the drop).
- `defer_push=True` with a re-bump: bump is applied + committed locally but not pushed;
  `pushed=False`. The driver owns the later push.
- Both flags set (`has_bump=False`, `defer_push=True`): rebase-only; no re-bump, no push.
- Default base (`origin`/`main`): unchanged behavior; tests that omit new kwargs still pass
  after stub widening.
- Fork base (e.g. `upstream/main`): `apply_bump`'s race-retry loop re-fetches the fork
  base, consistent with the rebase-side guard.

## Failure modes
1. `pushed` left hardcoded `True` while `defer_push` skips the push → callers misread
   push state. Earliest signal: `test_defer_push_skips_force_push` asserting
   `pushed is False` fails. Mitigation: derive `pushed` from the push branch.
2. A hardcoded `origin/main` site in `apply_bump` missed by the edit (error string or the
   retry re-fetch) → a fork guards against the wrong base. Signal: the fork test sees a
   `git fetch origin main` call. Mitigation: grep `apply_bump` for `origin/main` after
   the edit; assert fetch/show targets in `test_apply_bump_threads_base`.
3. `has_bump` gate scoped too narrowly (wrapping only `apply_bump`, not `classify_bump`)
   → classify side-effects (fetch origin main) run when `has_bump=False`. Signal: parity
   test sees classify calls under `has_bump=False`. Mitigation: wrap the whole
   classify→commit block.
4. Existing `_apply` stubs left at three-arg signature → `TypeError: unexpected keyword
   argument 'base_remote'` in `test_rebase_result_uses_apply_result_new_version` or
   `test_version_regression_guard_recomputes_target` before new tests run. Mitigation:
   widen both stubs as part of the `test_rebase.py` edit scope.
5. `test_apply_bump_receives_base` leaves `classify_bump` unmocked → spurious `origin/main`
   fetch fails the test or drags `classify_bump` into scope. Mitigation: monkeypatch
   `classify_bump`; keep classify/base separation explicit in the test docstring.

## Testing strategy
- Four new tests plus two stub signature updates via the `ScriptRunner` prefix-matching
  seam (no real git).
- `make py-test` and `make py-lint` green; do **not** claim all of `test_rebase.py` is
  untouched — only that defaults preserve behavior for tests that do not patch `apply_bump`.
- These satisfy the #3132 quality bar (unit/parity test per ported branch).

## Acceptance
- `python/rebase.py` `rebase_and_rebump` accepts keyword-only `has_bump: bool = True` and
  `defer_push: bool = False`.
- `has_bump=False` skips the classify/apply/changelog block; `RebaseResult.new_version is None`.
- `defer_push=True` skips `_force_push_branch`; `RebaseResult.pushed is False`. Defaults
  (`has_bump=True`, `defer_push=False`) keep current behavior and `pushed is True`.
- `python/version_bump.py` `apply_bump` accepts keyword-only `base_remote: str = "origin"`,
  `base_ref: str = "main"`; its guard fetch and `show_file` use the supplied base; omitting
  the params keeps origin/main behavior byte-identical.
- `rebase_and_rebump` passes its `base_remote`/`base_ref` into the `apply_bump` call.
- The two existing `_apply` monkeypatch stubs in `test_rebase.py` are widened to accept the
  new kwargs; the four new tests above are added and pass.
- `make py-test` and `make py-lint` are green; runtime imports stay stdlib-only.
- Gap #1 (pre-drop fixup) is NOT implemented here — it remains tracked on Phase 7 #3240.

diff_lines: 140

## Test plan
(no test plan section in plan-file)
