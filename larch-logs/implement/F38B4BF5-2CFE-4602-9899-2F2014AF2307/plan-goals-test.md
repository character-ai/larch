## Goal
Implement issue #6755: [IMPLEMENTING] architectural-knowledge-IV [FEATURE] Add guideline G-Root-1: resolve repo roots from run state, never ambient cwd.

## Implementation Plan
## Plan

## Approach

Add the new root-resolution guideline as documentation only.

Keep scope to `ARCHITECTURAL_GUIDELINES.md`. Do not change Python, tests, invariants, or existing guideline parser logic.

Place `## Execution roots` after `## CLI surface` and before `## Security`, per the resolved discussion. Add `### G-Root-1: Resolve the repository root from persisted run state, never from ambient cwd`.

Use the proposed wording with only the verified evidence issues `#4490`, `#4509`, and `#6049`. Keep the entry a guideline, not an invariant. Include `Why`, `Guidance`, and `Deviate when` bullets. The parser will include `Why` and `Deviate when` in `architectural-guidelines read`; it intentionally omits `Guidance`.

## Files to modify/create

### UPDATED: ARCHITECTURAL_GUIDELINES.md

Insert:

- `## Execution roots`
- `### G-Root-1: Resolve the repository root from persisted run state, never from ambient cwd`
- A `Why` bullet citing only `#4490`, `#4509`, and `#6049`
- A `Guidance` bullet that prefers `REPO_ROOT`, explicit `--repo-root`, or trusted-boundary `CLAUDE_PROJECT_DIR`, with cwd fallback logged as last resort
- A `Deviate when` bullet for interactive cwd-based helpers and tests that control cwd

## Edge cases

- Ensure the heading matches `GUIDELINE_HEADING_RE`: `### G-Root-1: ...`.
- Do not add extra evidence issue numbers.
- Do not imply all cwd use is banned. Preserve the documented exceptions.
- Keep Markdown heading order stable: CLI surface, execution roots, security.

## Failure modes when non-trivial

- If the heading format is wrong, `architectural-guidelines read` will skip the entry.
- If the entry lacks `Why` or `Deviate when`, the acceptance command may not show the required bullets.
- If extra issue citations are added, the change fails the evidence-scope requirement.

## Testing strategy

Run targeted checks after the edit:

1. `python3 python/cli.py architectural-guidelines read --repo-root .`
   - Confirm output includes `### G-Root-1: Resolve the repository root from persisted run state, never from ambient cwd`.
   - Confirm it includes the `Why` bullet with only `#4490`, `#4509`, and `#6049`.
   - Confirm it includes the `Deviate when` bullet.
2. Run the changed-file Markdown lint path, for example the repo's relevant-checks command if available:
   - `python3 python/cli.py checks run-relevant`

## Acceptance

Run targeted checks after the edit:

1. `python3 python/cli.py architectural-guidelines read --repo-root .`
   - Confirm output includes `### G-Root-1: Resolve the repository root from persisted run state, never from ambient cwd`.
   - Confirm it includes the `Why` bullet with only `#4490`, `#4509`, and `#6049`.
   - Confirm it includes the `Deviate when` bullet.
2. Run the changed-file Markdown lint path, for example the repo's relevant-checks command if available:
   - `python3 python/cli.py checks run-relevant`

diff_added: 7
diff_deleted: 0
mechanical_churn: false
diff_lines: 7

## Test plan
(no test plan section in plan-file)
