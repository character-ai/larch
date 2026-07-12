### OOS_1: `Path.iterdir()` committed-corpus walks are outside the ratchet
- **Description**: `Path.iterdir()` committed-corpus walks are outside the ratchet. Scenario: The analysis tool still lists implement run dirs with `root.iterdir()` and no containment checks. The planned AST lint covers glob/rglob/walk/scandir only, so this bypass survives enforcement. Track a follow-up to either repoint through `safe_child_run_dirs` or extend the lint to cover `iterdir`/`listdir` on `larch-logs` roots.
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/analysis/reviewer_impact.py:372
- **Phase**: design




Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### OOS_2: Pre-commit ratchet hook scopes only `python/**/*.py`
- **Description**: Pre-commit ratchet hook scopes only `python/**/*.py`. Scenario: `skills/fluff-analysis/scripts/fluff-analysis.py` and `skills/voter-calibration/scripts/voter-calibration.py` are in-scope repoint targets but outside the planned hook `files` filter; copied walkers could return in skill scripts until `make lint` / CI. Optionally widen the hook to `^(python|skills/[^/]+/scripts)/.*\.py$` or document that skill-script edits rely on CI fast lint only.
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: .pre-commit-config.yaml
- **Phase**: design




Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### OOS_3: Offline reviewer_impact still uses unsafe implement run enumeration
- **Description**: Offline reviewer_impact still uses unsafe implement run enumeration. Scenario: root.iterdir() on larch-logs/implement lacks symlink and containment checks. It is outside the issue’s named scanner repoint set, but it may still need a follow-up or lint exemption if the ratchet scans python/analysis.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/analysis/reviewer_impact.py:370-372
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_4: analyze_bugs prior-snapshot walk is another committed sibling-run glob
- **Description**: analyze_bugs prior-snapshot walk is another committed sibling-run glob. Scenario: _previous_snapshot globs */run-state.json across a runs root under committed logs. It is not in the repoint list and duplicates the unsafe enumeration pattern this feature centralizes elsewhere.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/issue/analyze_bugs.py:1743-1756
- **Phase**: design

Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

