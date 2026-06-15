## Decision 1: Remove oos-filing from ship.py
- **Question**: Should the OOS checking block (lines ~1334-1342 in ship.py) be removed to make ship.py a pure shipping machine?
- **Resolution**: Yes — remove the `oos_pending` check + `NEEDS_USER_INPUT` return from ship.py. Keep `materialize_manifest_oos` call only.
- **Source**: user

## Decision 2: Issue creation mechanism for new Python filer
- **Question**: Should `python/cli.py oos file` call `gh issue create` directly or hand off to orchestrator `/larch:issue` Skill?
- **Resolution**: Python calls `gh` directly via subprocess. The new subcommand owns the full pipeline end-to-end including GitHub issue creation.
- **Source**: user

## Decision 3: PR body OOS URL injection scope
- **Question**: Bug #1 asks to "remove OOS URL weaving from PR body" — is this fixing existing code or preventive?
- **Resolution**: Audit only. `compose_pr_body` does not inject OOS URLs today. Confirm defensively but no functional change needed unless audit reveals a hidden path.
- **Source**: user

## Decision 4: Codex combine step invocation
- **Question**: How should the Codex combine step be invoked?
- **Resolution**: Call Codex CLI binary via subprocess (same pattern as plan_review.py dispatches external reviewers). No SDK dependency.
- **Source**: user

## Decision 5: steps_ran={} fix approach
- **Question**: Should `python/cli.py oos file` always write run-statistics.md even on empty batches, or fix the heuristic?
- **Resolution**: Always write `run-statistics.md` after Python `outcome=OK`, even empty batches ("0 OOS issues filed"). Heuristic sees the file and returns True.
- **Source**: user

## Decision 6: Bash path scope
- **Question**: Is the bash OOS pipeline (Exit 0 OOS_PENDING=true + oos-pipeline.md) in scope?
- **Resolution**: Bash path is completely untouched. This PR only changes the Python path, ship.py OOS block, and SKILL.md Python routing.
- **Source**: user
