# Review Round 2

- Mode: `diff`
- 8 accepted, 5 rejected (2 neutral)

## Accepted Findings

### FINDING_16: risk-integration: python/test_ci.py
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Missing ci agentic-fix CLI parser coverage CLI argv drift breaks parent delegate at runtime Add parser tests for required/optional agentic-fix flags
- **Suggested revision**: Address the concern above.


### FINDING_2: correctness: skills/implement/scripts/stall-recovery-report.sh:731-762
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Test-output grep runs before ci-fix-exhausted bail handling in classify_from_evidence. ci-fix-exhausted detail log containing test failure text classifies as test-failure with RESUME_HINT=step8-shippr contradicting operator-only bail plan. When bail=ci-fix-exhausted classify as unrecoverable/none before generic test/lint heuristics regardless of detail content.
- **Suggested revision**: Address the concern above.


### FINDING_24: **correctness** `python/rebase.py:223-231` — Important: The conflict launcher now stores the model output file as `TierAttempt.failure_log`, but `agents.effective_failure_class()` treats any marker-free file as `"health"` instead of falling back to `attempt.failure`. Concrete scenario: Claude exits with `launcher_exit=1` because its JSON is malformed or it refused, while `launch_claude_ci_main` writes only diagnostics to the output and emits `LAUNCHER_FAILURE_CLASS=other` on stdout; `_resolve_conflicts()` then sees `"health"` at `python/rebase.py:289-291`, skips the required first-fixer non-health short-circuit, and tries Codex/Cursor anyway. **Suggested fix:** Point `failure_log` at a captured launcher stdout/KV envelope, or make `effective_failure_class()` fall back to `attempt.failure.failure_class` when the file has no `LAUNCHER_FAILURE_CLASS` marker.
- **Reviewer**: codex-generic-output.txt
- **Concern**: - **correctness** `python/rebase.py:223-231` — Important: The conflict launcher now stores the model output file as `TierAttempt.failure_log`, but `agents.effective_failure_class()` treats any marker-free file as `"health"` instead of falling back to `attempt.failure`. Concrete scenario: Claude exits with `launcher_exit=1` because its JSON is malformed or it refused, while `launch_claude_ci_main` writes only diagnostics to the output and emits `LAUNCHER_FAILURE_CLASS=other` on stdout; `_resolve_conflicts()` then sees `"health"` at `python/rebase.py:289-291`, skips the required first-fixer non-health short-circuit, and tries Codex/Cursor anyway. **Suggested fix:** Point `failure_log` at a captured launcher stdout/KV envelope, or make `effective_failure_class()` fall back to `attempt.failure.failure_class` when the file has no `LAUNCHER_FAILURE_CLASS` marker.
- **Suggested revision**: Address the concern above.


### FINDING_34: **correctness** `python/rebase.py:223-231,288-294` — `make_conflict_launch_fn` now sets `TierAttempt.failure_log` to the launcher output file whenever it exists, but write-capable CI launchers (`launch-claude-ci`, etc.) emit `LAUNCHER_FAILURE_CLASS=` on stdout, not into that output file. `effective_failure_class()` reads `failure_log` first and defaults missing KV to `"health"`. So a first-tier Claude failure that `classify_launch_failure()` correctly classifies as `"other"` (parse/refusal/timeout) is misread as `"health"`, the explicit loop does not take the first-fixer short-circuit, and Codex/Cursor still run. That breaks parity with `run_waterfall` and the plan's "first-tier non-health short-circuit" rule. Stub `_resolve_conflicts` tests avoid this because they omit `failure_log`. **Suggested fix:** Do not point `failure_log` at the model output artifact unless it contains launcher KV lines; prefer stdout capture, `.diag`/`.done` sidecars, or `attempt.failure.failure_class` in `_resolve_conflicts` when the output file lacks `LAUNCHER_FAILURE_CLASS=`.
- **Reviewer**: dyn-conflict-loop-output.txt
- **Concern**: - **correctness** `python/rebase.py:223-231,288-294` — `make_conflict_launch_fn` now sets `TierAttempt.failure_log` to the launcher output file whenever it exists, but write-capable CI launchers (`launch-claude-ci`, etc.) emit `LAUNCHER_FAILURE_CLASS=` on stdout, not into that output file. `effective_failure_class()` reads `failure_log` first and defaults missing KV to `"health"`. So a first-tier Claude failure that `classify_launch_failure()` correctly classifies as `"other"` (parse/refusal/timeout) is misread as `"health"`, the explicit loop does not take the first-fixer short-circuit, and Codex/Cursor still run. That breaks parity with `run_waterfall` and the plan's "first-tier non-health short-circuit" rule. Stub `_resolve_conflicts` tests avoid this because they omit `failure_log`. **Suggested fix:** Do not point `failure_log` at the model output artifact unless it contains launcher KV lines; prefer stdout capture, `.diag`/`.done` sidecars, or `attempt.failure.failure_class` in `_resolve_conflicts` when the output file lacks `LAUNCHER_FAILURE_CLASS=`.
- **Suggested revision**: Address the concern above.


### FINDING_35: **correctness** `python/rebase.py:125-137,278-285` — `_path_has_conflict_markers()` treats any line starting with `=======` as a conflict marker. Git uses that pattern, but so do RST/Markdown underlines and similar content. After a fixer removes real `<<<<<<<`/`>>>>>>>` markers and git clears the unmerged index, a legitimate `=======` line can leave `markers_remain=True`, block the success branch, force extra tier attempts, and end in stall/handoff despite a resolved conflict. The old waterfall path relied on git unmerged state only. **Suggested fix:** Tighten detection to git's conflict-marker shape (for example require adjacent `<<<<<<<`/`>>>>>>>` context, or anchor `=======` between them) instead of matching a bare separator line anywhere in the file.
- **Reviewer**: dyn-conflict-loop-output.txt
- **Concern**: - **correctness** `python/rebase.py:125-137,278-285` — `_path_has_conflict_markers()` treats any line starting with `=======` as a conflict marker. Git uses that pattern, but so do RST/Markdown underlines and similar content. After a fixer removes real `<<<<<<<`/`>>>>>>>` markers and git clears the unmerged index, a legitimate `=======` line can leave `markers_remain=True`, block the success branch, force extra tier attempts, and end in stall/handoff despite a resolved conflict. The old waterfall path relied on git unmerged state only. **Suggested fix:** Tighten detection to git's conflict-marker shape (for example require adjacent `<<<<<<<`/`>>>>>>>` context, or anchor `=======` between them) instead of matching a bare separator line anywhere in the file.
- **Suggested revision**: Address the concern above.


### FINDING_38: **security** `python/agents.py:4384-4425` — `launch_claude_lint_fix_main` does not apply the containment checks used by sibling Claude launchers. It only checks `prompt_file.is_file()` and never validates `--output` or `--prompt-body-file` for absolute paths, symlink rejection, allowed-root containment, or safe-path character rules (`_validate_ci_args`, `_validate_prompt_file`, `_validate_claude_output`). The command is exposed via `python/cli.py agent launch-claude-lint-fix`, so a direct caller can point `--prompt-body-file` at a symlinked readable file and `--output` at an arbitrary writable location for `.prompt`, `.diag`, `.done`, and `.token-record` sidecars. **Suggested fix:** Reuse the existing validators: require an absolute non-symlink `--output` under an allowed session/tmp root; validate `--prompt-body-file` with `_validate_prompt_file` against the output parent and repo cwd; reject symlinks; cap prompt size before `_read_text`.
- **Reviewer**: dyn-lint-claude-output.txt
- **Concern**: - **security** `python/agents.py:4384-4425` — `launch_claude_lint_fix_main` does not apply the containment checks used by sibling Claude launchers. It only checks `prompt_file.is_file()` and never validates `--output` or `--prompt-body-file` for absolute paths, symlink rejection, allowed-root containment, or safe-path character rules (`_validate_ci_args`, `_validate_prompt_file`, `_validate_claude_output`). The command is exposed via `python/cli.py agent launch-claude-lint-fix`, so a direct caller can point `--prompt-body-file` at a symlinked readable file and `--output` at an arbitrary writable location for `.prompt`, `.diag`, `.done`, and `.token-record` sidecars. **Suggested fix:** Reuse the existing validators: require an absolute non-symlink `--output` under an allowed session/tmp root; validate `--prompt-body-file` with `_validate_prompt_file` against the output parent and repo cwd; reject symlinks; cap prompt size before `_read_text`.
- **Suggested revision**: Address the concern above.


### FINDING_8: security: python/rebase.py:288-294
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Conflict failure class is parsed from model-authored .out files via effective_failure_class. Model output containing LAUNCHER_FAILURE_CLASS=other forces first-tier short-circuit handoff without trying Codex/Cursor. Parse LAUNCHER_FAILURE_CLASS from launcher subprocess stdout or driver sidecars only, not tier .out payload.
- **Suggested revision**: Address the concern above.


### FINDING_9: risk-integration: python/agents.py:356-376
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Missing LAUNCHER_FAILURE_CLASS in .out defaults to health, breaking first-tier other short-circuit in production launches. Real first-tier refusal short-circuit never fires; behavior diverges from plan and from unit tests that inject KVs into log files. Bind failure class to launch_tier stdout envelope, not model result file.
- **Suggested revision**: Address the concern above.


