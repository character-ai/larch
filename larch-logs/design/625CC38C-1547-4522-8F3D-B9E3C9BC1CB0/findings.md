### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: .pre-commit-config.yaml:200-214
- **Concern**: New repo-walking linters omit always_run: true unlike lint-readability-preamble and lint-foreground-markers. Scenario: Scoped pre-commit run --files on script-only edits skips SKILL.md↔script cross-check; drift can pass relevant-checks locally while full CI catches it later
- **Proposed resolution**: Mirror existing hooks: set pass_filenames: false and always_run: true on both new entries

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-renderer-substitution-safety.sh:125-128
- **Concern**: Edge case claims $'...' replacements are excluded but proposed grep ends with /$ only. Scenario: ${out//$'\n'/$'\n' } in skills/implement/scripts/test-check-review-changes.sh:119 matches and make lint-renderer-substitution-safety fails after enablement
- **Proposed resolution**: Tighten regex to require $[A-Za-z_][A-Za-z0-9_]* (or ${...}) in replacement position, or document and add # lint-renderer-safe: ok for literal ANSI-C escapes in that harness line

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:275-305
- **Concern**: Plan adds writer flags but only replaces the failure paragraph; Step 0b still does not set design_classification_reason, sketch_budget, review_budget, or workflow_path before invoking write-run-params.sh. Scenario: A normal SIMPLE/HARD run can pass empty values to the now-strict writer, causing the new abort path or later budget readers to default incorrectly
- **Proposed resolution**: Add explicit tier mapping assignments before the write-run-params.sh call, matching flags.md: SIMPLE => reason/source plus sketch_budget=2 review_budget=full workflow_path=SIMPLE; HARD => sketch_budget=4 review_budget=full workflow_path=HARD

### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/write-run-params.sh:23-44
- **Concern**: Proposed ${2:?} parsing contradicts the nullable optional-flag contract for the new fields. Scenario: Passing --reason "" or another optional flag with an empty value exits during shell expansion before jq can emit null, despite the plan requiring empty strings to become JSON null
- **Proposed resolution**: Use a Bash 3.2-safe value reader that distinguishes missing argv from an empty string, then apply enum validation only when the captured value is non-empty

### FINDING_5:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/test-check-review-changes.sh:119
- **Concern**: Proposed renderer-safety regex also matches ANSI-C literal replacements like ${out//$'\n'/$'\n '}. Scenario: The new linter can fail the existing tree or force an unnecessary waiver, even though the plan says this safe form must be excluded
- **Proposed resolution**: Tighten the regex to require a variable expansion after the replacement dollar, or explicitly skip $'...' replacements, and add this exact safe fixture to the harness

### FINDING_6:
- **Reviewer(s)**: Cursor-Edge, Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:125-128; skills/implement/scripts/test-check-review-changes.sh:119
- **Concern**: Renderer substitution linter regex still matches ANSI-C literal replacements. Scenario: The planned grep pattern catches the existing safe `${out//$'\n'/$'\n '}` test helper despite the plan saying ANSI-C `$'...'` replacements are excluded, so the new linter can fail `make lint` on an intended-safe current callsite
- **Proposed resolution**: Tighten the match to replacement variables only, for example `$name` or `${name}`, explicitly exclude `$'...'`, and pin the current ANSI-C case in the harness

### FINDING_7:
- **Reviewer(s)**: Cursor-Edge, Codex-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:19-22,222; skills/design/SKILL.md:282,301
- **Concern**: Empty reason/source contract conflicts with the parser shape. Scenario: The plan says empty `--reason` and `--source` emit JSON null, but also specifies `${2:?...}` for each new flag; Step 0b documents `design_classification_source` but not `design_classification_reason`, so an empty reason can turn the intended fixed call into the new hard abort path
- **Proposed resolution**: Either initialize non-empty reason/source before the Step 0b call, or implement these two flags with an empty-value-tolerant parser and add an empty-string regression test

### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: .pre-commit-config.yaml:200-214
- **Concern**: New pre-commit hooks omit always_run: true unlike lint-readability-preamble. Scenario: Scoped pre-commit/relevant-checks runs only fire hooks when staged files match types_or/types, so a shell-only or markdown-only commit can skip the cross-repo SKILL↔script or substitution-safety scan until a full make lint
- **Proposed resolution**: Match lint-readability-preamble: add always_run: true to both new local hooks (keep pass_filenames: false)

### FINDING_9:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:299-305
- **Concern**: Plan always passes --reason but writer plan rejects empty values. Scenario: design_classification_reason is not assigned in the cited Step 0 mapping, so --reason "" can make write-run-params.sh exit non-zero and the new contract-drift abort fires on normal SIMPLE/HARD runs
- **Proposed resolution**: Either set a non-empty design_classification_reason before this call, or make --reason/--source parsing accept empty strings and emit null, matching the plan edge case

### FINDING_10:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/design/references/flags.md:15-17
- **Concern**: Normative flag mapping is left out of the v3 schema update. Scenario: The mandatory flag reference still maps --simple to sketch_budget=2 and documents --trivial fields while the proposed writer/schema and SIMPLE no-sketch contract move elsewhere
- **Proposed resolution**: Update flags.md in the same change to describe the v3 fields and the intended SIMPLE/HARD mappings, or explicitly state that design_classification overrides sketch_budget for SIMPLE

### FINDING_11:
- **Reviewer(s)**: Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:275-309
- **Concern**: Plan accepts the new write-run-params flags but does not add the missing tier-derived variable assignments before the canonical call. Scenario: The call can still pass empty or unset design_classification_reason sketch_budget review_budget or workflow_path values, so /design --simple can abort instead of producing v3 run-params.json
- **Proposed resolution**: Add the minimal SIMPLE/HARD mapping in Step 0b before the call: reason/source plus sketch_budget review_budget workflow_path, or pass literal values derived from design_classification inline

### FINDING_12:
- **Reviewer(s)**: Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/test-check-review-changes.sh:119
- **Concern**: Proposed renderer linter regex matches any replacement starting with $ despite the plan saying ANSI-C literals are excluded. Scenario: The new lint target can fail on the existing safe ${out//$'\n'/$'\n '} call outside a heredoc
- **Proposed resolution**: Define the match as variable-derived replacement only, for example requiring $ followed by an identifier or ${...}, and pin this existing ANSI-C literal case in the harness

### FINDING_13:
- **Reviewer(s)**: Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/write-run-params.sh:23-54
- **Concern**: Plan asks tests to use --sketch-budget=5 style, but the writer parser shape only supports space-separated --flag value arguments. Scenario: The invalid enum tests will either hit unknown-flag handling instead of enum validation or push unnecessary equals-form parser expansion
- **Proposed resolution**: Change the planned tests to use --sketch-budget 5, --review-budget medium, and --workflow-path MEDIUM unless equals-form support is intentionally added for every flag

### FINDING_14:
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/flags.md:16; skills/design/SKILL.md:497
- **Concern**: Finding 1: Plan claims the SIMPLE end-to-end flow should have no sketches and no dialectic, but it does not update the existing SIMPLE tier mapping that still sets sketch_budget=2 and routes to the quick/simple two-sketch branch. Scenario: After Option A lands, /design --simple can still persist sketch_budget=2 from the current flag contract and run two sketch agents, failing the Section B acceptance criterion
- **Proposed resolution**: Revise the plan to update the SIMPLE mapping to sketch_budget=0 and adjust the Step 2a prose/flags contract/tests accordingly, or explicitly change the acceptance criterion if two sketches are intended

### FINDING_15:
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/write-run-params.md:17
- **Concern**: Finding 2: Plan adds --reason and --source but never pins their required v3 JSON field names design_classification_reason and design_classification_source. Scenario: Implementer may emit reason/source keys instead, leaving the documented schema contract and any future consumers without the expected fields
- **Proposed resolution**: Spell out the five v3 field names in the write-run-params.sh, write-run-params.md, and test-write-run-params.sh plan bullets, including design_classification_reason and design_classification_source

### FINDING_16:
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/test-check-review-changes.sh:119
- **Concern**: Finding 3: Proposed renderer-safety linter regex also matches the existing safe ANSI-C replacement ${out//$'\n'/$'\n '} despite the plan saying ANSI-C escapes are excluded. Scenario: The new linter will fail on the current tree or require an unnecessary waiver, blocking make lint before it can validate the intended unsafe renderer substitutions
- **Proposed resolution**: Revise the linter plan and harness so the replacement-side regex excludes $'...' literals, and include this existing line or an equivalent fixture as a pass case

### FINDING_17:
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: agent-lint.toml:837-844
- **Concern**: Finding 4: Plan creates new linter and harness scripts but omits the agent-lint.toml dead-script allowlist used by peer Makefile/pre-commit-only linters. Scenario: make lint can fail under agent-lint even though the new Makefile and pre-commit targets are wired
- **Proposed resolution**: Add the new linter, harness, and sibling .md paths to agent-lint.toml using the same exclusion pattern as lint-readability-preamble and lint-foreground-markers

### FINDING_18:
- **Reviewer(s)**: Cursor-dyn-schema-migration-compat, Codex-dyn-schema-migration-compat
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:29-39; scripts/test-write-run-params.sh:21-32,108-115
- **Concern**: The proposed test additions do not explicitly require the backward-compat round-trip where a legacy caller passes only the original five flags and the writer emits schema_version 3 with all five new fields present as null. Scenario: An implementation can satisfy the current plan by updating the minimal two-flag default case and adding an all-10-flags case, while missing the compatibility path for callers that still pass --partition-requested, --brainstorm-requested, and --manual-gate-b but none of the new v3 fields
- **Proposed resolution**: Add a concrete test case that invokes write-run-params.sh with only --classification, --output, --partition-requested, --brainstorm-requested, and --manual-gate-b; assert schema_version == 3, old booleans round-trip, and has("design_classification_reason"), has("design_classification_source"), has("sketch_budget"), has("review_budget"), has("workflow_path") with each new field == null

### FINDING_19:
- **Reviewer(s)**: Cursor-dyn-linter-pattern-gap
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:125-126;plan.txt:225-226;skills/implement/scripts/test-check-review-changes.sh:119
- **Concern**: Renderer grep `\$\{[A-Za-z_][A-Za-z0-9_]*//[^/]*/\$` matches any replacement starting with `$`, but edge cases claim `$'...'` ANSI-C forms are excluded with no matching filter. Scenario: The lone in-repo safe site `${out//$'\n'/$'\n' }` is flagged on first `make lint`; authors must add waivers or the linter fails green-tree
- **Proposed resolution**: After the grep match, skip when the replacement token after the second `/` is `$'` (ANSI-C); document that rule in `lint-renderer-substitution-safety.md` and add a harness pass case mirroring `test-check-review-changes.sh:119`

### FINDING_20:
- **Reviewer(s)**: Codex-dyn-linter-pattern-gap
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:123-128 and <TMPDIR>/plan.txt:224-236; skills/implement/scripts/test-check-review-changes.sh:119
- **Concern**: Renderer linter regex still matches ANSI-C replacement syntax the plan says is safe. Scenario: The proposed grep pattern ends at bare $ and therefore flags existing safe ${out//$'\n'/$'\n' } usage, while also lacking explicit harness coverage for the mentioned $arr[0] variant
- **Proposed resolution**: Tighten the regex so the replacement must start with a variable form such as $name or ${name}, not $'...'; add fixture cases for ANSI-C pass and $arr[0] fail

### FINDING_21:
- **Reviewer(s)**: Codex-dyn-linter-pattern-gap
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:84-90 and <TMPDIR>/plan.txt:106-115; skills/design/SKILL.md:299-309
- **Concern**: Flag-signature linter does not pin the real multi-line invocation shape. Scenario: The plan mentions continuation lines but the harness list has no multi-line fixture, so an implementation could pass tests while missing the current write-run-params.sh drift pattern
- **Proposed resolution**: Specify logical-command assembly for trailing-backslash lines and add a fixture mirroring the script line followed by flags on continuation lines

### FINDING_22:
- **Reviewer(s)**: Codex-dyn-linter-pattern-gap
- **Severity**: latent
- **Focus area**: architecture
- **Location**: <TMPDIR>/plan.txt:80-104 and <TMPDIR>/plan.txt:170-216
- **Concern**: Flag-signature linter scope is inconsistent and broader than the minimum-change contract. Scenario: The behavior says SKILL.md plus references/*.md, the sibling docs say skills/**/*.md, and Makefile/pre-commit invoke the linter without narrowing argv, leaving the implemented scan surface ambiguous
- **Proposed resolution**: Pick one scope and state it identically in behavior, docs, and hook rationale; for SIMPLE prefer skills/*/SKILL.md unless reference-file coverage is required by an acceptance criterion

### FINDING_23:
- **Reviewer(s)**: Cursor-dyn-silent-fallback-completeness, Codex-dyn-silent-fallback-completeness
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:466,769,930; scripts/read-design-classification.sh:6-18,52
- **Concern**: Plan only removes the Step 0b writer-failure downgrade, but downstream /design recovery paths still proceed as HARD when run-params is missing or invalid, and the plan tests only the happy SIMPLE write path.. Scenario: A SIMPLE run with a lost, malformed, or stale run-params.json after Step 0 can still take HARD sketches, HARD reviewer emphasis, or a HARD review-round cap despite the PR claiming to prevent silent tier downgrade.
- **Proposed resolution**: Extend Section B minimally to fail closed inside /design when post-Step-0 run-params is absent or invalid, or explicitly update these fallback branches and add a missing/malformed run-params acceptance test alongside the planned happy SIMPLE repro.
