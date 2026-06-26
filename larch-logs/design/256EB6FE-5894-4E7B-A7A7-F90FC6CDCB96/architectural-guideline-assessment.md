## Architectural guideline assessment (Gate C)

Two minor deviations, both consistent with existing module patterns and justified:

- **G-Py-7 (wrap gh/git as typed Runner calls):** the auto-boundary path adds local `_run_gh_json` and `_resolve_incentive_repo` direct-subprocess helpers in the stdlib-only analyzer, not the typed ShipError/Runner layer. These are one-shot internal probes with explicit fail-closed fallbacks (FileNotFoundError, non-zero exit, JSON failure -> boundary-unavailable, exit 0), matching G-Py-4 and the guideline's own "one-shot internal probe" carve-out. `analyze_issues.py` already shells out to `gh` directly via the same precedent.
- **G-Skill-2 (logic behind cli.py):** new era logic lives in `skills/voter-calibration/scripts/voter-calibration.py` (its existing shape, which bootstraps `python/` imports) and reuses private `_ground_truth_*` helpers from `analyze_issues.py`, rather than a new `cli.py` verb or shared `python/voting.py` helper. Keeps the change surgical and within the issue's named surfaces.

Otherwise aligned: G-Py-4 (boundary-unavailable is the sanctioned degraded path), and backward compatibility is preserved (no-flag output stays byte-stable).
