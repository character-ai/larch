## Decision 1: Defensive hardening scope
- **Question**: Beyond fixing the 3 broken `cli.py` paths in `pr_body.py` (+ regression test), how much defensive hardening should the fix include?
- **Resolution**: Both defensive additions. (a) Core: correct all 3 sites via a single shared module constant `_PY_CLI = Path(__file__).resolve().parents[2] / "cli.py"` (mirroring `larch/state/bootstrap.py` / `closeout.py`) + add a regression test in `python/test_pr_body.py` asserting the constructed argv points at an existing `python/cli.py`. (b) Fail-fast: the code-flow diagram site (`launch-claude-subprocess`) logs loudly if the resolved `cli.py` is missing, so a future packaging move surfaces fast instead of degrading silently. (c) Warn: the two `check=False` sites (`plugin read-version`, `tracking-issue upsert-summary`) surface a warning when the subprocess returns nonzero, so silent degradation (`version=unknown`, skipped `larch:metadata` upsert) becomes visible.
- **Source**: user

## Decision 2: No other relocated modules carry the broken idiom
- **Question**: Are there other modules from the `larch.*` packaging series (#5167-#5170) that compute `Path(__file__).resolve().parent / "cli.py"` and need the same correction?
- **Resolution**: No. Repo-wide grep shows `python/larch/git/pr_body.py` is the only nested module with the broken idiom. Every other `.parent / "cli.py"` site (`oos_filer.py`, `plan_quality.py`, `final_report.py`, `test_checks.py`, `test_forked_repo.py`) lives directly in `python/`, where `.parent` correctly resolves to `python/cli.py`. The `larch/state/*` siblings already use the correct `parents[2]` idiom. Scope stays limited to `pr_body.py` + its test.
- **Source**: codebase

## Decision 3: Preserve non-fatal / graceful-degradation behavior (hard constraint)
- **Question**: Must the existing non-fatal behavior of the three call sites be preserved?
- **Resolution**: Yes. The code-flow diagram step is non-fatal at the caller and the two `check=False` sites degrade gracefully today. The fail-fast guard must only fire when the resolved `cli.py` is genuinely missing (an error condition that, post-fix, will not occur in normal runs) — it adds visibility, it must not turn graceful degradation into a hard crash of `/implement`. New warnings are additive logging only; the public return/behavior of the three calls must not otherwise change.
- **Source**: codebase
