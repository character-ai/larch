## Proposed Design Outline

### Goals
- Add opt-in pre/post incentive-era segmentation to `/voter-calibration`, comparing panel `High Rate` and `Calibration Score` before vs after the incentive shipped.
- Make the #5461 acceptance signal (a post-incentive High Rate drop) directly readable from the tool.

### Non-goals
- No change to default (no-flag) output. Today's single report stays byte-identical and backward compatible.
- No change to agreement/severity math, reviewer/proposer points, spawning, thresholds, tokens, or live verdicts. The tool stays diagnostic-only.
- No hard GitHub dependency. Offline use stays first-class via `--era-since-date`.

### Approach sketch
- Add `--era {all,pre,post}` and `--era-since-date YYYY-MM-DD` to `voter-calibration.py`.
- Tag each discovered TSV with its run `manifest.json` `started_at` at discovery time; per-finding rows carry no date. Reuse `_ground_truth_run_started_at_strict` + `_ground_truth_run_dir`, or a thin `python/voting.py` helper.
- Resolve boundary: explicit `--era-since-date` wins; else best-effort `gh` auto-detect of the incentive close date; else a clear "boundary unavailable" fallback.
- Render pre vs post agreement + severity scoreboards side-by-side for `--era all`; filter to one corpus for `--era pre|post`.
- Update SKILL.md, the `voter-calibration.md` contract, and the test harness; document the acceptance readout path.

### Surfaces in scope
- `skills/voter-calibration/scripts/voter-calibration.py` and contract `voter-calibration.md`
- `skills/voter-calibration/SKILL.md`
- `skills/voter-calibration/scripts/test-voter-calibration.sh`
- Optional thin era-tagging helper in `python/voting.py`

### Open questions
- None. Boundary source and backward compatibility are resolved in Round 1; runs without `started_at` are excluded with a reported count.
