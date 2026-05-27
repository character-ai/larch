### FINDING_1: Runtime prompt assertion missing
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Codex-Innovation
- **Severity**: important
- **Concern**: The planned regression test greps launcher source rather than the rendered prompt passed to Codex, so the test can pass if the guard remains only in a comment, dead branch, or stale source text while disappearing from the actual prompt.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Assert against ${OUT_FIX}.prompt after the existing stub launch, and optionally verify non-fix rendered prompts if the guard is intended to be universal
  - From Codex-Edge: Add a runtime prompt assertion after the existing stubbed fix-role launch at scripts/test-launch-codex-ci.sh:75-82, grepping ${OUT_FIX}.prompt for the clause; keep or replace the source grep as secondary coverage
  - From Codex-Innovation: After the existing stub invocation writes ${OUT_FIX}.prompt, grep that prompt file for the phrase; keep or drop the source grep as secondary coverage

### FINDING_2: Misleading prompt-contract assertion helper
- **Reviewer(s)**: Codex-Arch
- **Severity**: nit
- **Concern**: The subprocess guard assertion is folded into a manifest-template helper and failure message, so a missing guard would be reported as a misleading manifest-template or self-validation failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Create a separate assert_prompt_contains_subprocess_guard helper or update the helper name and failure text to mention all three checked prompt contracts

### FINDING_3: Unescaped quotes break PROMPT assignment
- **Reviewer(s)**: Codex-Edge, Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: The planned inline PROMPT paragraph contains literal double quotes inside a double-quoted shell assignment, which can terminate the assignment or break shell syntax before Codex launches.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Either escape the inner quotes as \"stdin is closed for this session\" or change the PROMPT construction to a heredoc/command substitution that safely carries literal quotes
  - From Codex-Pragmatic: Revise the plan to escape the inner quotes as \"stdin is closed for this session\", remove the quote marks, or switch PROMPT construction to a quoted heredoc pattern before adding this paragraph
  - From Codex-Requirements: Specify the source form with escaped quotes, e.g. The \"stdin is closed for this session\" failure class, or refactor PROMPT construction to a heredoc while preserving variable expansion and add validation that the rendered prompt still contains the quoted sentence

### FINDING_4: Bail token omitted from manifest schema
- **Reviewer(s)**: Codex-Edge, Codex-Innovation
- **Severity**: important
- **Concern**: The planned stable bail_reason token is introduced in prompts but not added to the normative manifest schema token list, creating drift for docs, reviewers, operators, or downstream tooling that pattern-matches stable reasons.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Add interactive-subprocess-unsupported to the Bail-reason tokens section, or revise the planned prompt to make clear it is intentionally a free-form Codex-authored token and not a stable enumerated reason
  - From Codex-Innovation: Add interactive-subprocess-unsupported to codex-manifest-schema.md and codex-manifest-schema.digest.md with ownership semantics, and update any token-list harness if present

### FINDING_5: Codex-specific abort rule leaks to Cursor
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: The proposed Codex-only abort rule is placed in a shared hard-guard base that Cursor also copies, so Cursor implementers may inherit a non-negotiable abort instruction for a Codex-specific failure class.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Keep the new guard Codex-only by injecting it in scripts/generate-codex-implementer.sh or by adding a vendor-conditional base section filtered out by generate-cursor-implementer.sh; pin absence or non-abort wording in the Cursor artifact

### FINDING_6: Generator validation claim is false
- **Reviewer(s)**: Codex-dyn-generator-output-fidelity
- **Severity**: important
- **Concern**: The plan claims `make lint` transitively invokes `scripts/check-generators.sh`, but the cited targets do not run the real checker, so contributors can follow the plan’s validation and miss generated-artifact drift locally.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-generator-output-fidelity: Revise the plan to require explicit bash scripts/check-generators.sh or make agent-sync, or wire agent-sync/check-generators into lint if that is intended.

### FINDING_7: Walker has no --check mode
- **Reviewer(s)**: Codex-dyn-generator-output-fidelity
- **Severity**: latent
- **Concern**: The plan says `scripts/check-generators.sh` has a `--check` mode, but the walker rejects arguments; `--check` belongs to the registered generator scripts that the walker invokes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-generator-output-fidelity: Change the wording to say scripts/check-generators.sh invokes each registered generator in --check mode, or add and test a --check alias on the walker.

### FINDING_8: Markdown placement fallback targets wrong branch
- **Reviewer(s)**: Codex-dyn-sibling-md-placement
- **Severity**: important
- **Concern**: The planned fallback for `scripts/launch-codex-ci.md` can add a spurious new H2 even though existing `Interface` and `Behavior` sections already document prompt inputs and construction.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-sibling-md-placement: Revise the plan to name the exact placement: append the one-line bullet under ## Behavior after the fixed-prompt paragraph, or under ## Interface after the prompt-injection input descriptions; remove the conditional fallback for this file.
