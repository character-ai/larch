### [Plan Review] FINDING_3

### FINDING_3: `ci-fix-exhausted` omits `BAIL_FAILURE_DETAIL_LOG` expected by Step 8
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Concern**: The autonomous Step 8 path in `skills/implement/SKILL.md:1169-1175` expects redaction and reading of `BAIL_FAILURE_DETAIL_LOG`, but the plan only sets `BAIL_REASON=ci-fix-exhausted` before exit 3 at `scripts/ship-pr.sh:2679-2693`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: When setting ci-fix-exhausted, also set BAIL_FAILURE_DETAIL_LOG to a tmpdir diagnostic log, or update Step 8 to treat that supplemental log as optional for this token.


### [Plan Review] FINDING_6

### FINDING_6: `ci-fix-exhausted` autonomous path is out of minimum scope for this PR
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: The minimum fix is gating blind rerun so deterministic failures enter the existing fix loop. Expanding into a new `ci-fix-exhausted` exit-3 bail token, orchestrator trigger, Python status, and Step 8 prose broadens behavior after fixes are already exhausted and increases loop/triage risk without being required to stop no-fix rerun churn.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Keep this PR to the transient-vs-deterministic rerun gate. Leave max-retries as the existing stall path and defer ci-fix-exhausted autonomous routing to a separate design if still wanted.


