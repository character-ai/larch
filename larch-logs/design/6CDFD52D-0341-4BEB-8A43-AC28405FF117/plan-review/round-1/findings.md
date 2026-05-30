### FINDING_1:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-log-publish.sh:53-59
- **Concern**: Ancestor-race harness may pass without exercising the new guard. Scenario: Setup that leaves `sub` (or another intermediate dir) as an outside symlink before publish fails at the existing `find -type l` scan with `PUBLISH_OK=false`, so a test that only asserts `PUBLISH_OK=false` (per Testing strategy) can pass while `design_publish_ancestor_within_root` is never hit; a broken or missing guard could ship undetected
- **Proposed resolution**: Require (1) a stub extension that keeps `-type l` clean then swaps the parent directory at `-type f` time (document env vars in the plan, e.g. parent path + outside target), and (2) an assertion on the new ancestor-specific `larch_err` substring (render-cache / plan-review / `.completed`), not publish failure alone

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-log-publish.sh:1038-1057
- **Concern**: Ancestor-race coverage is underspecified relative to the existing leaf-race harness. Scenario: The plan says to mirror the render-cache symlink-race block, but that block uses make_find_symlink_race_stub to replace the enumerated file with a symlink at find -type f time, which exercises the existing [[ -L "$f" ]] leaf guard—not design_publish_ancestor_within_root. Copying it verbatim can leave the new helper untested while CI stays green.
- **Proposed resolution**: Extend make_find_symlink_race_stub (or add a sibling) so find -type l stays clean, find -type f still lists render-cache/sub/file.txt, and the stub swaps the intermediate sub directory to an outside symlink (not the leaf file). Assert PUBLISH_OK=false and prefer matching the new ancestor error substring.
