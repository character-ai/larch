### [rejected] FINDING_1

**Rejected subtype:** dismissed (0 YES)

### FINDING_1: Step 3 repeats still hit the probe branch
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-bg-wait
- **Severity**: important
- **Concern**: The generic Step 3 probe path still comes before the repeat-fingerprint silent-yield exception, so byte-identical non-empty notifications can keep burning turns instead of taking the silent-yield path first.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Require one probe on the first non-empty notification; allow silent-yield on repeats only after a prior WAIT while the marker is live; run post-notification when a prior probe returned DONE.
  - From cursor-specialist-edge-cases: Add one deferral sentence in #4 pointing byte-identical repeats to #5 and design-background-wait.md.
  - From cursor-specialist-testing: Qualify routing: fingerprint silent-yield first; probe only on first/changed non-empty notification
  - From cursor-specialist-testing: Reorder or add evaluate-fingerprint-before-probe lead-in
  - From cursor-specialist-testing: Add #4 carve-out deferring byte-identical repeats to design-background-wait.md #5418
  - From dyn-dyn-bg-wait: Pin evaluation order explicitly in all three surfaces: empty output → silent yield; byte-identical repeat with absent terminal sentinel → silent yield; first/changed non-empty premature notification → at most one foreground probe; terminal sentinel confirmed present → post-notification sequence. Move the fingerprint check above the probe paragraphs in `design-background-wait.md` and replace “yield or probe” in `skills/design/SKILL.md:413` with that ordered decision tree.
  - From dyn-dyn-bg-wait: Restore an explicit two-branch Apply block in anti-pattern #5: silent yield for empty output or byte-identical repeat with absent terminal sentinel; one non-sleeping terminal-sentinel probe only for the first or changed non-empty premature notification in the wait sequence.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** dismissed (0 YES)

### FINDING_2: Silent-yield turns can trip the no-progress breaker
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: important
- **Concern**: Silent-yield turns still count toward the no-progress circuit breaker while bg-wait-active is live, so long identical-notification runs can arm the breaker before the wrapper exits and stall the session.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Document guard interaction or note auto-disarm on sentinel; consider whether repeated silent yields should be excluded from the counter.
  - From cursor-specialist-edge-cases: Document that silent yields count toward the breaker; explain the sentinel/sidecar gap during normalize-to-EXIT; give operator recovery when waits exceed the default threshold.
  - From cursor-specialist-testing: Document that silent yields count toward hook-no-progress-guard threshold


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** dismissed (0 YES)

### FINDING_3: Later waits still reuse the Step 3 sentinel
- **Reviewer(s)**: codex-specialist-testing, dyn-dyn-bg-wait
- **Severity**: important
- **Concern**: The repeat-fingerprint rule lives in the shared wait anchor with a hard-coded Step 3 terminal sentinel, so Step 4, Step 5c, and final-summary waits can hit the wrong branch or skip their own post-notification sequence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Scope the rule to the Step 3 subsection only, or parameterize it on the active terminal sentinel before reusing the shared anchor.
  - From dyn-dyn-bg-wait: Scope anti-pattern #5 to Step 3 only, or parameterize the sentinel per fence (for example “unconfirmed `{terminal_sentinel}` for the active wait”) and align Step 5c / Step 4 / final-summary call sites with the same fingerprint rule.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

