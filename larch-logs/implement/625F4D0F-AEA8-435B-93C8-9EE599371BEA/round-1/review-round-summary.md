# Review Round 1

- Mode: `diff`
- 4 accepted, 6 rejected (6 exonerated)

## Accepted Findings

### FINDING_1: Sketch style requirements are outside substituted prompt bodies
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The readability style lines in `skills/design/references/sketch-prompts.md` are outside the quoted ARCH/EDGE/INNOVATION/PRAGMATIC prompt bodies, while launch assembly substitutes only those quoted bodies. HARD sketch launches can therefore omit `<READABILITY_STYLE>` and readability guidance even though lint passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_4: Plan-review renderer recursively expands readability tokens
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `render-plan-review-prompt.sh` performs global second-pass replacement of `<READABILITY_STYLE>`, so literal tokens inside the inserted preamble are expanded too. Production prompts can contain duplicated preamble text and remaining literal tokens while tests miss the issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_5: Plan-review fixture omits production-like readability tokens
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The `test-plan-review-prompt.sh` fixture preamble does not contain `<READABILITY_STYLE>`, so tests do not exercise the production substitution behavior that causes duplicated preambles or stray literal tokens.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_7: External-prompt lint only checks one match per file
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `lint-readability-preamble.sh` can pass when a file contains any matching readability line, even if individual sketch slots or sections lose their own readability directive.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


