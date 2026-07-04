## Proposed Design Outline

### Goals
- Add `CLONE_PATH=` stamp to the Step 3 `.bg-wait-active` writer in `run-step-checks.sh`, aligning it with the other eight bg-wait writers.
- Add a writer-parity lint that prevents future writers from omitting the stamp.

### Non-goals
- Change keepalive-fallback behavior in the hook scripts.
- Harden missing-keepalive diagnostics (left as acceptable silent behavior).
- Touch any other `.bg-wait-active` writer.

### Approach sketch
- In `run-step-checks.sh` SITE=step3 block: read `.larch-keepalive` CLONE_PATH (mirror `step-5-review.sh:74-79`), extend `printf` with `CLONE_PATH=%s\n`.
- Update `run-step-checks.md` to mention the CLONE_PATH field in the marker description.
- Add `python/larch/lint/lint_bg_wait_writer_parity.py`: enumerate known `.bg-wait-active` writer files, assert each contains `CLONE_PATH=`.
- Register as `lint bg-wait-writer-parity`; add Makefile `lint-bg-wait-writer-parity` and `test-lint-bg-wait-writer-parity` targets; add the lint target to the `lint:` dependency.
- Add `python/tests/lint/test_lint_bg_wait_writer_parity.py` with accept and reject cases.

### Surfaces in scope
- `skills/implement/scripts/run-step-checks.sh`
- `skills/implement/scripts/run-step-checks.md`
- `python/larch/lint/lint_bg_wait_writer_parity.py` (new)
- `python/tests/lint/test_lint_bg_wait_writer_parity.py` (new)
- `python/larch/cli.py`
- `Makefile`

### Open questions
- None.
