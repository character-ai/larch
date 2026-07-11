# Review Round 2

- Mode: `diff`
- 5 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Architectural-guidelines harness still asserts retired prompt-side normalization
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-step8-route
- **Severity**: major
- **Concern**: The architectural-guidelines harness still searches for prompt-only normalization prose that was replaced by the executable `normalize-assessment-handoff` fence. The harness fails immediately or no longer verifies the active normalization, alias-canonicalization, stdout-binding, and terminal-validation contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-step8-route: Update the harness to assert the normalization Bash fence (`ship normalize-assessment-handoff`), pin legacy-alias behavior via Python tests or fixture handoffs, and match SKILL’s current validation wording (`normalization fence's canonical Piece 2 order`, `ASSESSMENT_RESULTS` coverage).


### FINDING_2: Fence-shape harness is stale and does not enforce executable normalization ordering
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-step8-route
- **Severity**: major
- **Concern**: The fence-shape harness expects 28 fences and retired normalization prose, while the executable normalization fence brings the count to 29. Its ordering assertion does not require `normalize-assessment-handoff` before `step-8-assessment.sh`, so CI cannot enforce the normalize → adapter → validate → single-relaunch sequence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-step8-route: Replace the stale substring with anchors for `ship normalize-assessment-handoff` and `step-8-assessment.sh`, assert exactly one of each in the assessment slice, and keep the forbidden prompt-side wait/compose checks.


### FINDING_3: Expected assessment kinds are not bound to normalization stdout
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-step8-route
- **Severity**: major
- **Concern**: Post-normalization validation can be read as requiring the fixed pair `invariants,guidelines` rather than the actual requested kinds. Single-kind routes may therefore be falsely rejected or compared against raw `DETAIL` order. The orchestrator should capture `ASSESSMENT_REQUESTED_KINDS` from normalization stdout and use that exact binding for adapter-result validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-step8-route: Require parsing `ASSESSMENT_REQUESTED_KINDS` from the normalization fence stdout, compare adapter terminal `ASSESSMENT_REQUESTED_KINDS` and `ASSESSMENT_RESULTS` only to that binding (order-independent canonical set when both kinds are requested), and drop the hard-coded `(invariants,guidelines)` example.


### FINDING_6: Adapter behavior changed outside the declared frozen scope
- **Reviewer(s)**: cursor-specialist-testing, dyn-dyn-step8-route
- **Severity**: major
- **Concern**: The frozen Piece 3 adapter was changed to reject whitespace in kind tokens, despite the plan declaring Pieces 1–3 runtime-frozen and the approved scope excluding this adapter change. The behavior change lacks corresponding integration coverage and may diverge from the approved contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-step8-route: Either revert the adapter change and keep whitespace rejection only in the normalization CLI, or explicitly fold the adapter change into the contract with `test-step-8-assessment.sh` coverage and scope documentation so prompt and runtime stay atomically coupled.


### FINDING_7: Handoff rewrite uses a predictable symlink-following temporary file
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: major
- **Concern**: The atomic handoff rewrite uses a predictable temporary path that may follow a symlink. A same-UID attacker could redirect `.ship-route-exit-handoff.env.tmp` to another writable file and cause normalization to overwrite it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Use larch_io.trusted_atomic_write rooted at implement_tmpdir or an equivalent no-follow descriptor-relative write, and add a symlink-temp regression test.
