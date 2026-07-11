## Proposed Design Outline

### Goals
- Close the fail-open gap in `require_pr_mutation_scope_disposition` so a detectable ship or implement context cannot bypass disposition validation when the trusted tmpdir is missing or not a directory.
- Complete the `coder_runner.py` snapshot migration: route its decisions through the complete-snapshot validator and remove the legacy `_snapshot_mode` heuristic.
- Add the planned regression coverage to the five test files left out of #6852.

### Non-goals
- Do not redo the broader #6852 trusted-artifact migration. Only complete the leftover gaps.
- Do not add new opt-in flags or config knobs for gate detection.
- Do not change snapshot locations or the trusted I/O primitives introduced by #6852.

### Approach sketch
- In `scope_disposition.py`, detect a ship or implement context and raise `ShipError` when that context exists but the trusted tmpdir is missing or not a directory. Keep the no-op path only when no implement context is detectable, so standalone non-implement callers still work (G-Py-4, I-Gate-1).
- In `coder_runner.py`, replace the `_snapshot_mode(round_dir)` call with the complete-snapshot validator from `snapshot.py`, so mode decisions never trust unvalidated snapshot state (G-Fix-1, I-Stale-1).
- Align the `_ScopeDispositionModule` protocol in `gh.py` with the real function signature, including `manifest_path`.
- Add regression tests across the five named files covering context-gated fail-closed behavior and coder_runner validator routing.

### Surfaces in scope
- `python/larch/implement/scope_disposition.py`
- `python/larch/review/coder_runner.py`
- `python/larch/review/snapshot.py` (validator entry points, read-only discovery)
- `python/larch/git/gh.py` (protocol signature)
- `python/tests/git/test_pr.py`, `python/tests/git/test_pr_body.py`
- `python/tests/state/test_finalize.py`
- `python/tests/report/test_final_report.py`
- `python/tests/review/test_review_and_fix.py`

### Open questions
- The exact context signal for context-gated fail, set `IMPLEMENT_TMPDIR` versus a discoverable manifest, is an implementation decision deferred to plan drafting.
