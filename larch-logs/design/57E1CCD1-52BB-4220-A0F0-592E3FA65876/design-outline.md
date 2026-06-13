## Proposed Design Outline

### Goals
- Fold `design-step2b-prelude.sh` logic into `design-step2b-drafter.sh` so Step 2b needs one Bash fence on the drafter-success path.
- On drafter structural success, exec into `design-step2b-postplan.sh --site step2b` and propagate the rc contract (0, 10, 12, 13).
- Delete the now-unused `design-step2b-prelude.sh` and its sibling `.md`.

### Non-goals
- No change to inline-fallback behavior: the fallback postplan fence in SKILL.md stays.
- No change to `design-step2b-postplan.sh` itself.
- No change to the dirty-tree recovery path or its `AskUserQuestion` flow.
- No change to SKILL.md's rc-10/12/13 routing prose — only trigger point shifts from postplan fence to drafter fence.

### Approach sketch
- Add `step2b_exact_line_file()`, sentinel validation, `.completed/step-2a` write, and timing mark to `design-step2b-drafter.sh` (before the existing pause check).
- In the drafter success branch (after `✅` print), replace proceed to postplan fence with `exec design-step2b-postplan.sh --site step2b`.
- Remove the prelude Bash fence from SKILL.md Step 2b and the prelude entries from the wrapper contract inventory.
- Update SKILL.md orchestration: `✅` + rc=0 → Step 3; `✅` + rc=10/12/13 → same routing as before.
- Extend `test-design-step2b-drafter.sh`: add sentinel fixture files + postplan stub to existing tests; add rc=10/12/13 propagation test cases.
- Extend `scripts/test-design-structure.sh`: assert drafter contains postplan call, SKILL.md lacks prelude fence.

### Surfaces in scope
- `skills/design/scripts/design-step2b-drafter.sh`
- `skills/design/scripts/design-step2b-drafter.md`
- `skills/design/scripts/design-step2b-prelude.sh` (deleted)
- `skills/design/scripts/design-step2b-prelude.md` (deleted)
- `skills/design/SKILL.md`
- `skills/design/scripts/test-design-step2b-drafter.sh`
- `scripts/test-design-structure.sh`

### Open questions
- None.
