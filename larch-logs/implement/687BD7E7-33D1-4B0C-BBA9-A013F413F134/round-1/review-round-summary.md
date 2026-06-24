# Review Round 1

- Mode: `diff`
- 5 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Load contracts placed after background fences
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Read-and-apply load contracts for `design-background-wait.md` sit after `run_in_background` fences in `skills/design/SKILL.md` (586–601, 643–660, 302–317, 854–870), contradicting the plan to load shared anchors before background work and to read the Step 3 task-notification boundary before the Step 3 fence. A literal orchestrator can launch `design-step3-review.sh` / `design-step5c.sh` / `design-step-final-summary.sh`, get the background ack, and end the turn or probe without the shared wait rules, risking pre-notification table emit, polling, or other contract violations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Move all Read and apply ## blocks and Parameters above each background fence; add harness checks that each load directive precedes its fence anchor.

---


### FINDING_2: Final summary missing inlined WAIT-when-absent recovery prose
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-dyn-design-wait-contracts-output.txt
- **Severity**: important
- **Concern**: Final summary `extra_guards` is a meta-instruction to keep the WAIT-when-absent clause instead of inlining the hot-path prose removed during dedup. The shared anchor (`skills/shared/design-background-wait.md`) does not contain that clause and ends premature-notification recovery with weaker “When absent, yield without `ps` polling” guidance. On a premature `<task-notification>` with non-empty task output during final-summary background wait, a foreground probe may return `WAIT` while `.completed/step-final-summary` is still absent; without explicit “`WAIT` when absent is expected” guidance, the orchestrator may treat the probe as failure and fall into forbidden recovery (polling, aggressive re-probing, or improvised waiters) instead of yielding until the next notification.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Inline the full WAIT-when-absent recovery sentences in the Final summary parameter block or shared anchor; assert them in the anti-polling harness at that locus.
  - From cursor-specialist-edge-cases-output.txt: Inline the full clause: `WAIT when absent is expected. When present, proceed to marker extraction or the Read fallback. When absent, yield without ps polling.` in extra guards (or parameterize it in the shared anchor) and add a harness context grep at the Final summary locus.
  - From cursor-specialist-testing-output.txt: Restore the full WAIT-when-absent sentence in the Final summary Parameters/extra-guards block and add a harness assertion at that locus.
  - From dyn-dyn-design-wait-contracts-output.txt: Inline the full `WAIT when absent is expected. When present, proceed to marker extraction or the Read fallback. When absent, yield without ps polling.` text in the Final summary parameter block (or add a dedicated `{wait_when_absent}` parameter to the shared anchor and expand it at that site). Add a harness assertion that `skills/design/SKILL.md` still contains that literal near the Final summary block.

---


### FINDING_4: Step 3 launch harness anchor can match resume fence
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: In `scripts/test-implement-anti-polling-rule.sh` (165–193), the Step 3 launch anchor is a prefix of the resume fence, so launch assertions can match the resume block instead. If the first launch block loses its load directives while the resume block stays intact, the harness still passes and the required five-locus verification is incomplete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Anchor the launch check to an exact non---starting-round fence, or make the helper select only design-step3-review.sh lines without --starting-round before checking context.

---


### FINDING_5: Final summary probe semantics disagree (durable vs completion)
- **Reviewer(s)**: dyn-dyn-design-wait-contracts-output.txt
- **Severity**: important
- **Concern**: The retained local pre-wait paragraph at `skills/design/SKILL.md:306` says a foreground probe “may confirm **durable** completion”, while the shared-anchor parameter uses `confirmation purpose: completion`, which renders as “may confirm **completion**” in `skills/shared/design-background-wait.md:15`. The two instructions sit back-to-back and can disagree on what a successful probe means; the plan’s edge case called for preserving the Final-summary carve-out verbatim, not paraphrasing it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-design-wait-contracts-output.txt: Change the Final summary parameter to `confirmation purpose: durable completion` (and teach the shared anchor to accept that phrase), or remove the competing recovery sentence from line 306 so only the shared anchor governs probe semantics.

---


### FINDING_6: Harness does not assert WAIT-when-absent at Final summary locus
- **Reviewer(s)**: dyn-dyn-design-wait-contracts-output.txt
- **Severity**: important
- **Concern**: The expanded harness (`scripts/test-implement-anti-polling-rule.sh:154–163`) pins `confirmation purpose: completion` and shared-anchor presence at the Final summary locus but does not assert the plan-required `WAIT when absent` clause. That gap allowed the FINDING_2 regression to land while all 54 harness checks still passed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-design-wait-contracts-output.txt: Add a `check_context` (or `check`) assertion that the Final summary anchor window contains `` `WAIT` when absent is expected `` (or the exact legacy sentence), matching the plan edge case and failure-mode notes.

---


