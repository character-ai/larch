# compose-plan-goals-test.sh contract

`scripts/compose-plan-goals-test.sh` builds the `plan-goals-test` larch-log
payload from the file-backed implementation plan produced by `/design` or the
quick-mode inline plan.

Inputs:

- `--plan-file <path>` is required. The file must exist, be non-empty, and be at
  least 64 bytes.
- `--goal-text <text>` is optional and defaults to empty.

Output is written to stdout with this structure:

- `## Goal`
- `## Implementation Plan`
- `## Test plan`

The implementation plan section contains the plan-file body up to the first
recognized test/verification heading. If the source body starts with a level-1/2/3 heading whose text is
`Implementation Plan` (case-insensitive), the wrapper omits that first heading
so the payload does not duplicate `## Implementation Plan`.

The test plan section contains the content after the first level-1/2/3 heading
named `Test plan`, `Tests`, `Testing`, `Verification`, `Test strategy`, or
`Verification strategy`, stopping at the next level-1/2/3 heading. It emits
`(no test plan section in plan-file)` when no recognized heading is present.

The script fails closed for missing, empty, too-short, or pointer-only plan
files. It is called by `skills/implement/SKILL.md` before writing the
`plan-goals-test` batch through `scripts/larch-log.sh`.

Harness: `scripts/test-compose-plan-goals-test.sh`.
