### External Reviewer Issues

- **Step design Step 3 — collect-agent-results.sh cursor SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-arch-output.txt|TOOL=cursor|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/cursor-plan-arch-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	latent	correctness	scripts/test-launch-codex-ci.sh:75-82	New CI prompt pin is planned as a source grep instead of checking the rendered prompt	The test can pass if the phrase remains in a comment or dead code while the actual Codex prompt no longer carries the guard	Assert against ${OUT_FIX}.prompt after the existing stub launch, and optionally verify non-fix rendered prompts if the guard is intended to be universal
1	in_scope	nit	code-quality	skills/implement/scripts/test-codex-implementer.sh:22-30	Subprocess guard assertion is folded into a manifest-template helper and failure message	If the new phrase is missing, the harness reports a misleading manifest-template/self-validation failure	Create a separate assert_prompt_contains_subprocess_guard helper or update the helper name and failure text to mention all three checked prompt contracts

1. [correctness] `scripts/test-launch-codex-ci.sh:75-82`: the proposed `grep` against `scripts/launch-codex-ci.sh` does not validate the actual prompt passed to Codex. This file already has a stubbed runtime path that writes `${OUT_FIX}.prompt`; put the new assertion there so future refactors cannot pass by leaving the phrase in a comment or unused assignment.

2. [code-quality] `skills/implement/scripts/test-codex-implementer.sh:22-30`: adding the subprocess-prohibition check to `assert_manifest_template_present` makes the diagnostic inaccurate. Keep it as a separate prompt-contract assertion, or broaden the helper name and failure text so failures identify the missing subprocess guard.
## Reviewer stderr (<TMPDIR>/cursor-plan-arch-output.txt.diag)

(file missing: <TMPDIR>/cursor-plan-arch-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh cursor SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-edge-output.txt|TOOL=cursor|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/cursor-plan-edge-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	scripts/launch-codex-ci.sh:138-150	Planned inline PROMPT paragraph contains unescaped double quotes inside a double-quoted shell assignment	The literal The "stdin is closed for this session" failure class... inserted as written can terminate the PROMPT assignment; the launcher may exit or produce a broken prompt before Codex runs	Either escape the inner quotes as \"stdin is closed for this session\" or change the PROMPT construction to a heredoc/command substitution that safely carries literal quotes
1	in_scope	important	risk-integration	scripts/test-launch-codex-ci.sh:42-47	Planned regression pin greps launcher source instead of the emitted prompt	A future edit can leave persistent interactive subprocess in a comment or dead source while removing it from the actual ${OUTPUT}.prompt passed to Codex; the test still passes and the failure mode silently returns	Add a runtime prompt assertion after the existing stubbed fix-role launch at scripts/test-launch-codex-ci.sh:75-82, grepping ${OUT_FIX}.prompt for the clause; keep or replace the source grep as secondary coverage
1	in_scope	latent	architecture	skills/implement/references/codex-manifest-schema.md:69-90	New stable bail token is introduced in the prompt but omitted from the manifest schema token list	Implementers may repeatedly emit interactive-subprocess-unsupported, but the authoritative bail-reason section says stable tokens are enumerated there; downstream docs/tooling that pattern-match known reasons will not recognize it	Add interactive-subprocess-unsupported to the Bail-reason tokens section, or revise the planned prompt to make clear it is intentionally a free-form Codex-authored token and not a stable enumerated reason

1. [correctness] `scripts/launch-codex-ci.sh:138-150`: the plan gives literal prompt text with `"stdin is closed for this session"` for insertion into `PROMPT="..."`. That needs explicit shell quoting treatment or a heredoc-based prompt construction.

2. [risk-integration] `scripts/test-launch-codex-ci.sh:42-47`: the proposed grep pins source text, not the launched prompt. The harness already creates `${OUT_FIX}.prompt`; assert against that file so quoting or placement regressions are caught.

3. [architecture] `skills/implement/references/codex-manifest-schema.md:69-90`: the plan adds a reusable bail token but leaves the authoritative token list unchanged. Either document the token there or frame it as free-form rather than stable.
## Reviewer stderr (<TMPDIR>/cursor-plan-edge-output.txt.diag)

(file missing: <TMPDIR>/cursor-plan-edge-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh cursor SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-innovation-output.txt|TOOL=cursor|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/cursor-plan-innovation-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	architecture	agents/_implementer-base.md:23-34; scripts/generate-cursor-implementer.sh:67-70	Codex-only abort rule is proposed in the shared hard-guard base that Cursor also copies verbatim	Cursor implementer inherits a non-negotiable abort instruction for a Codex-specific failure class; a Cursor run that can safely use its own terminal/session mechanics may bail or avoid better verification even though #2991 is not a Cursor failure	Keep the new guard Codex-only by injecting it in scripts/generate-codex-implementer.sh or by adding a vendor-conditional base section filtered out by generate-cursor-implementer.sh; pin absence or non-abort wording in the Cursor artifact
1	in_scope	important	correctness	skills/implement/references/codex-manifest-schema.md:69-90	New planned bail_reason token is not added to the manifest schema token list	The prompt tells Codex to emit bail_reason="interactive-subprocess-unsupported", but the normative schema says stable bail reasons are listed there and downstream tooling pattern-matches them; docs and digest drift and reviewers/operators cannot distinguish this token from arbitrary free-form bail text	Add interactive-subprocess-unsupported to codex-manifest-schema.md and codex-manifest-schema.digest.md with ownership semantics, and update any token-list harness if present
1	in_scope	latent	risk-integration	scripts/test-launch-codex-ci.sh:42-48; scripts/test-launch-codex-ci.sh:75-82	The planned launcher assertion greps source instead of the composed prompt it claims to pin	A future edit can leave the phrase in a comment, docs string, or dead branch while removing it from PROMPT; the test still passes but Codex CI fixer never receives the prohibition	After the existing stub invocation writes ${OUT_FIX}.prompt, grep that prompt file for the phrase; keep or drop the source grep as secondary coverage

1. [architecture] `agents/_implementer-base.md:23-34`; `scripts/generate-cursor-implementer.sh:67-70`  
Concern: the plan puts a Codex-specific abort rule in the shared base and intentionally ships it to Cursor.  
Suggested revision: inject the guard only into `agents/codex-implementer.md`, or make the generator filter a vendor-conditional section.

2. [correctness] `skills/implement/references/codex-manifest-schema.md:69-90`  
Concern: the new directed `bail_reason` token is omitted from the schema’s stable token list and digest.  
Suggested revision: document `interactive-subprocess-unsupported` in both schema files so the prompt and manifest contract stay aligned.

3. [risk-integration] `scripts/test-launch-codex-ci.sh:42-48`; `scripts/test-launch-codex-ci.sh:75-82`  
Concern: source grep does not prove the runtime prompt contains the prohibition.  
Suggested revision: assert against `${OUT_FIX}.prompt` in the existing stubbed launcher path.
## Reviewer stderr (<TMPDIR>/cursor-plan-innovation-output.txt.diag)

(file missing: <TMPDIR>/cursor-plan-innovation-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh cursor SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-pragmatic-output.txt|TOOL=cursor|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/cursor-plan-pragmatic-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	scripts/launch-codex-ci.sh:138-150	Proposed inline PROMPT text contains unescaped double quotes for "stdin is closed for this session"	The PROMPT assignment is a double-quoted shell string; inserting the plan text verbatim turns the quoted error phrase into shell syntax that tries to run words from the phrase as a command, so launch-codex-ci.sh can fail before launching Codex	Revise the plan to escape the inner quotes as \"stdin is closed for this session\", remove the quote marks, or switch PROMPT construction to a quoted heredoc pattern before adding this paragraph

1. **[correctness]** `scripts/launch-codex-ci.sh:138-150` — The plan’s proposed `PROMPT=` paragraph includes raw double quotes around `"stdin is closed for this session"`. Since the current prompt is built inside a double-quoted shell assignment, inserting that text verbatim breaks the assignment at runtime. Update the plan’s clause for `scripts/launch-codex-ci.sh` to use escaped quotes, no quotes, or a heredoc-style prompt construction.
## Reviewer stderr (<TMPDIR>/cursor-plan-pragmatic-output.txt.diag)

(file missing: <TMPDIR>/cursor-plan-pragmatic-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh cursor SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-requirements-output.txt|TOOL=cursor|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/cursor-plan-requirements-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	scripts/launch-codex-ci.sh:138-150	Plan inserts literal double quotes into a double-quoted PROMPT assignment without specifying shell escaping	The proposed CI prompt paragraph contains The "stdin is closed for this session" failure class; inserted verbatim inside PROMPT="..." it terminates the string and breaks launch-codex-ci.sh syntax	Specify the source form with escaped quotes, e.g. The \"stdin is closed for this session\" failure class, or refactor PROMPT construction to a heredoc while preserving variable expansion and add validation that the rendered prompt still contains the quoted sentence
2	in_scope	latent	correctness	scripts/test-launch-codex-ci.sh:75-82	Planned regression pin only greps launcher source, not the rendered Codex prompt	A comment or dead string containing persistent interactive subprocess would satisfy the proposed grep while the actual ${OUTPUT}.prompt passed to Codex could omit the prohibition	Extend the existing stub launch prompt assertions to grep ${OUT_FIX}.prompt for persistent interactive subprocess, optionally keeping the source grep as a secondary pin

## Reviewer stderr (<TMPDIR>/cursor-plan-requirements-output.txt.diag)

(file missing: <TMPDIR>/cursor-plan-requirements-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh cursor SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-dyn-generator-output-fidelity-output.txt|TOOL=cursor|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/cursor-plan-dyn-generator-output-fidelity-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	risk-integration	Makefile:18-21; Makefile:43-68; Makefile:852-853; Makefile:948-951; scripts/test-check-generators.sh:251-257; .pre-commit-config.yaml:1-5	The plan claims make lint transitively invokes scripts/check-generators.sh, but lint runs test-harnesses and lint-only; test-harnesses-13 runs scripts/test-check-generators.sh, and agent-sync is a separate target that invokes the real checker.	A contributor can follow the plan's make lint validation and still miss real generated-artifact drift locally; explicit bash scripts/check-generators.sh or CI agent-sync would catch it later, but the plan's lint-signal claim is false.	Revise the plan to require explicit bash scripts/check-generators.sh or make agent-sync, or wire agent-sync/check-generators into lint if that is intended.
1	in_scope	latent	correctness	scripts/check-generators.sh:18-20; scripts/check-generators.sh:64-67; scripts/check-generators.sh:113-119	The plan says scripts/check-generators.sh has a --check mode, but the walker rejects all arguments; --check belongs to the registered generator scripts that the walker calls.	Running bash scripts/check-generators.sh --check exits with usage status 2, so any plan text or implementation step relying on that mode is wrong even though bash scripts/check-generators.sh does perform drift detection.	Change the wording to say scripts/check-generators.sh invokes each registered generator in --check mode, or add and test a --check alias on the walker.

1. [risk-integration] `Makefile:18-21`, `Makefile:43-68`, `Makefile:852-853`, `Makefile:948-951`: `make lint` does not invoke the real generator drift checker transitively. Suggested revision: make the plan require `bash scripts/check-generators.sh` or `make agent-sync` explicitly, unless this PR also wires `agent-sync` into `lint`.

2. [correctness] `scripts/check-generators.sh:64-67`: `scripts/check-generators.sh --check` is not a supported mode. Suggested revision: correct the plan language so `--check` is attributed to the individual generators, or add a tested `--check` alias to the walker.
## Reviewer stderr (<TMPDIR>/cursor-plan-dyn-generator-output-fidelity-output.txt.diag)

(file missing: <TMPDIR>/cursor-plan-dyn-generator-output-fidelity-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh cursor SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-dyn-harness-phrase-alignment-output.txt|TOOL=cursor|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/cursor-plan-dyn-harness-phrase-alignment-output.txt)

{"no_issues_found": true}
## Reviewer stderr (<TMPDIR>/cursor-plan-dyn-harness-phrase-alignment-output.txt.diag)

(file missing: <TMPDIR>/cursor-plan-dyn-harness-phrase-alignment-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh cursor SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-dyn-sibling-md-placement-output.txt|TOOL=cursor|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/cursor-plan-dyn-sibling-md-placement-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	code-quality	scripts/launch-codex-ci.md:5-20	The launch-codex-ci.md fallback branch is not the branch that should execute: existing H2 sections already document prompt inputs/construction via Interface and Behavior.	The plan says to add ## Subprocess tool discipline if no prompt-context section exists; an implementer keying off the absence of exact headings like Prompt construction or Inputs could add a spurious new H2 beside the existing Interface/Behavior prompt documentation.	Revise the plan to name the exact placement: append the one-line bullet under ## Behavior after the fixed-prompt paragraph, or under ## Interface after the prompt-injection input descriptions; remove the conditional fallback for this file.

1. [code-quality] `scripts/launch-codex-ci.md:5-20`: The current file has `## Interface` documenting prompt inputs at lines 11-14 and `## Behavior` documenting fixed prompt construction at line 18. So the plan’s `scripts/launch-codex-ci.md` conditional should not fall through to a new `## Subprocess tool discipline` section. Tighten the plan to specify the exact existing H2 placement.

I found no sibling-structure blocker for `skills/implement/scripts/test-codex-implementer.md:5-20` or `scripts/test-launch-codex-ci.md:5-17`: both have Coverage lists that can accept one appended bullet without renumbering ordered content or disturbing structured assertions.
## Reviewer stderr (<TMPDIR>/cursor-plan-dyn-sibling-md-placement-output.txt.diag)

(file missing: <TMPDIR>/cursor-plan-dyn-sibling-md-placement-output.txt.diag)

  ```
