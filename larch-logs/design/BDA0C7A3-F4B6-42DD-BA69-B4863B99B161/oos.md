### OOS_1: Retained panel-dispatch and aggregate implementations become Split-path dead code
- **Description**: Retained panel-dispatch and aggregate implementations become Split-path dead code. Scenario: After Split-path stops calling the panel, `panel-dispatch` and `aggregate` remain fully implemented and tested while unused by the feature entry routes.
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/design/decompose.py
- **Phase**: design


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_2: [OUT_OF_SCOPE] Fold migrate-deps into annotate after URL mapping
- **Description**: [OUT_OF_SCOPE] Fold migrate-deps into annotate after URL mapping. Scenario: annotate already consumes issue stdout and writes partition-filed.md; a separate migrate-deps fence adds orchestrator surface area. One helper pass could snapshot external edges and apply replacements immediately after annotate when the batch is complete.
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/design/decompose.py
- **Phase**: design


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### OOS_3: migrate-deps should reuse deps_audit dependency-read parsing
- **Description**: migrate-deps should reuse deps_audit dependency-read parsing. Scenario: The plan adds new dependency-read parsers in decompose.py while python/larch/issue/deps_audit.py already exposes _dep_numbers and _read_existing_edges on gh.issue_blocked_by_read/issue_blocking_read. Parallel parsers can disagree on paginated JSON shape and edge orientation during live verification.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/larch/design/decompose.py
- **Phase**: design


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### OOS_4: Close-original comment still describes only intra-batch dependencies
- **Description**: Close-original comment still describes only intra-batch dependencies. Scenario: The plan migrates original incoming/outgoing GitHub dependency edges onto filed pieces, but `close_original_issue` still tells operators to see only intra-batch edges from `partition-deps.tsv`. After migration succeeds, the close comment can misstate what was rewired on GitHub.
- **Reviewer**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: code-quality
- **Location**: python/larch/design/decompose.py:451-451
- **Phase**: design


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_5: Stale Split-path reference to decomposition panel dispatch
- **Description**: Stale Split-path reference to decomposition panel dispatch. Scenario: The plan removes panel dispatch from Split-path, but `plan-review-runtime.md` is not in the firm file list and still states that Split-path uses `decompose panel-dispatch`. That stale cross-reference can send maintainers or future edits back toward the retired multi-question panel flow.
- **Reviewer**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: architecture
- **Location**: skills/design/references/plan-review-runtime.md:208
- **Phase**: design

Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

