## Proposed Design Outline

### Goals
- Tighten the eight latent hardening gaps in lint, marker writers, write_tally staging, and the hook parity harness.
- Remove maintenance risk from duplicate `_write_bg_wait_marker` by extracting a shared `bg_wait.py` module.
- Ensure the parity harness covers intentionally renamed function pairs via semantic (name-normalized) comparison.

### Non-goals
- No user-visible changes.
- No changes to `hook-bg-poll-guard.sh` or `hook-no-progress-guard.sh` themselves.
- No changes to `run-step-checks.sh` (already correct).

### Approach sketch
- Item 1: narrow `_has_clone_path_emission` to check `CLONE_PATH=` within a proximity window of lines containing `.bg-wait-active`.
- Items 2–3: create `python/larch/implement/bg_wait.py` with shared `_write_bg_wait_marker`, `_read_keepalive_clone_path`, and related helpers; update `step_7a.py` and `dispatch_commit_route.py` to import from it; add `_optional_bg_wait_marker` call to `run_step_checks_main`.
- Items 4–5: guard `Path(args.log_root).parent` in `write_tally_main`; add assertion that the temp record staged under `log_root.parent` (not `/tmp`).
- Item 6: replace the first-`}`-exit awk with a brace-depth counter.
- Items 7–8: add `compare_renamed_pair` in the parity harness that extracts both functions, strips the differing name from each, and diffs the normalized bodies.

### Surfaces in scope
- `python/larch/lint/lint_bg_wait_writer_parity.py`
- `python/larch/implement/bg_wait.py` (NEW)
- `python/larch/implement/dispatch_commit_route.py`
- `python/larch/implement/step_7a.py`
- `python/larch/review/voting.py`
- `python/tests/review/test_voting.py`
- `scripts/test-hook-clone-ownership-parity.sh`

### Open questions
- None.
