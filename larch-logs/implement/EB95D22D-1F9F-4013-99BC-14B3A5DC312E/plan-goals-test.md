## Goal
Implement issue #6795: [IMPLEMENTING] [BUG] Step 2 dispatcher commit aborts on file-modifying client pre-commit hooks.

## Implementation Plan
## Plan

## Approach

Add one bounded retry to the shared Step 2 dispatcher commit tail.

- Keep the initial `git add -A` behavior unchanged.
- If the first `git commit -F <commit_msg_file>` fails, run `git add -A` again, then retry the same commit exactly once.
- Retry every non-zero commit result. Do not inspect hook output.
- Keep client hooks enabled. Do not add `--no-verify`.
- Continue normally when the retry succeeds. This adopts any hook-fixed source bytes.
- Run the existing teardown only when the retry add or retry commit fails.
- Preserve stderr from the final failing command in `<tool>-commit-stderr.txt`.
- Keep `files_touched` diagnostic-only. Do not alter the manifest schema or downstream coverage logic.
- Do not change the separate commit mechanism in `dispatch_commit_route.py`.

## Files to modify/create

### UPDATED: python/larch/implement/dispatch_step2.py

Update the complete-status commit block after plan coverage is computed.

- Retain the first staging command and its current immediate failure handling.
- On first commit failure, re-stage the full working tree with `git add -A`.
- If re-staging fails, write that add command's stderr, unlink `st.manifest_path` and `st.manifest_raw_path`, and emit `STATUS=bailed REASON=commit-failed`.
- If re-staging succeeds, run the same `git commit -F` command once more.
- If the second commit fails, write its stderr and run the existing manifest teardown and bail path.
- If the second commit succeeds, remove any stale commit-stderr artifact and continue through run-log flush and sanitized manifest output.
- Keep the retry local to this dispatcher source-commit path. Avoid a new shared abstraction unless it reduces duplication without widening scope.

### UPDATED: python/tests/implement/test_implement_dispatch.py

Add a small hermetic pre-commit hook installer, mirroring the fixture pattern in `python/tests/report/test_run_logs.py`.

Add dispatcher-level regression coverage:

1. **File-modifying hook succeeds on retry**
   - Use the existing temporary feature-branch repository fixture.
   - Have the fake launcher create an edited file without a final newline and emit a valid complete manifest.
   - Install an executable `.git/hooks/pre-commit` that records its invocation count, appends the missing newline, and exits 1 only when it changes the file.
   - The hook must not run `git add` or otherwise stage its edit; the dispatcher's retry `git add -A` is the sole operation that stages the hook-fixed bytes.
   - Run the Step 2 dispatcher.
   - Assert `STATUS=complete`.
   - Assert the hook ran twice.
   - Assert the commit exists with the manifest commit message.
   - Assert the committed file contains the hook-fixed bytes and the working tree is clean.
   - Assert the manifest remains available at the dispatcher-selected `st.manifest_path` equivalent for the chosen coder, and no commit-stderr failure artifact remains.
   - For a Codex case, this means asserting the manifest under `codex-step2-out/manifest.json`, rather than a bare `$tmpdir/manifest.json`; retain the raw-manifest assertion at the corresponding dispatcher raw path.

2. **Checking-only hook fails twice**
   - Install a hook that records its invocation count, writes distinct failure stderr, and always exits 1.
   - Run the dispatcher with a valid complete manifest and source edit.
   - Assert `STATUS=bailed REASON=commit-failed`.
   - Assert the hook ran exactly twice.
   - Assert `<tool>-commit-stderr.txt` contains stderr from the second failing commit.
   - Assert both manifest files are unlinked using the exact dispatcher paths for the selected coder: the effective `st.manifest_path` and `st.manifest_raw_path`.
   - For a Codex case, assert removal of `$tmpdir/codex-step2-out/manifest.json` and `$tmpdir/manifest-raw.json`, not bare same-directory manifest names.
   - Assert no implementation commit was created.

## Edge cases

- An initial `git add -A` failure still bails without attempting a commit.
- A failed first commit may leave both index and worktree changes. The second `git add -A` must adopt all unstaged hook edits.
- A retry-stage failure must not trigger a second commit.
- A retry that succeeds after a transient commit failure must not leave stale failure diagnostics.
- A hook may modify bytes not declared in `files_touched`. Existing undeclared-path warnings and manifest diagnostics remain unchanged because the manifest does not define committed byte identity.
- Cursor and Codex both use this shared block through `st.tool_tag`; avoid tool-specific branching.

## Failure modes

- Retrying without re-staging would attempt to commit stale index content and fail the fixer-hook case.
- Allowing the test hook to stage its own fix would let a retry pass without proving that the dispatcher re-staged hook edits.
- Parsing hook stderr would miss other recoverable failures and couple behavior to client hook text.
- Retrying more than once could hide persistent hook failures or create an unbounded loop.
- Writing first-attempt stderr after the retry fails would obscure the final failure.
- Unlinking manifests after the first failure would prevent successful retry completion.
- Using bare manifest paths in Codex teardown assertions could false-pass while leaving the dispatcher-owned manifest behind.
- Using `--no-verify` would bypass legitimate client validation and violate the source-commit contract.

## Testing strategy

Run the focused dispatcher commit tests first:

`python -m pytest python/tests/implement/test_implement_dispatch.py -k commit`

Run the full dispatcher test file if the focused selector excludes either new case:

`python -m pytest python/tests/implement/test_implement_dispatch.py`

Run repository-selected checks:

`python3 python/cli.py checks run-relevant`

Inspect the changed diff to confirm no `--no-verify` was introduced, the fixer hook does not stage its own edit, teardown assertions use the dispatcher-specific manifest paths, and no changes reached `dispatch_commit_route.py` or run-log commit code.

## Scope and confidence

Confidence: high. The failing commit block, sibling retry precedent from #6791, approved outline, and existing hermetic hook fixture are directly present. The change affects a workflow commit path, so the difficulty floor is MODERATE.

## Acceptance

Run the focused dispatcher commit tests first:

`python -m pytest python/tests/implement/test_implement_dispatch.py -k commit`

Run the full dispatcher test file if the focused selector excludes either new case:

`python -m pytest python/tests/implement/test_implement_dispatch.py`

Run repository-selected checks:

`python3 python/cli.py checks run-relevant`

Inspect the changed diff to confirm no `--no-verify` was introduced, the fixer hook does not stage its own edit, teardown assertions use the dispatcher-specific manifest paths, and no changes reached `dispatch_commit_route.py` or run-log commit code.

diff_added: 117
diff_deleted: 10
mechanical_churn: false
diff_lines: 127

## Test plan
(no test plan section in plan-file)
