### FINDING_1: run_lint_fix fixer dispatch must mirror lint-fix-loop.sh, not launch-*-ci.sh
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The proposed `run_lint_fix` path in `python/checks.py` does not specify fixer dispatch parity with live Bash. `lint-fix-loop.sh` dispatches local lint fixes through `run-external-agent.sh` with codex/cursor leaf argv (`run_codex` / `run_cursor` at `scripts/lint-fix-loop.sh:234-310`), including serial locks, cursor preflight (`cursor-wrap-prompt.sh`, model/auth setup), and related wrapper behavior. Routing through `agents.build_launch_argv` / `agents.launch_tier` and `launch-*-ci.sh` targets a different CI-fix surface. A “classifiers only” port that still launches via `launch_tier` / `run_waterfall` would diverge from production fixer behavior at Phase 7 cutover.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Spell out run-external-agent.sh argv parity for codex→cursor; use agents.classify_launch_failure (and related helpers) only for post-dispatch classification, not agents.launch_tier
  - From Cursor-Pragmatic: Spell out parity: shell out through `run-external-agent.sh` (mirror `run_codex`/`run_cursor` in `scripts/lint-fix-loop.sh:234-310`), reuse `agents` only for `classify_launch_failure` / transient checks; do not route local fix through `agents.launch_tier` / `run_waterfall`.


