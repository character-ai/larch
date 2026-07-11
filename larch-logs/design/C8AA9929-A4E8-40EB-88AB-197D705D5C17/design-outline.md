## Proposed Design Outline

### Goals
- Fix hardcoded `origin/main` in `_merge_base_baseline` by detecting the remote default branch via `git symbolic-ref refs/remotes/origin/HEAD` first.
- Warn loudly on stderr when `_baseline_sha` falls back to the frozen `step2-baseline.txt`, so operators see inflated-coverage risk.

### Non-goals
- Add a new persisted base-branch key to the session env or tmpdir.
- Change coverage computation or disposition logic beyond the fallback warning.
- Touch anything outside `scope_disposition.py` and its test file.

### Approach sketch
- In `_merge_base_baseline`: call `git symbolic-ref refs/remotes/origin/HEAD`; parse `refs/remotes/origin/<branch>` to get `origin/<branch>`; use that for merge-base; fall back to `origin/main` when symbolic-ref fails.
- In `_baseline_sha`: after reading `step2-baseline.txt`, print a warning to `sys.stderr` before returning the frozen SHA.
- Update `FakeRunner` in the test file to handle `git symbolic-ref` calls via a new `symbolic_ref_head` parameter.
- Add two new tests: one for the symbolic-ref-resolved path (non-main branch), one for the fallback warning.

### Surfaces in scope
- `python/larch/implement/scope_disposition.py`
- `python/tests/implement/test_scope_disposition.py`

### Open questions
- None.
