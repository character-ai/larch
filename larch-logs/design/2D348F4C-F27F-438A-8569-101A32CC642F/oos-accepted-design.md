### OOS_1: `scripts/ship-pr.md:82-84` doc drift — `git add -u` vs `collect_ci_stage_paths`
- **Description**: Invariant prose at `scripts/ship-pr.md:82-84` still says `run_ci_fix_vendor` runs `git add -u` before `git-commit.sh`, but the actual implementation at `scripts/ship-pr.sh:1263-1277` uses `collect_ci_stage_paths` + `git add -- "${stage_paths[@]}"`. Reviewers tagged it OOS but recommended fixing it during the same edit as the plan touches the nearby retry-math prose. Raised by 6 reviewers (multiple tagged OOS, multiple tagged in-scope nit).
- **Reviewer**: Cursor-Arch, Cursor-Edge, Cursor-Innovation, Codex-Pragmatic, Codex-Requirements, Cursor-Requirements
- **Phase**: design


