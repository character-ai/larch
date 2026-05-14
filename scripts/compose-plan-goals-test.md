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

The implementation plan section contains the full plan-file body. The test plan
section contains the content after a `# Test plan` or `## Test plan` heading in
the plan file, or `(no test plan section in plan-file)` when the heading is
absent.

The script fails closed for missing, empty, too-short, or pointer-only plan
files. It is called by `skills/implement/SKILL.md` before writing the
`plan-goals-test` batch through `scripts/larch-log.sh`.

Harness: `scripts/test-compose-plan-goals-test.sh`.
