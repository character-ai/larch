### FINDING_1: Voter 1 backfill uses `_wait_rc` after cleanup
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `scripts/dispatch-code-voters.sh` unsets `_wait_rc` before the Voter 1 synthetic `.done` backfill gate still depends on it. Reviewers describe failure modes including `set -u` aborts, incorrectly creating `.done` after wait helper failure, or failing to backfill valid output, which can misclassify Voter 1 before tally.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: Voter 1 synthetic `.done` backfill lacks clear launcher attestation semantics
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The dispatcher-owned Voter 1 `.done` backfill can make a voter look launched without a launcher-owned sentinel, and the behavior is not documented or logged. This creates ambiguity for operators diagnosing races and may mask abnormal launcher behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_3: Missing hook-delay regression coverage for plan FINDING_4
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `scripts/test-dispatch-code-voters.sh` has a hook test named for the delayed `.done` race, but it only sources an exit-143 case. A regression in delayed `.done` promotion after `.txt` output would not be caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_4: Wall-clock wait assertion can false-fail near second boundaries
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-dispatch-code-voters.sh` uses `date +%s` with a `< 1` threshold for a 1-second stub delay. On slow or contended runners, a delay finishing within the same second can make the happy-path shard fail incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_5: Cursor stdin test is weaker than the inherit-stdin contract
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-run-external-agent.sh` only checks that fd 0 is not `/dev/null`. A pipe or wrong fd could pass while still breaking the intended inherit-stdin behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_6: No red-green evidence for new tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The plan lacks an automated or documented check that the new tests fail on `main`. Tests that pass on both `main` and the branch could provide false confidence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_7: Timeout stderr harness case is undocumented
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-run-external-agent.md` does not document case 18 for capture-stdout-only timeout stderr behavior, making the harness coverage harder to discover.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_8: Voter 2 skipped status is referenced but not assigned locally
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `scripts/dispatch-code-voters.sh` checks skipped Voter 2 status for the wait list, but this script does not assign that status. Future skipped wiring that omits wait inclusion could reintroduce the Voter 2 race.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_9: Fixed 60-second sentinel wait may force degraded voting on slow hosts
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The non-blocking sentinel timeout can mark all voters failed and force main-agent-vote-required on loaded CI or slow hosts even when voters are recoverable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] Breadcrumb monitor idle behavior remains deferred
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `scripts/breadcrumb-monitor.sh` may still let the orchestrator exit before `review-and-fix.sh` finishes when breadcrumbs go idle, but the reviewer marked this as deferred by plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] Plan voters lack the new `.done` wait barrier
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `scripts/dispatch-plan-voters.sh` does not have the new `.done` wait barrier, so `/design` plan-review voting could still tally before external voter completion if it has the same race.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_12: Branch contains unrelated work outside the implementation plan
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The branch includes orphan-script, Codex telemetry, parser, security, and test changes outside the #2973 implementation plan. This broadens review, release-note, rollback, and bisect risk beyond the planned voter-failure fix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_13: Changelog omits the primary voter/stdin/sidecar fixes
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `CHANGELOG.md` does not document the #2973 voter/stdin/sidecar fixes, while the visible 42.6.1 entry only mentions orphan-script work. Operators would not see the primary branch behavior in release notes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
