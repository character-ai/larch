### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/checks.py (proposed run_lint_fix)
- **Concern**: Fixer dispatch unspecified vs lint-fix-loop.sh run_codex/run_cursor. Scenario: Using agents.build_launch_argv / launch-*-ci.sh (CI-fix role/plan-file surface) diverges from lint-fix-loop.sh, which shells to run-external-agent.sh with codex exec / cursor agent argv (scripts/lint-fix-loop.sh:234-310)
- **Proposed resolution**: Spell out run-external-agent.sh argv parity for codex→cursor; use agents.classify_launch_failure (and related helpers) only for post-dispatch classification, not agents.launch_tier

### FINDING_2:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:18
- **Concern**: `failure_reason` uses `head-changed` not bash `head-changed-after-dispatch`. Scenario: `run_check_fix_loop` will not map vendor HEAD moves to terminal `head-changed` / `TRANSIENT`; they become `dispatch-failed`
- **Proposed resolution**: Match `scripts/ship-pr.sh:202-203` and `scripts/lint-fix-loop.sh:436-451`; use `head-changed-after-dispatch` in `FixOutcome` and loop handling

### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:18-19
- **Concern**: `run_lint_fix` dispatch is underspecified vs `lint-fix-loop.sh`. Scenario: Bash dispatches via `run-external-agent.sh` with codex/cursor argv, serial locks, and cursor preflight (`cursor-wrap-prompt.sh`, model/auth setup). `agents.launch_tier` targets `launch-*-ci.sh` — a different surface. A “classifiers only” port would not match live fixer behavior at Phase 7.
- **Proposed resolution**: Spell out parity: shell out through `run-external-agent.sh` (mirror `run_codex`/`run_cursor` in `scripts/lint-fix-loop.sh:234-310`), reuse `agents` only for `classify_launch_failure` / transient checks; do not route local fix through `agents.launch_tier` / `run_waterfall`.
