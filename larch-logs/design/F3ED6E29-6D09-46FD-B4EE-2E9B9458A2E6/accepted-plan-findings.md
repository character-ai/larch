### FINDING_1: Plan-review prompts miss the real renderer
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Edge, Codex-Edge, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-token-render-pipeline, Codex-dyn-token-render-pipeline, Cursor-dyn-amendment-coverage, Codex-dyn-amendment-coverage, Cursor-dyn-lint-manifest-soundness
- **Severity**: important
- **Concern**: The plan-review readability amendment targets `skills/design/references/plan-review.md`, but the runtime external reviewer prompts are emitted by `skills/design/scripts/render-plan-review-prompt.sh` and dispatched from rendered prompt files. Updating only the reference doc can leave static and dynamic plan-review agents without the readability preamble while lint still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an UPDATED subsection for render-plan-review-prompt.sh (inject readability guidance or <READABILITY_STYLE> plus substitution) and extend test-plan-review-prompt.sh; keep plan-review.md changes only if they document the renderer contract
  - From Codex-Arch: Add the readability preamble injection to render-plan-review-prompt.sh itself and pin it in test-plan-review-prompt.sh; include this renderer in the lint manifest or otherwise check the rendered prompt surface.
  - From Cursor-Edge: Add the minimal renderer change to read skills/design/references/readability-style.md and inject it into the emitted prompt, and update test-plan-review-prompt.sh to assert rendered prompts contain the preamble and no raw <READABILITY_STYLE> token
  - From Codex-Edge: Add the minimal renderer change to read skills/design/references/readability-style.md and inject it into the emitted prompt, and update test-plan-review-prompt.sh to assert rendered prompts contain the preamble and no raw <READABILITY_STYLE> token
  - From Cursor-Pragmatic: Add an UPDATED entry for render-plan-review-prompt.sh: inline readability-style.md (or substitute <READABILITY_STYLE>) in the emitted prompt; extend scripts/test-plan-review-prompt.sh accordingly
  - From Codex-Pragmatic: Add render-plan-review-prompt.sh and its harness to the plan; read skills/design/references/readability-style.md and include or substitute it in the emitted heredoc
  - From Cursor-Requirements: Add render-plan-review-prompt.sh and test-plan-review-prompt.sh to the plan; read the shared preamble and inject the expanded style text into the heredoc, with a harness assertion that rendered prompts contain the style guidance and no raw <READABILITY_STYLE> token
  - From Codex-Requirements: Add render-plan-review-prompt.sh and test-plan-review-prompt.sh to the plan; read the shared preamble and inject the expanded style text into the heredoc, with a harness assertion that rendered prompts contain the style guidance and no raw <READABILITY_STYLE> token
  - From Cursor-dyn-token-render-pipeline: Move the plan-review prompt amendment and substitution into render-plan-review-prompt.sh, with test-plan-review-prompt.sh asserting the rendered prompt includes the expanded style text and not the token.
  - From Codex-dyn-token-render-pipeline: Move the plan-review prompt amendment and substitution into render-plan-review-prompt.sh, with test-plan-review-prompt.sh asserting the rendered prompt includes the expanded style text and not the token.
  - From Cursor-dyn-amendment-coverage: Amend render-plan-review-prompt.sh to load readability-style.md and emit the concrete style text in the rendered prompt, then update test-plan-review-prompt.sh to assert the rendered prompt contains it and no literal <READABILITY_STYLE>
  - From Codex-dyn-amendment-coverage: Amend render-plan-review-prompt.sh to load readability-style.md and emit the concrete style text in the rendered prompt, then update test-plan-review-prompt.sh to assert the rendered prompt contains it and no literal <READABILITY_STYLE>
  - From Cursor-dyn-lint-manifest-soundness: ### UPDATED: skills/design/scripts/render-plan-review-prompt.sh — inject style (or substitute `<READABILITY_STYLE>`) in the rendered body; extend test-plan-review-prompt.sh if needed


### FINDING_2: Prompt assembly sites lack token expansion
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation, Codex-Pragmatic, Cursor-dyn-token-render-pipeline, Codex-dyn-token-render-pipeline
- **Severity**: important
- **Concern**: Several proposed prompt edits add `<READABILITY_STYLE>` tokens without defining where those tokens are expanded before launch or write. Sketch, brainstorm, dialectic, and plan-review prompt paths can therefore send a literal token to agents instead of the shared readability preamble.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Update the plan to modify render-plan-review-prompt.sh and each prompt assembly instruction so <READABILITY_STYLE> is replaced with the full readability-style.md content before launch; pin rendered prompt tests against the expanded preamble
  - From Codex-Innovation: Update the plan to modify render-plan-review-prompt.sh and each prompt assembly instruction so <READABILITY_STYLE> is replaced with the full readability-style.md content before launch; pin rendered prompt tests against the expanded preamble
  - From Codex-Pragmatic: Add the minimum assembly instruction at each affected prompt-render path: read readability-style.md once and replace <READABILITY_STYLE> before launch or Write
  - From Cursor-dyn-token-render-pipeline: Add the minimum explicit expansion contract at each existing renderer/assembly point: read skills/design/references/readability-style.md and replace <READABILITY_STYLE> after existing prompt substitutions and before launch/write. Add focused harness checks that rendered prompts contain no literal <READABILITY_STYLE>.
  - From Codex-dyn-token-render-pipeline: Add the minimum explicit expansion contract at each existing renderer/assembly point: read skills/design/references/readability-style.md and replace <READABILITY_STYLE> after existing prompt substitutions and before launch/write. Add focused harness checks that rendered prompts contain no literal <READABILITY_STYLE>.


### FINDING_3: Lint is not wired into enforced validation paths
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation, Codex-Innovation, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Codex-dyn-lint-manifest-soundness
- **Severity**: important
- **Concern**: The plan describes the new readability guard as a pre-commit lint, but wires it only through Makefile-level targets. Normal enforcement paths use `.pre-commit-config.yaml`, `scripts/relevant-checks.sh`, `make lint-only`, and CI test-harness shards, so the guard and harness can be skipped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add a local pre-commit hook for scripts/lint-readability-preamble.sh, likely pass_filenames false and always_run true; keep the Makefile target as a convenience wrapper if desired.
  - From Cursor-Innovation: Add a local .pre-commit-config.yaml hook for scripts/lint-readability-preamble.sh with pass_filenames false and always_run true, or explicitly place the test target in a test-harnesses-N shard and revise the plan away from the pre-commit claim
  - From Codex-Innovation: Add a local .pre-commit-config.yaml hook for scripts/lint-readability-preamble.sh with pass_filenames false and always_run true, or explicitly place the test target in a test-harnesses-N shard and revise the plan away from the pre-commit claim
  - From Codex-Pragmatic: Add the lint as a pre-commit hook if it is meant to be pre-commit, and add the harness to exactly one test-harnesses-N shard; keep local make lint as the aggregate only
  - From Cursor-Requirements: Add a local .pre-commit-config.yaml hook for scripts/lint-readability-preamble.sh with pass_filenames false/always_run as appropriate, and assign test-lint-readability-preamble to one test-harnesses-N shard instead of relying only on the top-level lint target
  - From Codex-Requirements: Add a local .pre-commit-config.yaml hook for scripts/lint-readability-preamble.sh with pass_filenames false/always_run as appropriate, and assign test-lint-readability-preamble to one test-harnesses-N shard instead of relying only on the top-level lint target
  - From Codex-dyn-lint-manifest-soundness: Add a local `.pre-commit-config.yaml` hook for `scripts/lint-readability-preamble.sh`; put `test-lint-readability-preamble` in one `test-harnesses-N` shard instead of only adding both targets directly to `lint`


### FINDING_4: Approval gates are omitted from amendment coverage
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements, Cursor-dyn-amendment-coverage, Codex-dyn-amendment-coverage
- **Severity**: important
- **Concern**: `approval-gates.md` owns Gate A, Gate B, and Gate C operator-facing prose, including the Gate B plan rewrite and dedup path. Omitting it from amendment sites can let reviewed or final design text lose the required readability style.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add a MANDATORY read directive for readability-style.md before the Gate B Apply-all body/shared post-apply rewrite, and include approval-gates.md in the lint manifest as an orchestrator-inline site
  - From Codex-Requirements: Add a MANDATORY read directive for readability-style.md before the Gate B Apply-all body/shared post-apply rewrite, and include approval-gates.md in the lint manifest as an orchestrator-inline site
  - From Cursor-dyn-amendment-coverage: Add approval-gates.md to the amendment list and lint manifest, with the style directive placed before the Gate A, Gate B, and Gate C prompt bodies or a single file-level directive that clearly covers all three gate sections
  - From Codex-dyn-amendment-coverage: Add approval-gates.md to the amendment list and lint manifest, with the style directive placed before the Gate A, Gate B, and Gate C prompt bodies or a single file-level directive that clearly covers all three gate sections


### FINDING_5: Brainstorm synthesis instructions are covered in the wrong file
- **Reviewer(s)**: Cursor-dyn-amendment-coverage, Codex-dyn-amendment-coverage, Codex-dyn-lint-manifest-soundness
- **Severity**: important
- **Concern**: The proposed brainstorm synthesis directive is assigned to `SKILL.md` or external prompt docs, but the in-session synthesis and discussion-loop instructions live in `skills/design/references/brainstorm.md`. The writer of `$DESIGN_TMPDIR/brainstorm.md` may never be told to read the readability preamble.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-amendment-coverage: Add brainstorm.md to the amendment list and lint manifest, placing the mandatory readability read before the Synthesis and free-form discussion loop sections
  - From Codex-dyn-amendment-coverage: Add brainstorm.md to the amendment list and lint manifest, placing the mandatory readability read before the Synthesis and free-form discussion loop sections
  - From Codex-dyn-lint-manifest-soundness: Move that planned directive to `skills/design/references/brainstorm.md` immediately before `## Synthesis → brainstorm.md`, and include that file in the lint manifest as a MANDATORY-directive site


### FINDING_6: Pragmatic brainstorm prompt path is misclassified
- **Reviewer(s)**: Cursor-dyn-token-render-pipeline, Codex-dyn-token-render-pipeline
- **Severity**: important
- **Concern**: The plan treats all brainstorm slot prompt bodies as token-substitution sites, but `BRAINSTORM_PRAGMATIC_PROMPT` is an always-Claude parent-session path rather than an external prompt file path. That slot can receive a literal token or rely on unspecified parent-agent behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-token-render-pipeline: Either define <READABILITY_STYLE> expansion as part of assembling all three brainstorm slot prompts, including the parent-session pragmatic prompt, or change only the pragmatic slot to a MANDATORY read directive before composing its in-session output.
  - From Codex-dyn-token-render-pipeline: Either define <READABILITY_STYLE> expansion as part of assembling all three brainstorm slot prompts, including the parent-session pragmatic prompt, or change only the pragmatic slot to a MANDATORY read directive before composing its in-session output.


### FINDING_8: Lint manifest can false-pass on non-amendment files
- **Reviewer(s)**: Codex-dyn-lint-manifest-soundness
- **Severity**: important
- **Concern**: The lint manifest and grep contract do not explicitly exclude non-amendment files, including `readability-style.md`, lint docs, scripts, and tests. Including those files can satisfy token checks without proving any real prompt or orchestrator site uses the preamble.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-lint-manifest-soundness: Spell out the manifest as only real amendment sites and exclude `skills/design/references/readability-style.md`, `scripts/lint-readability-preamble.sh`, `scripts/lint-readability-preamble.md`, and the test harness; make each manifest row declare the expected variant


### FINDING_9: Lint grep patterns are too broad
- **Reviewer(s)**: Codex-dyn-lint-manifest-soundness
- **Severity**: important
- **Concern**: The proposed grep patterns for `<READABILITY_STYLE>` and mandatory readability reads can match examples, comments, contract prose, or documentation instead of the intended prompt-body or orchestrator-directive lines.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-lint-manifest-soundness: Use exact anchored checks for the intended line forms, such as `^Style requirements: \`<READABILITY_STYLE>\`\.$` for external prompt bodies and a line-start `**MANDATORY — READ ENTIRE FILE before ...: \`skills/design/references/readability-style.md\`.` pattern for inline directives


### FINDING_10: Lint harness lacks negative coverage per variant
- **Reviewer(s)**: Codex-dyn-lint-manifest-soundness
- **Severity**: important
- **Concern**: The lint harness specifies only one non-compliant fixture, so one accepted pattern branch can break while the lone negative fixture still covers only the other branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-lint-manifest-soundness: Split negative coverage into at least two isolated cases: one external-prompt fixture missing the token and one orchestrator-inline fixture missing the MANDATORY readability directive; assert the offending path for each


### FINDING_11: Sketch plan includes an unused generic prompt
- **Reviewer(s)**: Codex-dyn-lint-manifest-soundness
- **Severity**: latent
- **Concern**: The sketch plan includes `GENERIC_PROMPT`, but the current sketch prompt file has only four prompt bodies and SIMPLE mode launches no sketch prompt. Adding or linting a generic prompt would create an unused amendment site unless the PR intentionally changes SIMPLE sketch behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-lint-manifest-soundness: Drop `GENERIC_PROMPT` from the planned sketch-prompts change unless the PR also intentionally changes SIMPLE sketch behavior, which would exceed the minimum-change lane

