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

### FINDING_2: Lint manifest and test fixtures can drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `scripts/lint-readability-preamble.sh` and `scripts/test-lint-readability-preamble.sh` duplicate manifest path data, so a new lint row can be added without corresponding regression coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: lint-readability-preamble runs twice under make lint
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `make lint` invokes `lint-readability-preamble` directly and also through the always-run pre-commit hook, adding duplicate cost.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

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

### FINDING_6: Brainstorm and dialectic docs encode the same risky global substitution contract
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: The documented brainstorm/dialectic assembly contract appears to rely on replacing every literal `<READABILITY_STYLE>`, matching the renderer behavior that can bloat prompts or leave literals when the real preamble contains the token.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_7: External-prompt lint only checks one match per file
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `lint-readability-preamble.sh` can pass when a file contains any matching readability line, even if individual sketch slots or sections lose their own readability directive.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_8: Missing or empty readability preamble fallback lacks robust coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Tests do not sufficiently cover missing, unreadable, or empty preamble behavior. The renderer can emit valid-looking prompts with a literal readability anchor instead of failing closed or producing a clear guarded output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_9: Sketch and dialectic assembly lack structural substitution tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Sketch and dialectic prompt expansion depends on orchestrator behavior, but there is no structural test asserting assembled prompts include the preamble excerpt and contain no literal token.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_10: READABILITY_STYLE_FILE can exfiltrate arbitrary local files
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `READABILITY_STYLE_FILE` allows any readable local file to be loaded into externally dispatched plan-review prompts. If set to a secret path, the rendered prompt can leak file contents to third-party review tools.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] Orchestrator-inline lint allows stale per-step directives
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The orchestrator-inline lint can pass with one readability match per file even if a specific per-step readability directive is removed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
