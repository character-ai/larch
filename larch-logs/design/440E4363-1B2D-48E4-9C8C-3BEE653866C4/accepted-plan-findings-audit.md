FINDING_1: agree
  Plan reads and validates the daemon result envelope before requiring merge/status artifacts (ci_fixer_lane.py crashed-lane helper + step-8-ci-fixer.sh --finalize bullets).

FINDING_7: mild-disagree
  Crashed-lane helper returns retry-next-tool/operator-bail only. Plan does not explicitly compare live HEAD to STARTING_HEAD to emit reship when a crashed lane already salvage-committed (the Lane 2 incident shape: salvage commit 64bf7e0eb landed before the _persist crash). Plan follows the issue acceptance criterion (retry-next-tool while tiers remain). Implementer should consider adding salvage-HEAD detection so a crashed lane that advanced HEAD reships instead of consuming the next tier. Not strong: loop still fails safe to operator-bail and matches accepted scope.

FINDING_10: mild-disagree
  Helper validates launch identity/envelope/lineage/log paths and returns operator-bail when postconditions are unprovable, but does not explicitly validate working-tree cleanliness or uncommitted drift before retry-next-tool. Partially addressed via the postcondition/operator-bail path. Implementer should make repo-safety validation explicit. Not strong: fails safe.

FINDING_11: agree
  Plan enforces one total diagnostic cap near config.BGJOB_LOG_TAIL_BYTES (redact then truncate the composed payload), not per-source.
