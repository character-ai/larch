## Proposed Design Outline

### Goals
- Add neutral-rate (1-YES) and important-reject-rate (0-YES on reviewer-claimed-important findings) to `fluff-analysis.py`, segmented pre/post a cutoff.
- Add per-voter false-negative view to `voter-calibration.py`: fraction of each voter's YES votes that end on neutral/rejected findings.
- Add optional realized-outcome tie-in to `voter-calibration.py` as a degraded section that skips when GitHub is unavailable.

### Non-goals
- No changes to live review spawning, thresholds, tokens, or proposer scores.
- No changes to `voting.py` or existing baseline tables (neutral stays lumped in the rej% column for backward compat).
- No structural changes to classification TSV formats.

### Approach sketch
- In `fluff-analysis.py`: add `_section_false_negatives()` that reads `outcome` and `body_severity` from existing records. Render neutral-rate by severity tier + important-reject-rate. Gate pre/post sub-tables on existing `cutoff`/`since_version` logic.
- In `voter-calibration.py`: add a `_per_voter_false_negative()` helper that reads TSV rows directly (without the agreement-row path which skips neutral) and counts YES-on-(neutral|rejected) per voter.
- In `voter-calibration.py`: add optional realized-outcome section using `ground_truth_voter_calibration` from `analyze_issues.py`. Wrap in try/except with logged note on failure.
- Update both test harnesses with synthetic fixture rows covering neutral and important-rejected cases.

### Surfaces in scope
- `skills/fluff-analysis/scripts/fluff-analysis.py`
- `skills/fluff-analysis/scripts/fluff-analysis.md` (sibling doc — behavior change)
- `skills/fluff-analysis/scripts/test-fluff-analysis.sh`
- `skills/voter-calibration/scripts/voter-calibration.py`
- `skills/voter-calibration/scripts/voter-calibration.md` (sibling doc)
- `skills/voter-calibration/scripts/test-voter-calibration.sh`

### Open questions
- None.
