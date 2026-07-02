### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/implement/checks_run_relevant.py:443
- **Concern**: `checks run-relevant` still maps `plan_review.py` / `plan_quality.py` changes to `test-revise-plan-with-waterfall`. Scenario: The plan deletes `revise_plan_with_waterfall_main`, removes `plan revise-waterfall` tests, and retires the Step 3 revise path, but leaves `_DIRECT_TARGET_RULES` row 443 and `Makefile` target `test-revise-plan-with-waterfall` (`pytest -k revise_waterfall`) unchanged. Any PR touching `python/larch/review/plan_review.py` or `python/larch/design/plan_quality.py` will still run that target and fail when zero revise tests match or the helper is gone.
- **Proposed resolution**: Add `### UPDATED: python/larch/implement/checks_run_relevant.py` to drop the `test-revise-plan-with-waterfall` rule (and any paired patterns that only existed for revise-waterfall). Retire or repoint the `Makefile` target; do not leave a dead harness in `make lint` / `checks run-relevant`.

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/coder_runner.py:426-431
- **Concern**: Three-tier review-fix waterfall still returns `CODER_STATUS=no-changes` on first successful tier with zero `stage_paths`. Scenario: The plan adds Codex→Cursor→Claude and its edge cases require that a successful Claude review-fix with no working-tree edits fall through to `main-agent-required`, not stop at `no-changes`. `apply_findings_with_coder` still returns immediately when any tier succeeds but `_collect_round_stage_paths` is empty, so a Codex/Cursor failure followed by Claude success-without-edits exits before `main-agent-required`, leaving accepted fixes unapplied.
- **Proposed resolution**: In `### UPDATED: python/larch/review/coder_runner.py`, change the no-edit branch so non-final automated tiers `continue` and only the last registry tier (or all tiers exhausted) may emit `main-agent-required`; add/adjust `test_review_and_fix.py` for Codex+Cursor fail, Claude success-no-edit → `main-agent-required`.

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-step35-settle.sh:198-218
- **Concern**: Accepted F7 fix remains incomplete: the plan adds a prompt-side pre-apply snapshot, but the prompt-side settle path that now handles default Gate B apply never restores that snapshot on dedup failure.. Scenario: After inline Gate B rewrites plan.txt, gate-b-dedup can fail before .gate-b-postapply-ready-N is written. The current settle wrapper returns dedup-revise with the mutated plan left in place, so resume can reapply findings or recover from already-mutated bytes instead of the pre-apply plan.
- **Proposed resolution**: Add skills/design/scripts/design-step35-settle.sh to the plan and restore $DESIGN_TMPDIR/plan-pre-apply-round-$GATE_B_ROUND.txt to plan.txt before returning on Gate B dedup failure, matching _run_dedup restore semantics.

### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/agents/_ci_launcher.py:958-965; python/larch/review/coder_runner.py:265-278
- **Concern**: The Claude review-fix launcher argv contract conflicts with the planned runner call: the launcher is specified to mirror launch-claude-lint-fix's argv, but _run_coder_claude is planned to pass --timing-task-kind.. Scenario: If the launcher mirrors lint-fix literally, argparse rejects --timing-task-kind and the Claude review-fix tier always fails before applying fixes, leaving the new third tier unusable.
- **Proposed resolution**: Either add --timing-task-kind with default claude-review-fix to launch-claude-review-fix, or remove the flag from _run_coder_claude and hardcode the timing task in the launcher.

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/coder_runner.py:426-431
- **Concern**: Claude tier no-changes path still terminates the waterfall early. Scenario: The plan Edge cases require that a write-capable Claude tier with exit 0 and no working-tree edits fall through to main-agent-required, but the UPDATED coder_runner.py section only adds _run_coder_claude. apply_findings_with_coder still returns CoderResult(status=no-changes) whenever a tier returns True with empty stage_paths, so Codex→Cursor→Claude can stop at Claude no-changes and never reach main-agent-required.
- **Proposed resolution**: In Codex and Cursor fail, Claude launch-claude-review-fix exits 0 without edits, /implement Step 5 or /review review-and-fix reports CODER_STATUS=no-changes instead of escalating, leaving accepted findings unapplied. Add an explicit UPDATED coder_runner.py step: when the Claude tier succeeds with no stage paths, continue the waterfall (do not return no-changes). Prefer handling inside _run_coder_claude or a Claude-only branch; extend test_review_and_fix.py with a Claude no-op fallthrough assertion.

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/implement/checks_run_relevant.py:443
- **Concern**: Relevant-checks mapping still pins deleted revise-waterfall harness. Scenario: The plan removes plan revise-waterfall and its tests but does not list UPDATED checks_run_relevant.py. Line 443 still maps plan_quality.py/plan_review.py changes to make test-revise-plan-with-waterfall, which runs pytest -k revise_waterfall.
- **Proposed resolution**: After the deletion, any local or CI checks run-relevant pass touching plan_review.py or plan_quality.py invokes a harness whose tests were removed, failing the run despite unrelated edits. Add ### UPDATED: python/larch/implement/checks_run_relevant.py; drop the test-revise-plan-with-waterfall tuple (and retire or no-op the Makefile target if nothing else needs it).

### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/agents/_ci_launcher.py:958-965
- **Concern**: Claude review-fix launcher argv contract conflicts with the planned caller. Scenario: The plan tells `_run_coder_claude()` to pass `--timing-task-kind claude-review-fix`, but the new launcher is specified to mirror `launch-claude-lint-fix` argv, which does not accept that flag. Argparse would reject the Claude tier before it can run, so the required Codex→Cursor→Claude review-fix waterfall is incomplete.
- **Proposed resolution**: Add `--timing-task-kind` to `launch_claude_review_fix_main` with default `claude-review-fix` and use it for timing, or remove the caller flag and hardcode the task kind in the launcher.

### FINDING_8:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/coder_runner.py:405; python/larch/agents/_ci_launcher.py:958-968
- **Concern**: Claude review-fix caller and launcher argv contracts disagree on --timing-task-kind. Scenario: The plan tells _run_coder_claude to pass --timing-task-kind claude-review-fix, but the proposed launch-claude-review-fix argv shape omits that flag. If the launcher mirrors launch-claude-lint-fix exactly, argparse rejects the Claude tier and the required Codex→Cursor→Claude waterfall never reaches Claude.
- **Proposed resolution**: Add --timing-task-kind to launch-claude-review-fix with default claude-review-fix and use it for timing, or remove the caller flag and hard-code the task kind in the launcher.

### FINDING_9:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/coder_runner.py:426-431
- **Concern**: Edge case requires no-changes fallthrough but `apply_findings_with_coder` update omits loop change. Scenario: Plan edge cases require that when an automated review-fix tier (especially Claude after Codex and Cursor fail) exits successfully with no working-tree edits, the waterfall must continue to `main-agent-required` instead of returning `CODER_STATUS=no-changes`. The `UPDATED: python/larch/review/coder_runner.py` section adds `_run_coder_claude` and registry order only; it does not change the early `return` at lines 426-431 when `stage_paths` is empty. Codex or Cursor can already stop the waterfall the same way today; adding Claude as the third tier extends that failure mode and can mark review-fix `complete` while accepted findings remain unapplied.
- **Proposed resolution**: In `apply_findings_with_coder`, replace the successful `no-changes` early return with `continue` to the next `review.fix_coder` tier (after failed-attempt cleanup), reserving `main-agent-required` for exhaustion of all tiers. Add or adjust `test_review_and_fix.py` waterfall coverage to assert Codex→Cursor→Claude→`main-agent-required` when the last tier succeeds with no edits.

### FINDING_10:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:63-69,88-94
- **Concern**: Claude review-fix caller passes a flag the planned launcher shape omits. Scenario: `_run_coder_claude()` is planned to call `agent launch-claude-review-fix --timing-task-kind claude-review-fix`, but the new launcher is planned to mirror lint-fix argv shape with only `--prompt-body-file`, `--output`, `--timeout`, and `--model`. If implemented that way, argparse rejects the Claude tier and the required Codex→Cursor→Claude review-fix waterfall is broken.
- **Proposed resolution**: Add `--timing-task-kind` to the planned `launch_claude_review_fix_main` argv contract with default `claude-review-fix`, or remove the caller flag and hardcode that timing kind inside the launcher.
