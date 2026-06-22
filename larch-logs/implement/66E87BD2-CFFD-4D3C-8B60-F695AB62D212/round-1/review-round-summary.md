# Review Round 1

- Mode: `diff`
- 2 accepted, 3 rejected (2 neutral)

## Accepted Findings

### FINDING_1: Warning-string-consistency harness not migrated to pytest
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-dyn-retired-paths-output.txt
- **Severity**: important
- **Concern**: The retired Bash harness case `case-warning-string-consistency` was not migrated to pytest. The operator-facing failure contract in `docs/configuration-and-permissions.md` (canonical `/implement` OOS cap failure breadcrumb) is no longer CI-guarded. `make test-oos-issue-cap` can stay green while documented recovery text drifts from what operators see at runtime (`python/oos_filer.py` tool-failure logging vs `python/design_oos.py` generic stderr).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add a pytest asserting the warning substring remains in docs/configuration-and-permissions.md (and optionally skills/implement/SKILL.md if it echoes the string).
  - From dyn-dyn-retired-paths-output.txt: Add a pytest case under `-k issue_cap` that reads `docs/configuration-and-permissions.md` and asserts the canonical warning string is still present verbatim (and optionally that `skills/implement/SKILL.md` / `skills/design/SKILL.md` still describe cap failure as blocking OOS filing), restoring the contract the retired harness enforced.


### FINDING_9: `IssueCapInvalidEnv` handler leaves stale `--output` file on disk
- **Reviewer(s)**: dyn-dyn-oos-cap-output.txt
- **Severity**: important
- **Concern**: On invalid `OOS_ISSUES_PER_RUN_CAP` or `OOS_ISSUE_CAP_EXCERPT_MAX`, `issue_cap_main` returns exit code 2 from the `IssueCapInvalidEnv` handler without deleting a pre-existing `--output` file. The retired Bash helper's `cleanup_on_exit` trap removed `--output` on any failure when `--output` was provided, including env-validation failures before any write. A retry after a bad env value can leave a stale capped file at `--output` while stderr reports exit 2.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-oos-cap-output.txt: Mirror the `ValueError`/`OSError` cleanup in the `IssueCapInvalidEnv` handler (or share one failure-path helper) so that when `args.output` is set and resolves to a different path than `args.input_file`, `Path(args.output).unlink(missing_ok=True)` runs before returning 2.


