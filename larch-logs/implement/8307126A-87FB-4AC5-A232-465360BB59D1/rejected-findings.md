### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: Voter 1 synthetic `.done` backfill lacks clear launcher attestation semantics
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The dispatcher-owned Voter 1 `.done` backfill can make a voter look launched without a launcher-owned sentinel, and the behavior is not documented or logged. This creates ambiguity for operators diagnosing races and may mask abnormal launcher behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_3: Missing hook-delay regression coverage for plan FINDING_4
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `scripts/test-dispatch-code-voters.sh` has a hook test named for the delayed `.done` race, but it only sources an exit-143 case. A regression in delayed `.done` promotion after `.txt` output would not be caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_4: Wall-clock wait assertion can false-fail near second boundaries
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-dispatch-code-voters.sh` uses `date +%s` with a `< 1` threshold for a 1-second stub delay. On slow or contended runners, a delay finishing within the same second can make the happy-path shard fail incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Cursor stdin test is weaker than the inherit-stdin contract
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-run-external-agent.sh` only checks that fd 0 is not `/dev/null`. A pipe or wrong fd could pass while still breaking the intended inherit-stdin behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: No red-green evidence for new tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The plan lacks an automated or documented check that the new tests fail on `main`. Tests that pass on both `main` and the branch could provide false confidence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: Voter 2 skipped status is referenced but not assigned locally
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `scripts/dispatch-code-voters.sh` checks skipped Voter 2 status for the wait list, but this script does not assign that status. Future skipped wiring that omits wait inclusion could reintroduce the Voter 2 race.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: Fixed 60-second sentinel wait may force degraded voting on slow hosts
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The non-blocking sentinel timeout can mark all voters failed and force main-agent-vote-required on loaded CI or slow hosts even when voters are recoverable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

