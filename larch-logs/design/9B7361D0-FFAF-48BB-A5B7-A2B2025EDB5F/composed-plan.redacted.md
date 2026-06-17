## Plan

## Approach

- Make **minimum necessary** docs/config/test changes.
- Treat **NO_SKETCHES** as binding. Use direct codebase inspection, not planning-panel claims.
- Keep runtime behavior unchanged.
- Preserve existing formatting and harness style.
- Do not reformat adjacent JSON, Markdown, or shell blocks.

## Files to modify/create

### UPDATED: README.md

Update the `/implement --emergency` sentence.

- Replace the stale "bypass plan-block presence / plan-adequacy audit / clarify-state pending gates" framing.
- Say `--emergency` **skips the item 4 plan-adequacy audit entirely**.
- Say it downgrades only the documented emergency Preflight gates to warn-and-proceed.
- Keep the summary short enough for the table row.

### UPDATED: docs/skills.md

Mirror the README emergency-mode wording, with slightly more detail if needed.

- State that `--emergency` skips the item 4 plan-adequacy audit.
- State that no `AUDIT=refuse` exists on the emergency path.
- Keep existing facts about loud warnings, `coder=claude`, `--draft`, `--merge`, and default-off behavior.

### UPDATED: skills/implement/SKILL.md

Fix NEVER #5 run-statistics ownership prose.

- Remove the claim that `run-statistics` remains owned only by the post-checkpoint Step 8+ block.
- Say the active Python OOS file path emits `run-statistics` through `python/cli.py oos file` / `python/oos_filer.py`.
- Keep the legacy Step 8+ checkpoint wording only where it still applies to the bash fallback path.
- Do not change OOS control flow.

### UPDATED: .claude/settings.json

Add missing strict-permissions Skill allowlist entries.

- Add `"Skill(bug)",` near `"Skill(block-issue)",`.
- Add `"Skill(larch:bug)",` near `"Skill(larch:block-issue)",`.
- Preserve valid JSON and existing ordering style.
- Do not edit `docs/configuration-and-permissions.md`; it already lists both entries.

### UPDATED: skills/status/SKILL.md

Update degraded health copy.

- Replace "reduced panel or Claude-only mode".
- Distinguish the two actual gate outcomes:
  - **one vendor down**: `/implement` requires explicit operator confirmation, then continues with the unavailable external dropped.
  - **both vendors down**: `/implement` hard-fails and cannot continue until at least one vendor is fixed.
- Do not imply Claude-only fallback for both-down.

### UPDATED: scripts/test-sessionstart-health.sh

Add a regression for stale `LARCH_TOKEN_SESSION_ID`.

- Add a helper or optional argument that runs the hook with a stale ambient `LARCH_TOKEN_SESSION_ID` instead of `env -i` stripping it.
- Use jq and git real tools plus a python3 stub.
- Create a `claude-implement-*` cache dir so the resolver branch runs.
- Feed SessionStart JSON with `cwd` and empty or missing `session_id`.
- Have the python3 stub record the value it sees for `LARCH_TOKEN_SESSION_ID`.
- Assert the stub sees it unset, not the stale value.
- Keep the test fail-open and avoid asserting parent-shell env mutation, because child unsets cannot propagate to the harness shell.

### UPDATED: skills/design/scripts/test-design-step1d5.sh

Add a regression for non-zero `agent collect-results` RC logging.

- Extend the existing python3 stub's `agent collect-results` branch with a test-only env var such as `LARCH_TEST_COLLECT_RESULTS_RC`.
- When set non-zero, emit fixture stdout/stderr and exit with that RC.
- Add a collect-mode case with at least one output path and clean dirty-tree status.
- Assert:
  - `brainstorm-collect.failure.log` exists and contains both collector stdout and stderr.
  - `execution-issues.md` contains the `agent collect-results` failure row.
  - the row references `brainstorm-collect.failure.log`.
  - the exit code in the row matches the stubbed non-zero RC.
- Keep the existing launch-failure test unchanged; this covers a different path.

## Edge cases

- **Emergency docs**: avoid saying clarify-state is bypassed. The clarify refusal path is unreachable because the audit is skipped.
- **Status copy**: avoid "Claude-only mode". Both-down hard-fails.
- **Session token test**: assert child-process resolver env, not parent env.
- **Collect-results test**: ensure the failure log is non-empty. `design_append_brainstorm_failure` returns early for empty files.
- **Settings JSON**: keep commas valid.

## Failure modes

- A stale-token test that uses `env -i` will not exercise the bug.
- A stale-token test that checks the parent shell will fail by design.
- A collect-results test without output paths will hit the existing argument-validation branch, not the non-zero collector branch.
- A collect-results test with no stderr/stdout may miss the append path if the combined failure log is empty.

## Testing strategy

- Run targeted harnesses first:
  - `bash scripts/test-sessionstart-health.sh`
  - `bash skills/design/scripts/test-design-step1d5.sh`
- Run full repo lint:
  - `make lint`
- No Python files are planned. Run `make py-lint` and `make py-test` only if implementation touches Python.

## Acceptance

- **Item 1**: `README.md` and `docs/skills.md` `/implement` `--emergency` text reframed to the audit-skip framing; no remaining "bypasses ... clarify-state pending gates" phrasing in either file.
- **Item 2**: `skills/implement/SKILL.md` NEVER #5 prose names the `python/cli.py oos file` / `python/oos_filer.py` run-statistics emit site; it no longer claims Step 8+ sole ownership.
- **Item 3**: `.claude/settings.json` allowlist contains both `Skill(bug)` and `Skill(larch:bug)`; the file remains valid JSON.
- **Item 4**: `skills/status/SKILL.md` DEGRADED copy distinguishes one-down (operator confirm, reduced panel) from both-down (hard fail, cannot continue); no "Claude-only mode".
- **Item 5**: `scripts/test-sessionstart-health.sh` has a new case that pre-exports a stale `LARCH_TOKEN_SESSION_ID`, runs without `env -i`, and asserts the child resolver sees it unset.
- **Item 6**: `skills/design/scripts/test-design-step1d5.sh` has a new case driving a non-zero `collect-results` RC and asserting the `brainstorm-collect.failure.log` content plus the `execution-issues.md` failure row.
- `make lint` passes; targeted harnesses `bash scripts/test-sessionstart-health.sh` and `bash skills/design/scripts/test-design-step1d5.sh` pass.

review_status: complete
rounds_completed: 1
diff_lines: 95
