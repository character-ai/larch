## Proposed Design Outline

### Goals
- Repoint the 3 broken larch-CLI path computations in `python/larch/git/pr_body.py` from the nonexistent `python/larch/git/cli.py` to the real `python/cli.py`.
- Make a future recurrence visible: loud log at the diagram site when the CLI is missing; warnings at the two silent `check=False` sites on nonzero exit.
- Add regression coverage so the path defect cannot recur silently.

### Non-goals
- No changes to any other module — the codebase scan confirms only `pr_body.py` carries the broken idiom.
- No change to the non-fatal / graceful-degradation contract of `/implement` Step 7a or the two `check=False` calls.
- No refactor of `pr_body.py` beyond the three call sites + one new constant.

### Approach sketch
- Add a module-level `_PY_CLI = Path(__file__).resolve().parents[2] / "cli.py"` (mirrors `larch/state/bootstrap.py` / `closeout.py`).
- Point all three argv builders (733, 746, 860/865) at `_PY_CLI`; drop the now-redundant `plugin_root` local.
- Diagram site: when `_PY_CLI` is missing (non-test-hook branch only), emit a loud bounded warning before launch; keep the step non-fatal.
- `read-version` + `upsert-summary` sites: log a warning when the subprocess returns nonzero, so silent degradation surfaces.
- Add a regression test in `python/test_pr_body.py` asserting the built argv targets an existing `python/cli.py`.

### Surfaces in scope
- `python/larch/git/pr_body.py` (the only file with the defect)
- `python/test_pr_body.py` (regression coverage)

### Open questions
- None.
