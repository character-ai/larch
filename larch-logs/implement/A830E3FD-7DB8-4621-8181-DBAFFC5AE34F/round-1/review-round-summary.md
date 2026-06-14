# Review Round 1

- Mode: `diff`
- 2 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: close-stale dry-run resolves repo before dry-run output
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `close-stale` dry-run resolves the repo before emitting dry-run output, violating the plan's no-`gh` dry-run contract. Running `combine-issues close-stale --issues 1 --reason "not planned" --dry-run` without `--repo` can call `gh repo view` and fail before printing `DRY_RUN=true`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Move the dry-run branch before repo resolution, or skip repo resolution for dry-run.


### FINDING_3: SKILL oos-2 omits close-stale argv contract
- **Reviewer(s)**: dyn-stale-helper-safety-output.txt
- **Severity**: latent
- **Concern**: The all-stale-only oos-2 terminal path says to invoke `combine-issues close-stale` after approval but does not pin the required argv contract (`--repo`, `--reason "not planned"`, per-issue `--comment-file`) that oos-4 documents. An orchestrator following only the oos-2 branch can omit repo/reason/comment and either fail preflight or close without the intended audit comment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-stale-helper-safety-output.txt: Add the same concrete `close-stale` invocation block to oos-2 (with `not planned`, redacted comment-file requirement, and stdout/stderr parsing for `CLOSED_ISSUES`, `PARTIAL`, and `WARNING=`) so both terminal paths share one contract.


