### FINDING_1: Stale Step 5c private imports in the lifecycle barrel
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: major
- **Concern**: The planned Step 5c migration removes or relocates private trailer helpers from `design_step5c.py`, but `design_lifecycle.py` still eagerly imports them. Because those imports resolve at module load, the refactor can raise `ImportError` and prevent `larch.design.design_lifecycle`, registered `design` CLI verbs, and dependent modules from loading before grammar tests run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `### UPDATED: python/larch/design/design_lifecycle.py` to drop obsolete Step 5c trailer imports or repoint them to `plan_grammar` public APIs; alternatively keep thin backward-compat aliases in `design_step5c.py` only until the barrel is updated. Add an import smoke test that `import larch.design.design_lifecycle` succeeds after the Step 5c refactor.
  - From Cursor-Innovation: Add `### UPDATED: python/larch/design/design_lifecycle.py` to drop stale Step 5c private imports or repoint them to `plan_grammar` public helpers; keep the change limited to the import block
  - From Cursor-Pragmatic: Add `### UPDATED: python/larch/design/design_lifecycle.py`: drop removed private re-exports, repoint any retained symbols to `plan_grammar` or thin public Step 5c wrappers, and add a barrel import smoke test so a Step 5c refactor cannot break `larch.design.design_lifecycle` load.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_2: Incomplete Step 5c auto-compose trailer subset
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: The planned optional-size trailer subset does not include `difficulty`, even though Step 5c auto-compose currently handles it alongside the four optional-size keys. Repointing Step 5c splitting and peeling to the narrower subset could leave `difficulty:` in the body or change trailer ordering and orphan-trailer recovery behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In `plan_grammar.py`, export a documented Step-5c auto-compose subset (optional-size keys plus `difficulty`, still excluding `review_status` / `rounds_completed`) and wire Step 5c split/peel helpers to it explicitly in the `design_step5c.py` plan step


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_4: Active replacement extraction is not migrated to terminal `diff_lines` parsing
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: `_extract_file_replacement` remains an active local parser that records the last `diff_lines:` line found anywhere in a candidate block, rather than using the shared terminal contiguous-trailer semantics. Earlier or non-terminal lines can therefore determine the replacement boundary despite the new grammar.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Use the shared terminal trailer result when selecting the replacement boundary, reject candidates without a valid terminal `diff_lines`, and add a revise-waterfall fixture with an earlier and a final conflicting `diff_lines:` line.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_1: [OUT_OF_SCOPE] Marker-bypass sites stay on independent marker/heading logic after the in-scope migration
- **Description**: [OUT_OF_SCOPE] Marker-bypass sites stay on independent marker/heading logic after the in-scope migration. Scenario: The plan excludes `decompose.py`, `learn_from_bugs.py`, and `design_router.py`, so inline `larch:plan` marker checks and `learn_from_bugs`’s `###`-only heading regex remain parallel owners; the feature goal still names marker drift at those paths
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/design/decompose.py:336-339; python/larch/issue/learn_from_bugs.py:62-66; python/larch/design/design_router.py:128
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

