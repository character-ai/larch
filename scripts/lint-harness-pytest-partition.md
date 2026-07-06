# lint-harness-pytest-partition.sh

`python3 scripts/lint-harness-pytest-partition.py` verifies that pytest `-k` selectors in Makefile targets stay disjoint when tests are split across harness targets. The script is a repository harness with this sibling contract so callers, invariants, and edit-in-sync expectations remain discoverable beside the implementation.

Update this contract and the Makefile target documentation whenever the selector grammar or partition policy changes.
