### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: Phase 1 include-probe evidence and BRANCH decision not retained on a committed path
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: No committed artifact reproduces the Phase 1 BRANCH decision or per-agent transcripts from the ephemeral tmpdir; plan acceptance expects evidence (for example results with BRANCH and transcripts) so post-merge audit and reviewers cannot verify cross-agent include probes, strict decision rules, or that Branch B followed from failed gate conditions versus skipping Phase 1 using git or the PR alone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: AGENTS.md polling / ScheduleWakeup bullet still more verbose than needed for Branch-B trim
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Under the 11000-character budget, the polling / ScheduleWakeup bullet keeps more wording than necessary versus a minimal trim; less headroom is reclaimed than possible while preserving canonical pointers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: AGENTS.md anti-polling bullet lost nuance not fully duplicated in cited NEVER / BASH passages
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: The shortened anti-polling bullet no longer states nuanced failure modes (duplicate task notifications, stale poller, ScheduleWakeup as pseudo-/loop input); those are not fully duplicated in the cited NEVER #9, BASH_AUTHORING §4, and NEVER #16 passages, so operators who never open the harness doc may under-weight original #1011 motivation distinct from foreground-marker rules.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: AGENTS.md trimmed orchestration bullets may under-weight incidents unless one short outcome clause remains visible
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Incident-level rationale for orchestration NEVER rules (polling, ScheduleWakeup, session-env, session safety) moved mostly behind SKILL.md / BASH pointers; models or humans that reason only from AGENTS and skip linked files may under-weight concrete failure signatures and worst-case outcomes that previously discouraged mistakes at first read, within character budget constraints.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: Canonical sources list has uneven gloss for voting / point-competition paths
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: At AGENTS.md around the canonical sources list, voting and point-competition docs appear as bare paths while other entries carry gloss, weakening skimming UX and making it harder to pick the right doc from the list alone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: Session-env bullet lost compact script or symptom anchors for AGENTS-only triage
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: The session-env bullet no longer names representative scripts or missing-key symptom strings, so grep- or runbook-driven triage from AGENTS alone is weaker unless readers defer entirely to SKILL NEVER #14.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

