### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/step_7a.py:235-250
- **Concern**: Step 7a still calls run-log commit after a guarded flush_logs_pre skip. Scenario: flush_logs_pre will refuse its internal _commit_run when final-summary.md has a forbidden label, but Step 7a _run_log_flush always invokes python/cli.py run-log commit afterward (skills/implement/scripts/test-step-7a.sh:776 expects this). larch_log_commit_main calls _commit_run directly with no pre-terminal label check, so a stalled or bailed summary in the tmpdir log tree can still reach the repo on the Step 7a pre-ship path.
- **Proposed resolution**: Add the shared parse/check helper to larch_log_commit_main (python/larch/report/run_log_commit.py) immediately before _commit_run: when the staged implement run_dir final-summary.md parses to a forbidden label, refuse commit with a bounded warning and non-zero exit. Keep finalize teardown commit_larch_logs unguarded. Add a regression test in python/tests/report/test_run_logs.py (or test_run_log_flush.py) that seeds a forbidden heading under log_root and asserts larch_log_commit_main does not commit. List python/larch/report/run_log_commit.py under ### UPDATED: if the guard lives there. ## Findings ### 1. [correctness] `python/larch/implement/step_7a.py:235-250` — Step 7a bypasses the new pre-terminal guard The plan wires `_preterminal_outcome_refresh_skip` only into `flush_logs_pre()` and `larch_log_flush_main()`. That covers `refresh_run_logs_main`, ship postbump refresh, and the standalone flush helper. Step 7a uses a different two-step pattern in `_run_log_flush`: if not no_logs_commit and not defer_git_commit: refresh = run_logs.flush_logs_pre(runner=run_logs.proc, ctx=with_context, cwd=str(Path.cwd())) if refresh.skipped and refresh.reason not in {"no-repo-cwd", "no-logs-commit", "volatile-only"}: log_flush_status = "degraded" commit = _run_cli( "run-log", "commit", ... ) After `flush_logs_pre` returns `RefreshSkip(reason=REFRESH_SKIP_COMMIT_FAILED)` for a forbidden label, Step 7a still runs `run-log commit`. `larch_log_commit_main` goes straight to `_commit_run` with no label guard (`python/larch/report/run_log_commit.py:712-719`). Staging in `flush_logs_pre` will already have written the stalled or bailed `final-summary.md` into the tmpdir log tree, so the follow-on commit can publish the forbidden pre-terminal label and defeat I-Outcome-1 on a primary in-flight path. **Suggested revision:** Extend the shared helpers to `larch_log_commit_main` (or have Step 7a skip commit when the pre-terminal guard fires). Prefer guarding `larch_log_commit_main` so design publish and implement share one chokepoint; keep `commit_larch_logs` in finalize teardown on the documented terminal carve-out. Add a focused test and list `python/larch/report/run_log_commit.py` in **Files to modify/create**.



### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/step_7a.py:235-252
- **Concern**: Step 7a still unconditionally runs `run-log commit` after `flush_logs_pre()`. Scenario: When the new preterminal-label guard makes `flush_logs_pre()` return `REFRESH_SKIP_COMMIT_FAILED`, this branch still invokes the commit CLI, so a stalled or bailed `final-summary.md` can still be copied into the repo and the guard is bypassed.
- **Proposed resolution**: Skip the commit call when `refresh.reason == config.REFRESH_SKIP_COMMIT_FAILED`, or gate the commit on `not refresh.skipped` after the flush result is checked.



### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/step_7a.py:235-250
- **Concern**: Step 7a run-log commit bypasses the pre-terminal label guard. Scenario: flush_logs_pre will return RefreshSkip when final-summary.md has a forbidden label, but step_7a always calls run-log commit afterward (skills/implement/scripts/test-step-7a.sh asserts flush-failure still runs commit). That second commit copies the same stalled or bailed summary into the repo, defeating I-Outcome-1 on an in-flight implement path.
- **Proposed resolution**: Add python/larch/implement/step_7a.py to the plan: call the shared _preterminal_outcome_refresh_skip (or equivalent) before run-log commit and skip commit when it fires; update skills/implement/scripts/test-step-7a.sh so pre-terminal refusal does not fall through to commit.



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/report/run_log_flush.py
- **Concern**: Heading parser must target the run summary line, not the first ## section. Scenario: final-summary.md is built with _join_prefixed_summary and may contain ## Architectural guidelines or ## Architectural invariants before the canonical ## /implement run ... label (python/larch/report/final_report.py:842-856). A parser that reads the first ## heading or the first colon-delimited line can miss or misread the outcome label, letting forbidden labels commit or blocking neutral ones.
- **Proposed resolution**: Specify that _parse_preterminal_outcome_label scans all lines for startswith("## /") (same contract as final_report._summary_stalled_heading_index), extracts the trailing label after : or em-dash, and add a unit test with prefixed ## Architectural sections before the run heading.



### FINDING_5:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/report/run_log_flush.py:893-999
- **Concern**: `capture_transcript_main()` still commits the whole run tree without the new pre-terminal outcome guard.. Scenario: The public `run-log capture-transcript` CLI can still publish a run tree whose `final-summary.md` says `stalled`, `bailed`, or `bailed-needs-user-input` when invoked with the default `--defer-commit false`, so the new invariant is bypassed outside the refresh/flush paths.
- **Proposed resolution**: Apply the same pre-terminal guard before `_commit_run()` here too, or force this CLI onto the no-commit path whenever `final-summary.md` is present.



### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/step_7a.py:235-250
- **Concern**: Pre-terminal guard omits the Step 7a run-log commit chokepoint. Scenario: Plan wires I-Outcome-1 only into flush_logs_pre and larch_log_flush_main. Step 7a always calls python/cli.py run-log commit after flush_logs_pre, even when refresh returns RefreshSkip with REFRESH_SKIP_COMMIT_FAILED. That second path hits larch_log_commit_main -> _commit_run directly and can still publish a forbidden stalled/bailed heading from the staged log tree.
- **Proposed resolution**: Add the same shared pre-terminal check to larch_log_commit_main in python/larch/report/run_log_commit.py (skip commit with bounded warning, mirroring larch_log_flush_main), or teach step_7a to skip run-log commit when the refresh skip was caused by a forbidden label. List run_log_commit.py (and step_7a.py if branching there) under Files to modify/create and add a Step 7a regression test. ## 1. [correctness] Pre-terminal guard omits the Step 7a `run-log commit` chokepoint **Location:** `python/larch/implement/step_7a.py:235-250` **Concern:** The plan correctly places the guard in `flush_logs_pre()` and `larch_log_flush_main()`, but `/implement` Step 7a runs a second, unconditional `run-log commit` after every `flush_logs_pre()` call. That path goes through `larch_log_commit_main()` → `_commit_run()` with no label check. **Scenario:** When `flush_logs_pre()` returns `RefreshSkip(skipped=True, reason=REFRESH_SKIP_COMMIT_FAILED)` because the settled `final-summary.md` still has `: stalled`, `: bailed`, or `: bailed-needs-user-input`, Step 7a still invokes `run-log commit` and can publish the forbidden label anyway. This leaves a live implement pre-ship commit seam outside the mechanical backing named in `I-Outcome-1`. **Suggested revision:** Extend the shared guard to `larch_log_commit_main()` (preferred: one fix covers Step 7a and any other direct commit callers), or gate Step 7a's commit on a successful/non-forbidden refresh. Add `python/larch/report/run_log_commit.py` to the plan's firm file list and cover the Step 7a seam in tests.



### FINDING_7:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/step_7a.py:235-250
- **Concern**: Step 7a direct commit still bypasses the new pre-terminal guard. Scenario: When `flush_logs_pre()` refuses a staged `final-summary.md` with a forbidden label, Step 7a only marks the flush degraded and then still invokes `python/cli.py run-log commit`; `larch_log_commit_main()` calls `_commit_run()` directly, so the forbidden staged summary can still publish.
- **Proposed resolution**: Add a firm plan step to guard the Step 7a direct commit path, either by applying the same pre-terminal label check in `larch_log_commit_main()` for implement tmpdirs before `_commit_run()`, or by making Step 7a skip the direct commit after this specific pre-terminal refusal, with a focused regression for that path.



### FINDING_8:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: minor
- **Focus area**: correctness
- **Location**: plan.txt:42-45
- **Concern**: Reference sweep is not documented in the PR body. Scenario: The acceptance criteria require the `G-Orch-4|G-Obs-4` sweep to be documented in the PR body, but the plan only says to run and update the sweep. The implementation can pass code/tests while still missing this required acceptance artifact.
- **Proposed resolution**: Add a firm PR-description step that records the exact reference-sweep command and result in the PR body.



