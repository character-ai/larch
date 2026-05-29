### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: No dedicated harness for hex-encoded P3119 patterns
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: No offline harness exercises hex-encoded pattern pass/fail paths; helper regression (broken `printf` patterns) could noop assertions silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: Hex-encoded patterns vs literal `fail()` diagnostics
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Hex-encoded detection coexists with literal `fail()` text on line 24, which is inconsistent and harder to maintain: structure failures require decoding hex while the grep gate still matches the literal fail line.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Sourced `lib-p3119-fence-absence.sh` lacks script-md sibling
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The sourced library has no sibling `.md` contract unlike peer `lib-*` helpers. `agent-lint` and contributors expect script-md-sibling docs for sourced libraries, increasing discovery and audit cost.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Timeout/autobackground recovery may re-invoke ship-pr before task-notification
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Stage 4 fence collapse removes in-fence shell `background`/`wait` coupling for long-running implement scripts (`ship-pr.sh`, `run-step5-review.sh`, `run-step2-dispatch.sh`), relying on harness auto-background and task-notification. When `ship-pr.sh` exceeds the Bash timeout, the harness auto-backgrounds and returns a non-contract exit; orchestrator prose (including NEVER #16 / Step 8+) can direct same-turn re-invoke without waiting for task-notification, while `AGENTS.md` requires notification-first completion. A prior auto-backgrounded `ship-pr` may still be running, producing dual writers racing on `ship-pr-state.sh` and git, weakening the single-runner invariant and risking interleaved `git`/`gh` publication state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: Step 8+ exit routing when Bash `writer_rc` and `ship-pr-state` disagree
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: After timeout or auto-background, Bash may return `124`/`143` while `ship-pr.sh` is still running and `ship-pr-state.sh` has stale `PHASE`/`EXIT_CODE`. Dual exit authority between process exit and state is not reconciled for non-contract Bash exits; orchestrator may follow Bash return, miss Exit 4/6 branches, or Step 18a classification may default `EXIT_CODE` to 0. The Exit 0–6 matrix should key off `EXIT_CODE` and related keys from `ship-pr-state.sh` after a completed invocation; on timeout or in-progress `PHASE`, use NEVER #16 resume—not matrix branches from `writer_rc` alone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

