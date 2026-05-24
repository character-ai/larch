### OOS_1: skills/shared/topology.tsv may need regeneration when new script surfaces appear
**Reviewer**: Cursor-Arch
**Description**: Repository may have policy that `skills/shared/topology.tsv` (and possibly agent-lint reachability docs at `agent-lint.toml`) need regeneration when new script surfaces appear. This plan adds 5 new `.sh` files (`lib-phantom-probe.sh`, `rebase-checkpoint-probe.sh`, `phantom-probe-with-warn.sh`, `test-rebase-checkpoint-probe.sh`, `test-phantom-probe-with-warn.sh`) plus sibling `.md` files. If CI surfaces a new lint after merge tied to topology regeneration, that would need a follow-up issue to add the topology rows. The agent-lint.toml portion is covered by in-scope FINDING_7; the topology.tsv aspect is the genuine OOS observation.
**Affected files**: skills/shared/topology.tsv
**Phase**: design

Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

