# Review Round 2

- Mode: `diff`
- 9 accepted, 5 rejected (2 neutral)

## Accepted Findings

### FINDING_10: retargeted finalize/cleanup harnesses stub the wrong dispatcher path
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Several retargeted harnesses create or reference a malformed `python/cli.py` stub path, so the tests either fail during fixture setup or fail to exercise the production dispatcher path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_11: external reviewer degraded-tools prose still invokes retired read-key helper
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `skills/shared/external-reviewers.md` still instructs degraded-tools rehydration through deleted `scripts/read-session-env-key.sh`, causing followers of the shared doc to invoke a missing helper.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_12: deferred sourced-only libs follow-up issue is not filed or recorded
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The deferred migration follow-up for sourced-only bash libraries is not tracked or linked as required, leaving no recorded owner/DAG for the remaining migration work and incomplete closure for the parent scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_13: Python session CLI pytest replacement lacks migrated harness coverage
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The replacement pytest suite does not cover all plan-mandated migrated session behaviors, including design-env refresh preservation, setup/caller-env/repo fallback, local-cleanup behavior, invalid run-id rejection, and related read-classification/default paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_19: design plan review panel fixture chmods nonexistent cli path
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `skills/design/scripts/test-dispatch-plan-review-panel.sh` builds a bad fixture path for the migrated `python/cli.py` reader and aborts under `set -e` before testing reviewer fallback behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_20: design postplan emit fixture still stubs retired read-design-classification.sh
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `skills/design/scripts/test-design-postplan-emit.sh` still stubs the deleted bash classification reader while the subject reads through `python/cli.py`, so classification cases may not exercise the migrated path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_24: session setup crashes when gh is missing instead of using repo fallback
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `session setup` does not catch missing `gh` before attempting repo fallback, so environments without `gh` but with a valid git origin crash instead of using the intended fallback path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_7: implement NEVER prose still names retired session helpers
- **Reviewer(s)**: codex-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `skills/implement/SKILL.md` still describes deleted bash helper surfaces and/or sourcing `session-env.sh`, so future prompt-side repair work could follow stale trust-boundary instructions instead of the Python session CLI contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_8: release cleanup invokes python/cli.py without python3
- **Reviewer(s)**: codex-specialist-security-output.txt, cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `.claude/skills/release/SKILL.md` calls `python/cli.py` as an executable even though the dispatcher is not executable / lacks a shebang, causing release local-cleanup to fail and leaving the local release branch behind.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.


