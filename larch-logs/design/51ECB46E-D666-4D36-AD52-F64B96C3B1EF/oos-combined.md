### OOS_1: [SCOPE-REDUCTION] Ship helper extraction does not add a pure KEY=value decision core for `run_ship`
- **Description**: [SCOPE-REDUCTION] Ship helper extraction does not add a pure KEY=value decision core for `run_ship`. Scenario: Issue acceptance asks for pure cores unit-tested without stdout scraping for named god-functions including `run_ship`. This plan's ship work is imperative Flush+Push/postmerge dedup with existing integration tests, not a `(inputs) -> rows` decider; it adds ~280 deletions and merge-loop touch risk without new pure-test seams
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/ship.py:1364-2114
- **Phase**: design
