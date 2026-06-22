### OOS_1: [SCOPE-REDUCTION] Ship helper extraction does not add a pure KEY=value decision core for `run_ship`
- **Description**: [SCOPE-REDUCTION] Ship helper extraction does not add a pure KEY=value decision core for `run_ship`. Scenario: Issue acceptance asks for pure cores unit-tested without stdout scraping for named god-functions including `run_ship`. This plan's ship work is imperative Flush+Push/postmerge dedup with existing integration tests, not a `(inputs) -> rows` decider; it adds ~280 deletions and merge-loop touch risk without new pure-test seams
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/ship.py:1364-2114
- **Phase**: design




Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted

### OOS_2: [OUT_OF_SCOPE] Dual row models (`tuple[tuple[str, object], ...]` vs postplan `tuple[str, ...]`) increase refactor hazard
- **Description**: [OUT_OF_SCOPE] Dual row models (`tuple[tuple[str, object], ...]` vs postplan `tuple[str, ...]`) increase refactor hazard. Scenario: Review uses structured KV row tuples; postplan uses raw stdout segments in `PostplanDecision.rows`. Same PR already carries a large parity matrix; inconsistent modeling raises join/ordering mistakes during apply
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/review_pipeline.py:37-44
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

