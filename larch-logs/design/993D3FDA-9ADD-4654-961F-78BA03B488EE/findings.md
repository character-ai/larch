### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/test-launch-codex-ci.sh:75-82
- **Concern**: New CI prompt pin is planned as a source grep instead of checking the rendered prompt. Scenario: The test can pass if the phrase remains in a comment or dead code while the actual Codex prompt no longer carries the guard
- **Proposed resolution**: Assert against ${OUT_FIX}.prompt after the existing stub launch, and optionally verify non-fix rendered prompts if the guard is intended to be universal

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: skills/implement/scripts/test-codex-implementer.sh:22-30
- **Concern**: Subprocess guard assertion is folded into a manifest-template helper and failure message. Scenario: If the new phrase is missing, the harness reports a misleading manifest-template/self-validation failure
- **Proposed resolution**: Create a separate assert_prompt_contains_subprocess_guard helper or update the helper name and failure text to mention all three checked prompt contracts

### FINDING_3:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/launch-codex-ci.sh:138-150
- **Concern**: Planned inline PROMPT paragraph contains unescaped double quotes inside a double-quoted shell assignment. Scenario: The literal The "stdin is closed for this session" failure class... inserted as written can terminate the PROMPT assignment; the launcher may exit or produce a broken prompt before Codex runs
- **Proposed resolution**: Either escape the inner quotes as \"stdin is closed for this session\" or change the PROMPT construction to a heredoc/command substitution that safely carries literal quotes

### FINDING_4:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-launch-codex-ci.sh:42-47
- **Concern**: Planned regression pin greps launcher source instead of the emitted prompt. Scenario: A future edit can leave persistent interactive subprocess in a comment or dead source while removing it from the actual ${OUTPUT}.prompt passed to Codex; the test still passes and the failure mode silently returns
- **Proposed resolution**: Add a runtime prompt assertion after the existing stubbed fix-role launch at scripts/test-launch-codex-ci.sh:75-82, grepping ${OUT_FIX}.prompt for the clause; keep or replace the source grep as secondary coverage

### FINDING_5:
- **Reviewer(s)**: Codex-Edge
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/implement/references/codex-manifest-schema.md:69-90
- **Concern**: New stable bail token is introduced in the prompt but omitted from the manifest schema token list. Scenario: Implementers may repeatedly emit interactive-subprocess-unsupported, but the authoritative bail-reason section says stable tokens are enumerated there; downstream docs/tooling that pattern-match known reasons will not recognize it
- **Proposed resolution**: Add interactive-subprocess-unsupported to the Bail-reason tokens section, or revise the planned prompt to make clear it is intentionally a free-form Codex-authored token and not a stable enumerated reason

### FINDING_6:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: agents/_implementer-base.md:23-34; scripts/generate-cursor-implementer.sh:67-70
- **Concern**: Codex-only abort rule is proposed in the shared hard-guard base that Cursor also copies verbatim. Scenario: Cursor implementer inherits a non-negotiable abort instruction for a Codex-specific failure class; a Cursor run that can safely use its own terminal/session mechanics may bail or avoid better verification even though #2991 is not a Cursor failure
- **Proposed resolution**: Keep the new guard Codex-only by injecting it in scripts/generate-codex-implementer.sh or by adding a vendor-conditional base section filtered out by generate-cursor-implementer.sh; pin absence or non-abort wording in the Cursor artifact

### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/references/codex-manifest-schema.md:69-90
- **Concern**: New planned bail_reason token is not added to the manifest schema token list. Scenario: The prompt tells Codex to emit bail_reason="interactive-subprocess-unsupported", but the normative schema says stable bail reasons are listed there and downstream tooling pattern-matches them; docs and digest drift and reviewers/operators cannot distinguish this token from arbitrary free-form bail text
- **Proposed resolution**: Add interactive-subprocess-unsupported to codex-manifest-schema.md and codex-manifest-schema.digest.md with ownership semantics, and update any token-list harness if present

### FINDING_8:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/test-launch-codex-ci.sh:42-48; scripts/test-launch-codex-ci.sh:75-82
- **Concern**: The planned launcher assertion greps source instead of the composed prompt it claims to pin. Scenario: A future edit can leave the phrase in a comment, docs string, or dead branch while removing it from PROMPT; the test still passes but Codex CI fixer never receives the prohibition
- **Proposed resolution**: After the existing stub invocation writes ${OUT_FIX}.prompt, grep that prompt file for the phrase; keep or drop the source grep as secondary coverage

### FINDING_9:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/launch-codex-ci.sh:138-150
- **Concern**: Proposed inline PROMPT text contains unescaped double quotes for "stdin is closed for this session". Scenario: The PROMPT assignment is a double-quoted shell string; inserting the plan text verbatim turns the quoted error phrase into shell syntax that tries to run words from the phrase as a command, so launch-codex-ci.sh can fail before launching Codex
- **Proposed resolution**: Revise the plan to escape the inner quotes as \"stdin is closed for this session\", remove the quote marks, or switch PROMPT construction to a quoted heredoc pattern before adding this paragraph

### FINDING_10:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/launch-codex-ci.sh:138-150
- **Concern**: Plan inserts literal double quotes into a double-quoted PROMPT assignment without specifying shell escaping. Scenario: The proposed CI prompt paragraph contains The "stdin is closed for this session" failure class; inserted verbatim inside PROMPT="..." it terminates the string and breaks launch-codex-ci.sh syntax
- **Proposed resolution**: Specify the source form with escaped quotes, e.g. The \"stdin is closed for this session\" failure class, or refactor PROMPT construction to a heredoc while preserving variable expansion and add validation that the rendered prompt still contains the quoted sentence

### FINDING_11:
- **Reviewer(s)**: Codex-dyn-generator-output-fidelity
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: Makefile:18-21; Makefile:43-68; Makefile:852-853; Makefile:948-951; scripts/test-check-generators.sh:251-257; .pre-commit-config.yaml:1-5
- **Concern**: The plan claims make lint transitively invokes scripts/check-generators.sh, but lint runs test-harnesses and lint-only; test-harnesses-13 runs scripts/test-check-generators.sh, and agent-sync is a separate target that invokes the real checker.. Scenario: A contributor can follow the plan's make lint validation and still miss real generated-artifact drift locally; explicit bash scripts/check-generators.sh or CI agent-sync would catch it later, but the plan's lint-signal claim is false.
- **Proposed resolution**: Revise the plan to require explicit bash scripts/check-generators.sh or make agent-sync, or wire agent-sync/check-generators into lint if that is intended.

### FINDING_12:
- **Reviewer(s)**: Codex-dyn-generator-output-fidelity
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/check-generators.sh:18-20; scripts/check-generators.sh:64-67; scripts/check-generators.sh:113-119
- **Concern**: The plan says scripts/check-generators.sh has a --check mode, but the walker rejects all arguments; --check belongs to the registered generator scripts that the walker calls.. Scenario: Running bash scripts/check-generators.sh --check exits with usage status 2, so any plan text or implementation step relying on that mode is wrong even though bash scripts/check-generators.sh does perform drift detection.
- **Proposed resolution**: Change the wording to say scripts/check-generators.sh invokes each registered generator in --check mode, or add and test a --check alias on the walker.

### FINDING_13:
- **Reviewer(s)**: Codex-dyn-sibling-md-placement
- **Severity**: important
- **Focus area**: code-quality
- **Location**: scripts/launch-codex-ci.md:5-20
- **Concern**: The launch-codex-ci.md fallback branch is not the branch that should execute: existing H2 sections already document prompt inputs/construction via Interface and Behavior.. Scenario: The plan says to add ## Subprocess tool discipline if no prompt-context section exists; an implementer keying off the absence of exact headings like Prompt construction or Inputs could add a spurious new H2 beside the existing Interface/Behavior prompt documentation.
- **Proposed resolution**: Revise the plan to name the exact placement: append the one-line bullet under ## Behavior after the fixed-prompt paragraph, or under ## Interface after the prompt-injection input descriptions; remove the conditional fallback for this file.
