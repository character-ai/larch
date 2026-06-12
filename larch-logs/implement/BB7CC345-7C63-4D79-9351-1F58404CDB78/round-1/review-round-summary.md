# Review Round 1

- Mode: `diff`
- 1 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Step 5 can route Step 2 protected-path recovery to shipping
- **Reviewer(s)**: codex-specialist-correctness-output.txt, dyn-architecture-output.txt
- **Severity**: important
- **Concern**: Protected-path Step 2 recovery still appears in a Step 5 flow that defaults to re-invoking `step-8-ship.sh`. That can send orchestrators to shipping before inline implementation has happened.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Split dispatch by RESUME_HINT so step2-impl records escalation and runs Main Claude inline, and only step8-shippr invokes step-8-ship.sh.
  - From dyn-architecture-output.txt: Split Step 5 into explicit `RESUME_HINT` branches (e.g. `step2-impl` → inline Step 2 per `SKILL.md` NEVER #18; `step8-shippr` → `step-8-ship.sh`), and demote the ship re-invoke text to the `step8-shippr` branch only.


