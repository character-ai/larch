# Review Round 1

- Mode: `diff`
- 4 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_2: Step 5 coder runners called with positional args after keyword-only refactor
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: blocking
- **Concern**: Keyword-only coder runner functions are still invoked positionally at `review_and_fix.py:2193`. Any Step 5 round with an in-scope accepted finding raises `TypeError` before Cursor or Codex can apply fixes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Call runner with `round_dir=round_dir`, `prompt_body=prompt_body`, and `tool_log=tool_log`, or keep the runner signatures positional-compatible.


### FINDING_4: Structure harness missing Step 7 invalid-envelope STALL_STEP=7 pin
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: important
- **Concern**: Plan acceptance requires Step 7 invalid-envelope fail-closed pins with `STALL_STEP=7`. The harness only pins `STALL_STEP=5` for self-review. A SKILL edit could remove Step 7 prompt-side `STALL_STEP=7` / skip-to-18 invalid-envelope handling while structure lint still passes, leaving seed-failure paths without orchestrator teardown at Step 7.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add `require(skill, 'set prompt-side `STALL_TRACKING=true` and `STALL_STEP=7` when durable seed is absent, and skip to Step 18', 'SKILL Step 7 invalid envelope fail-closed')` next to the existing `STALL_STEP=5` pin.


### FINDING_7: _step5_resume_commit_phase ignores non-zero returncode on NEXT_ACTION=continue
- **Reviewer(s)**: dyn-dyn-commit-route
- **Severity**: important
- **Concern**: `_step5_resume_commit_phase` treats a single `NEXT_ACTION=continue` as success and returns `None` without checking `commit_result.returncode`. `step5_resume_main` can relaunch `review-and-fix step5` when nested `implement commit-route` exits non-zero but still printed `NEXT_ACTION=continue`. The shell wrapper (`step-5-resume.sh:116-118`) and SKILL lacks-envelope branch 4 block this; Python parity is broken for harnesses or direct `step5_resume_main` callers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-commit-route: In `_step5_resume_commit_phase`, fail closed on the continue branch when `commit_result.returncode != 0` (mirror the shell wrapper and branch 4), and add a `test_step5_resume_*` case with `route_rc != 0` plus `NEXT_ACTION=continue` asserting no `review-and-fix step5` relaunch.


### FINDING_8: _step5_resume_commit_phase relays duplicate or malformed NEXT_ACTION before validation
- **Reviewer(s)**: dyn-dyn-commit-route
- **Severity**: important
- **Concern**: `_step5_resume_commit_phase` relays all captured stdout (including any `NEXT_ACTION=` lines) before validating envelope cardinality or token value, so duplicate or malformed `NEXT_ACTION` output is forwarded verbatim to the orchestrator. `test_step5_resume_duplicate_next_action_fails_closed` expects two `NEXT_ACTION=continue` lines on stdout. The shell wrapper avoids that on happy paths by printing `NEXT_ACTION` once and using `relay_commit_kvs_without_next_action`. That weakens the exactly-one line-anchored `NEXT_ACTION=` contract the SKILL pins for self-review, Step 7, and resume lacks-envelope routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-commit-route: Parse and validate `NEXT_ACTION` first, then relay commit KVs with `include_next_action=False` and emit exactly one routing line (match `step-5-resume.sh:114-115` / `120-122`), or dedupe so stdout never contains more than one `NEXT_ACTION=` even on invalid-envelope returns.


