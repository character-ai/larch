# Review Round 3

- Mode: `diff`
- 4 accepted, 6 rejected (4 neutral)

## Accepted Findings

### FINDING_1: Codex/Cursor stderr-tail path mismatch breaks Step 3/6 failure surfacing
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `_coder_stderr_tail` strips `.log` and looks for `codex.stderr-tail`, but `write_failed_agent_stderr_tail` writes `codex.log.stderr-tail`. When Codex/Cursor lint-fix dispatch fails with a sidecar, `STDERR_TAIL_PATH` is empty or points at a non-existent file, so `/implement` Steps 3/6 cannot surface the redacted operator tail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Use `run_dir / f"{log_name}.stderr-tail"` without stripping `.log`


### FINDING_10: `test-implement-structure.sh` pin mismatches post-cutover SKILL prose
- **Reviewer(s)**: dyn-ship-cutover-output.txt
- **Severity**: important
- **Concern**: The structural harness still requires `skills/implement/SKILL.md` to contain `re-invoke \`${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/step-8-ship.sh\` per the selector`, but the cutover replaced that recovery prose with state-file-driven re-entry at `skills/implement/SKILL.md:769`. `make test-implement-structure` / `make lint` should fail on this mismatch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ship-cutover-output.txt: Update the pin at `scripts/test-implement-structure.sh:298` to the new canonical re-entry wording (for example the `every Step 8+ re-entry goes through ... step-8-ship.sh` block), or restore equivalent SKILL prose if that contract is still intended.


### FINDING_8: `/review` relevant-checks command omits `python3`
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: The `/review` relevant-checks command is quoted as one executable and omits `python3`, so a shell tries to execute a non-existent path containing spaces: `$CLAUDE_PLUGIN_ROOT/python/cli.py checks run-relevant`. This breaks Step 3e validation before the new Python helper can run. `skills/review-and-fix/SKILL.md:28` has the same missing `python3` pattern in validation guidance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Use `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" checks run-relevant --site review-step3e --tmpdir "$REVIEW_TMPDIR"` in both places.


### FINDING_9: `test_migration_lint.py` fixture embeds real retired path
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: The new test fixture embeds the real retired path `scripts/ship-pr.sh` in a tracked file, so the retired-script linter flags the test itself (`python/test_migration_lint.py:336: references retired path 'scripts/ship-pr.sh'`). This blocks the planned stale-reference acceptance check.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Use a synthetic retired path in the fixture, such as `scripts/old-ship-pr.sh`, and keep the manifest in that test scoped to the synthetic path.


