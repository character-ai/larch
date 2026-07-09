## Final Design Plan

The plan is very large. Showing the full plan body below.

## Plan

## Approach

Add one shared fail-closed PR mutation gate around scope-disposition validation, and tighten `validate_disposition_for_ship` so gate-relevant tmpdirs cannot fall through advisory recompute-failure paths.

Use `IMPLEMENT_TMPDIR` and optional explicit tmpdir or manifest inputs. Validate before any remote PR mutation. Do not trust `plan.txt` presence as the only relevance signal.

The gate no-ops only when no implement tmpdir is available, or when the tmpdir has none of the artifacts that make validation relevant. Relevance includes:

- `plan.txt`
- `plan-coverage.json`
- `scope-disposition.json`
- a resolved implement manifest at `manifest.json` or `codex-step2-out/manifest.json`

When any relevance artifact exists, call `require_valid_disposition_for_ship` with the resolved manifest path. If validation fails, raise `NeedsUserInput(config.NEEDS_USER_SCOPE_DISPOSITION)` through the existing helper path.

Tighten `validate_disposition_for_ship` so advisory success is allowed only when the tmpdir is not gate-relevant for ship/PR mutation:

- If `scope-disposition.json` exists, fail closed when recompute cannot prove the current plan; do not return the advisory success path.
- When gate-relevant artifacts exist and recompute cannot run because `plan.txt` is missing or unreadable, fail closed even if persisted coverage marks `disposition_required=false`.
- Keep the existing advisory path only for non-gate-relevant contexts where recompute succeeds and disposition is not required, or where no disposition/coverage/manifest relevance artifacts are present.
- Do not silently treat malformed persisted coverage as advisory when recompute cannot run on a gate-relevant tmpdir.

## Files to modify/create

### UPDATED: python/larch/implement/scope_disposition.py

Add shared helpers for PR mutation gates and gate relevance.

Suggested shape:

- `resolve_implement_manifest(tmpdir, manifest_path=None) -> Path | None`
  - Prefer explicit `manifest_path` when provided and readable.
  - Else check `tmpdir / "manifest.json"`, then `tmpdir / "codex-step2-out" / "manifest.json"`.
- `is_pr_mutation_gate_relevant(*, tmpdir: Path, manifest_path: Path | None = None) -> bool`
  - Return true when any of:
    - `plan.txt` exists,
    - `plan-coverage.json` exists,
    - `scope-disposition.json` exists,
    - resolved manifest exists.
- `require_pr_mutation_scope_disposition(*, tmpdir: Path | None, repo_root: Path, manifest_path: Path | None = None, runner: Runner = proc) -> None`
  - Resolve tmpdir from explicit argument first, then `IMPLEMENT_TMPDIR` env.
  - No tmpdir or non-relevant tmpdir: no-op return.
  - If relevant, resolve manifest and call `require_valid_disposition_for_ship`.
  - Propagate `NeedsUserInput(config.NEEDS_USER_SCOPE_DISPOSITION)` on refusal.

Tighten `validate_disposition_for_ship`:

- Add a gate-relevance check using the same artifact/manifest rules as `is_pr_mutation_gate_relevant`.
- In the `ShipError` recompute-failure branch, remove the advisory `ok=True` return when gate-relevant artifacts exist; always return `ok=False` with `coverage-recompute-failed`.
- When `scope-disposition.json` exists and recompute cannot run, fail closed with `scope-disposition-stale` or `coverage-recompute-failed` instead of advisory success.
- In the stale-fingerprint branch that currently unlinks disposition and may return `ok=not coverage.disposition_required`, fail closed when a disposition record was present and recompute could not establish a valid current disposition.
- Preserve advisory behavior only when the tmpdir is not gate-relevant and recompute succeeds with `disposition_required=false`.

### UPDATED: python/larch/git/pr.py

Use the shared gate before each PR mutation path.

Update:

- `_require_scope_disposition` to delegate to `require_pr_mutation_scope_disposition` and remove the `plan.txt`-only skip.
- `ensure_pr` before pushing an existing PR branch, creating a PR, or updating an existing PR body.
- `_push_existing_pr` and `_push_open_pr_branch` before any push.
- `create_pr_parity` before any push or PR create operation.
- `create_main`:
  - Resolve repo root and implement tmpdir from env before mutation.
  - Run the shared gate before `create_pr_parity`.
  - Add an explicit `except NeedsUserInput` handler before the broad `except Exception` that emits:
    - `needs_user_reason=scope-disposition`
    - `NEXT_ACTION=halt-scope-disposition`
    - `PR_STATUS=needs-user` or equivalent non-mutation status KVs
    - return `config.EXIT_NEEDS_USER_INPUT`
  - Leave the broad `except Exception` for unexpected errors only; it must not catch scope-disposition refusal.
- `body_update_main`:
  - Run the shared gate before `gh.pr_edit_body_file`.
  - Map `NeedsUserInput` to the same needs-user route with `UPDATED=false` and no `gh pr edit`.

Keep existing usage errors at exit 2 when no mutation would occur.

### UPDATED: python/larch/git/gh.py

Protect low-level PR body-edit mutation helpers that can be called outside `pr.py`.


- `pr_edit_body`
- `pr_edit_body_file`

Add optional keyword inputs only if needed for explicit tmpdir or manifest threading. Default to env resolution so current callers do not need changes.

Run `require_pr_mutation_scope_disposition` immediately before `gh pr edit`.

For `pr_edit_body_file`, preserve the existing missing-body-file exit 2 before the gate. If the gate refuses, return a `BodyUpdateResult` with exit code `config.EXIT_NEEDS_USER_INPUT`, `updated=False`, and a short sanitized error.

For `pr_edit_body`, raise `NeedsUserInput` before running `gh pr edit` when the gate refuses.

### UPDATED: python/tests/implement/test_scope_disposition.py

Add unit coverage for the new shared gate helpers and tightened validator behavior.

Cover:

- no tmpdir means no-op,
- tmpdir with no plan, coverage, disposition, or manifest artifacts means no-op,
- resolved `manifest.json` alone makes the gate relevant and runs validation,
- manifest with open todos makes disposition required even without `plan-coverage.json`,
- `plan-coverage.json` with `disposition_required=true` and missing `plan.txt` raises `NeedsUserInput`,
- stale `scope-disposition.json` with missing or unreadable `plan.txt` fails closed,
- recompute failure with persisted `disposition_required=false` still fails closed when `scope-disposition.json` exists,
- recompute failure with gate-relevant coverage artifacts fails closed,
- non-required persisted coverage remains advisory only when tmpdir is not gate-relevant and recompute succeeds with `disposition_required=false`.

### UPDATED: python/tests/git/test_pr.py

Add direct mutation regression tests.


- `create_main` returns `config.EXIT_NEEDS_USER_INPUT`, emits `needs_user_reason=scope-disposition` and `NEXT_ACTION=halt-scope-disposition`, and performs no `gh`/`git push` when coverage requires disposition and `plan.txt` is missing.
- `create_main` `NeedsUserInput` is not caught by the broad `except Exception` path (`PR_STATUS` must not be `error` with exit 2).
- `create_pr_parity` refuses before `git push` when manifest-only tmpdir requires disposition.
- `_push_open_pr_branch` refuses before `git push`.
- `body_update_main` returns needs-user exit and emits `UPDATED=false` before `gh pr edit`.

Assert the recording runner saw no mutating `git push`, `gh pr create`, or `gh pr edit` call.

### UPDATED: python/tests/git/test_gh.py

Add low-level body-edit coverage.


- `gh.pr_edit_body_file` refuses with exit 3 and no `gh pr edit` call when env tmpdir artifacts require disposition.
- `gh.pr_edit_body` raises `NeedsUserInput` before running `gh pr edit`.
- manifest-only tmpdir with open todos blocks body edit.

Keep existing retry and repo-threading tests unchanged.

### UPDATED: SECURITY.md

Add a short note under the Python ship-pr driver posture or trust model section.

State that PR create, push, and body-edit mutation helpers validate scope disposition from implement tmpdir artifacts, including manifest-derived todo state, before remote mutation, and fail closed when required artifacts are missing, stale, malformed, unreadable, cannot be recomputed, or when an existing disposition record cannot be validated against the current plan.

## Edge cases

- `IMPLEMENT_TMPDIR` unset: direct gh helpers keep current behavior.
- Empty tmpdir with no scope or manifest artifacts: direct helper remains usable outside `/implement`.
- Manifest-only tmpdir with open todos: gate is relevant; block when disposition is required.
- `plan.txt` missing but `plan-coverage.json` says disposition is required: block.
- `scope-disposition.json` exists without readable `plan.txt`: block until recomputed or rescoping path runs.
- `plan-coverage.json` malformed with no usable recompute path on a gate-relevant tmpdir: block.
- Persisted coverage says `disposition_required=false` but `scope-disposition.json` exists and recompute fails: block.
- Existing open PR path: block before push or body edit.
- Body file missing: preserve current usage error, because no PR mutation is attempted.

## Failure modes

- Over-gating generic gh helpers could break non-implement callers that inherit a stale `IMPLEMENT_TMPDIR`. Mitigate by requiring gate relevance artifacts, including manifest presence, before validation.
- Under-gating low-level helpers leaves a direct import bypass. Cover `gh.pr_edit_body_file` and `gh.pr_edit_body` directly.
- Advisory fallback in `validate_disposition_for_ship` could still bypass stale disposition if gate-relevance rules are not shared between the gate helper and validator. Use one relevance predicate for both paths.
- Catching `NeedsUserInput` under broad `Exception` would downgrade the route to generic error. Add explicit handlers before broad catches in `create_main` and assert the route in tests.

## Testing strategy

Run focused tests:

```bash
python3 -m pytest python/tests/implement/test_scope_disposition.py python/tests/git/test_pr.py python/tests/git/test_gh.py
```

Run changed Python lint:

make py-lint-main

If lint scope needs tighter changed-file targeting, run the repo’s relevant checks CLI after implementation.

difficulty: HARD
diff_lines: 240
