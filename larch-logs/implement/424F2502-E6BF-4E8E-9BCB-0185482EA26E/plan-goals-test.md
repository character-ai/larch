## Goal
Implement issue #4887: [IMPLEMENTING] [BUG] Step 5c publish validator: false missing-script for consumer-repo scripts.

## Implementation Plan
## Plan

### Approach

Fix the Step 5c publish-tail false positive at its root: the helper that resolves the consumer repo's git toplevel is copy-pasted in ~5-6 places, and `design_publish.py` is the one copy that was never written, so it passes the plugin root as `--repo-root`. Extract one shared helper, adopt it everywhere, and stop the drift that produced this recurrence (#4490 then #4847 then #4887).

- Add one shared, stdlib-only helper module `python/repo_roots.py` exposing `consumer_repo_root()`.
- Adopt it in every validator caller that needs the consumer repo's git toplevel; delete the duplicated local definitions and inline `git rev-parse --show-toplevel` calls.
- Fix the broken Step 5c publish-tail caller (`design_publish.py`): pass the consumer repo as `--repo-root` and keep `CLAUDE_PLUGIN_ROOT` pinned to the plugin cache, exactly as Step 2b postplan does.
- Preserve dual-root validation semantics in `plan_quality.py`: consumer repo first, plugin cache second. Do not change `_resolve_repo_script()`.
- Improve the Step 5c operator guidance so `missing-script` defects (often a root-resolution false positive) are called out separately from genuinely unsafe-token defects.
- Run a grep audit after the change to confirm no remaining caller passes the plugin root as `--repo-root` when a consumer repo is available.

### Files to modify/create

#### NEW: python/repo_roots.py

Small, stdlib-only helper (no heavy or circular imports, so CLI startup does not regress).

- Add `consumer_repo_root(cwd: Path | None = None) -> Path | None`.
- Run `git -C <cwd or Path.cwd()> rev-parse --show-toplevel`; return `Path(out).resolve()` on success.
- Return `None` on `OSError`, non-zero git exit, or empty stdout.
- Docstring cites the #4490 contract: larch may run from a plugin cache; plan-command paths are repo-relative to the consumer repo; validators need the consumer repo first and the plugin root second.
- Consolidates logic now duplicated in `design_postplan.py`, `plan_review.py`, `design_lifecycle.py`, and `plan_quality.py`.

#### UPDATED: python/design_publish.py

Fix the Step 5c publish-tail validator invocation (the defect site).

- Import `consumer_repo_root` from `repo_roots`.
- In the composed-plan `plan validate` block, replace `--repo-root str(plugin_root)` with the Step 2b pattern:
  - `validate_env = {**os.environ, "DESIGN_TMPDIR": str(design_tmpdir), "LARCH_QUIET_DISABLE": "1", "CLAUDE_PLUGIN_ROOT": str(plugin_root)}`
  - `repo_root_arg = consumer_repo_root() or plugin_root`
  - Pass `--repo-root str(repo_root_arg)` and `env=validate_env`.
- Preserve `--skip-validate`, `PLAN_WRITE_OK`, `PUBLISH_RC`, `VALIDATE_STATUS`, `VALIDATE_DEFECT_COUNT`, `VALIDATE_SKIPPED_COUNT`, `VALIDATE_UNSAFE_TOKEN_COUNT`, `VALIDATE_LOG_FILE`, and rc `4`.
- Add an internal helper that counts `kind=missing-script` defect lines in `VALIDATE_LOG_FILE` and expose a new `VALIDATE_MISSING_SCRIPT_COUNT` result-env key additively (rename or remove nothing).

#### UPDATED: python/design_postplan.py

- Import `consumer_repo_root`; delete the local `_consumer_repo_root()` (lines ~26-47); replace `_consumer_repo_root() or root` with `consumer_repo_root() or root`.
- Keep the validation env behavior (`DESIGN_TMPDIR`, `LARCH_QUIET_DISABLE`, `CLAUDE_PLUGIN_ROOT=str(root)`).

#### UPDATED: python/plan_review.py

- Import `consumer_repo_root`; delete the local `_consumer_repo_root()` (line ~85); change `_run_post_apply(..., cwd=_consumer_repo_root())` (line ~900) to `cwd=consumer_repo_root()`.
- Keep the `_run_command(..., cwd=None)` fallback to `_REPO_ROOT`; preserve the #4847 comment, updating its helper reference.

#### UPDATED: python/design_lifecycle.py

- Import `consumer_repo_root`; replace the inline `git rev-parse --show-toplevel` discovery for the `driver_main` validate path (line ~2817) with `consumer_repo_root() or root`; replace `_repo_root()` internals (line ~3148) with the shared helper plus the current fallback, preserving its return-type contract.
- Do not change Step 5c publish rc handling or status emission.

#### UPDATED: python/plan_quality.py

- Import `consumer_repo_root`; replace the inline `git rev-parse --show-toplevel` lookup in the validator-autofix path (line ~2324) with `consumer_repo_root()`; keep the fallback to `CLAUDE_PLUGIN_ROOT` / `validate_repo`.
- Do not change `_resolve_repo_script()` or the dual-root semantics.

#### UPDATED: python/test_design_publish.py

Add the publish-tail regression with a dedicated recording fake CLI. Do not modify the shared `_write_fake_cli`.

- Many existing success-path tests run without a consumer git cwd; after the fix, `consumer_repo_root()` returns `None` there and validation falls back to `plugin_root`. A global fake-validator failure on plugin `--repo-root` would break those tests, so leave `_write_fake_cli` unchanged.
- Add `_write_recording_cli(path)` based on `_write_fake_cli`'s publish-tail handlers (`redact secrets`, `named-block write`, `tracking-issue rename`, `design log-publish`, `diagrams upsert`) so publish reaches `PLAN_WRITE_OK=true`. Replace only the `plan validate` branch: parse `--repo-root`, write `REPO_ROOT=` and `CLAUDE_PLUGIN_ROOT=` to `os.environ["RECORD_FILE"]`, print `VALIDATE_STATUS=ok` + zero counts, exit 0 (recording only).
- Add `test_publish_passes_consumer_repo_root_and_preserves_plugin_root(tmp_path)`: a `git init` consumer repo as `cwd`, a fake plugin root lacking the consumer script, a `composed-plan.md` referencing a consumer-only script. Assert `REPO_ROOT` resolves to the consumer repo, `CLAUDE_PLUGIN_ROOT` to the plugin root, `returncode == 0`, `PLAN_WRITE_OK=true`, `VALIDATE_STATUS=ok`, and no `PUBLISH_RC=4`.

#### UPDATED: python/test_design_postplan.py

- Keep `test_postplan_passes_consumer_repo_root_and_preserves_plugin_root`; replace any reference to `design_postplan._consumer_repo_root` with a behavior assertion or patch `repo_roots.consumer_repo_root` at the call site.

#### UPDATED: python/test_plan_review.py

- If a test patches the local `_consumer_repo_root`, patch `repo_roots.consumer_repo_root` (or the `plan_review` import binding) at the call site instead.

#### UPDATED: python/test_plan_quality.py

- Update import/monkeypatch points only if the extraction requires it; `test_auto_fix_revalidation_uses_consumer_repo_root` must still prove autofix revalidation uses the consumer repo.

#### NEW: python/test_repo_roots.py

- Unit-cover `consumer_repo_root()`: returns the resolved git toplevel inside a work tree; returns `None` when cwd is not a git repo, `git` is missing (`OSError`), or stdout is empty; accepts and resolves an explicit `cwd`.

#### UPDATED: skills/design/SKILL.md

- In `### Plan command validator failure (shared)`, before the final `AskUserQuestion`, add Step 5c-specific wording: when `--site` is `design Step 5c`, summarize `kind=missing-script` separately from `VALIDATE_UNSAFE_TOKEN_COUNT`, explain that `missing-script` is often a root-resolution false positive when running from a plugin cache, and warn against deleting valid consumer-repo test commands to satisfy it.
- Preserve the exact option labels (`Fix-and-retry`, `Override`, `Cancel`), the missing-composition special case, and the `--skip-validate` Override path.

### Edge cases

- Cwd not in a git worktree: `consumer_repo_root()` returns `None`; callers fall back to the plugin root, preserving plugin-only behavior and existing harness tests without `git init`.
- Consumer repo == plugin root: `_resolve_repo_script()` dual-root collapse unchanged.
- Plugin-cache install: `--repo-root` is the consumer repo; `CLAUDE_PLUGIN_ROOT` is the cache.
- Missing `git` binary or git failure: return `None`, use the fallback.
- Truly absent script: validation still fails with `missing-script`.

### Failure modes

- Helper in a heavy/circular-import module regresses CLI startup. Mitigation: a tiny stdlib-only `repo_roots.py`.
- `CLAUDE_PLUGIN_ROOT` not preserved in the Step 5c validate env turns plugin-only scripts into false `missing-script`. Mitigation: set it explicitly; assert it in the regression recorder.
- Harmonizing load-bearing callers risks review-loop / validation regressions. Mitigation: mechanical import-swap only; run `test_plan_review.py`, `test_plan_quality.py`, `test_design_lifecycle.py`, and `make py-test`.
- Result-env key changes break callers. Mitigation: add `VALIDATE_MISSING_SCRIPT_COUNT` additively.

### Testing strategy

- `python3 -m pytest python/test_repo_roots.py`
- `python3 -m pytest python/test_design_publish.py`
- `python3 -m pytest python/test_design_postplan.py`
- `python3 -m pytest python/test_plan_review.py`
- `python3 -m pytest python/test_plan_quality.py`
- `python3 -m pytest python/test_design_lifecycle.py`
- `make py-lint`
- `make py-test`
- `make lint`
- Grep audit (validation only): `grep -RnE "rev-parse --show-toplevel|--repo-root" python`

## Acceptance

- Step 5c composed-plan validation resolves repo-relative scripts against the consumer repo (plugin cache as secondary root); a plan referencing existing consumer-repo scripts validates clean at Step 5c, identical to Step 2b. No spurious `defects-found`, `PUBLISH_RC=4`, or forced Override.
- `consumer_repo_root()` lives only in `python/repo_roots.py`; `design_publish.py`, `design_postplan.py`, `plan_review.py`, `design_lifecycle.py`, and `plan_quality.py` import it. No local `_consumer_repo_root()` or inline `git rev-parse --show-toplevel` copies remain for consumer-repo resolution.
- `grep -RnE "rev-parse --show-toplevel|--repo-root" python` shows no caller passing the plugin root as `--repo-root` when a consumer repo is available.
- `python/test_design_publish.py` asserts the publish validate receives the consumer repo as `--repo-root` while `CLAUDE_PLUGIN_ROOT` stays the plugin cache, exercising the full publish tail to `PLAN_WRITE_OK=true`; `python/test_repo_roots.py` covers the helper.
- The Step 5c operator message distinguishes `missing-script` from unsafe-token defects; `VALIDATE_MISSING_SCRIPT_COUNT` is added additively and no existing result-env key is renamed or removed.
- `make py-lint`, `make py-test`, and `make lint` pass.

diff_lines: 295

## Test plan
(no test plan section in plan-file)
