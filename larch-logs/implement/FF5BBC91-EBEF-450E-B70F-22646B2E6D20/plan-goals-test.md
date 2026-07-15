## Goal
Implement issue #7317: [IMPLEMENTING] [FEATURE] Move /learn-from-bugs state publication from a 232-line SKILL.md Bash fence behind python/cli.py (G-Skill-2).

## Implementation Plan
## Summary

`skills/learn-from-bugs/SKILL.md` embeds a 232-line Bash fence implementing the state-publication flow: branch validation, local and remote branch-reuse refusal, worktree management, commit, PR creation, and recovery control flow, with complex quoting and many error branches, all executed by the orchestrator inline. G-Skill-2 (`ARCHITECTURAL_GUIDELINES.md` line 251: "Keep logic in Python behind cli.py; SKILL.md and Bash stay thin") says this logic belongs behind `python/cli.py`. This was recorded twice as pre-push architectural warnings in the committed run log of the #7151 fix and remains unchanged on main.

## Evidence

- Committed warnings in `larch-logs/implement/B69F75CD-43AE-47C9-9CBA-05D1DF654677/execution-issues.ndjson` (issue #7151 run, 2026-07-12): "The changed SKILL.md embeds a large state-publication implementation in an inline Bash fence, including complex quoting and control flow, rather than keeping logic behind cli.py or a file-backed script." and "The new state-publication Bash fragment embeds substantial control flow, parsing, recovery, and external-command logic in SKILL.md rather than behind cli.py."
- Current main: the largest bash fence in `skills/learn-from-bugs/SKILL.md` spans lines ~186-418 (232 lines). Inline error-handling excerpts around lines 244-265 include branch validation ("The state publication branch is invalid."), local branch-reuse refusal, remote branch-reuse refusal, remote-check failure handling, and worktree-path collision handling.
- The state-publication contract itself is load-bearing: SKILL.md line ~28 documents that state publication runs automatically after a successful default-mode Step 4 report and under `--file`/`-s`, and that "The local marker commit is not durable until its state PR is confirmed merged. A valid unmerged state PR is a manual-merge handoff."

## Why now

- Orchestrator-inline Bash of this size is the exact class the repo has been migrating away from (docs/python-migration.md); it is untestable offline, fails only at runtime, and its two security-adjacent bugs already needed a separate fix (#7168, DONE: unverified repo identity and reverted lifecycle refreshes).
- SKILL.md prose size is ratcheted (skill-closure-growth); moving 200+ lines behind cli.py buys headroom.

## Suggested design

1. Add a cli verb owning the whole flow, for example `python3 python/cli.py learn-from-bugs state-publish` (match existing learn-from-bugs verb naming in `python/larch/cli.py`), implemented in the existing learn-from-bugs module family under `python/larch/issue/`. Inputs: repo root from run state (G-Root-1, never ambient cwd), state-file path, branch-name parameters, and a dry-run flag if the current fence has one. Outputs: machine KV stdout (`STATE_PUBLISH_STATUS=...`, PR URL, reason tokens) with every token defined once (G-Cfg-1).
2. Port each Bash branch to a typed, tested Python path, preserving observable behavior byte-for-byte where machine-consumed (G-Wire-1) or sweeping all consumers in the same change: branch-name validation, refuse-existing-local-branch, refuse-existing-remote-branch, remote-check-failure, worktree-path collision, worktree creation and cleanup, commit, PR creation via the file-backed body path (`python/cli.py pr create --body-file` or the gh wrappers; never inline `--body`), and the manual-merge handoff outcome.
3. Shrink the SKILL.md fence to a thin invocation plus KV parse and outcome routing, matching how other skills call cli verbs. Target roughly 30 lines or fewer.
4. Follow docs/python-migration.md: no shims, repoint all consumers, and update `scripts/residual-bash-paths.txt` and the migration manifest only if any standalone script is retired (the fence itself is SKILL prose, not a scripts/ file).
5. Offline tests per the stub-and-subprocess pattern in `python/tests/issue/`: one test per outcome listed in point 2, driving the verb with stubbed `gh`/git runners; assert the exact KV grammar and exit codes.

## Acceptance criteria

- The state-publication fence in `skills/learn-from-bugs/SKILL.md` is a thin invocation (roughly 30 lines or fewer); all validation, recovery, and mutation logic lives behind `python/cli.py`.
- New pytest coverage exercises: fresh publish success, invalid branch name, existing local branch refusal, existing remote branch refusal, remote-check failure, worktree-path collision, PR-create failure, and the unmerged-PR manual-merge handoff outcome.
- The documented durability contract (marker commit not durable until state PR merges) and automatic-publication triggers are unchanged and re-stated in the skill prose.
- `make py-lint`, `make py-test`, `make agent-lint`, skill-closure-growth ratchet, and the learn-from-bugs harnesses pass. Note: SKILL.md shrinkage should satisfy the closure ratchet without a baseline regen; if a regen is somehow needed, use the sanctioned `--write` path and say so in the PR.

## Affected files

- `skills/learn-from-bugs/SKILL.md`
- `python/larch/issue/` learn-from-bugs modules and `python/larch/cli.py` (verb registration)
- `python/tests/issue/` (new tests)
- `docs/` only if a doc names the inline flow

## Related work (do not duplicate)

- #7151 (DONE) fixed the stray modified/committed `larch-logs/shared/learn-from-bugs-state.json`; its run's assessment produced the warnings above.
- #7168 (DONE) fixed repo-identity verification and lifecycle refreshes inside this flow; behavior from that fix must be preserved in the port.

## Test plan
(no test plan section in plan-file)
