### FINDING_1: New repo-wide hooks can be skipped in scoped pre-commit runs
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: important
- **Concern**: The new repo-walking linters are wired without `always_run: true`, so scoped `pre-commit run --files` or relevant-checks runs can skip cross-repo scans and let drift pass locally until full CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Mirror existing hooks: set pass_filenames: false and always_run: true on both new entries
  - From Cursor-Innovation: Match lint-readability-preamble: add always_run: true to both new local hooks (keep pass_filenames: false)


### FINDING_2: Renderer substitution linter matches safe ANSI-C replacements
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Edge, Codex-Edge, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-linter-pattern-gap, Codex-dyn-linter-pattern-gap
- **Severity**: important
- **Concern**: The proposed renderer-safety grep treats any replacement beginning with `$` as unsafe, so it matches safe ANSI-C replacement forms like `${out//$'\n'/$'\n '}` even though the plan says `$'...'` replacements are excluded. This can make `make lint` fail on an existing intended-safe callsite or require an unnecessary waiver.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Tighten regex to require $[A-Za-z_][A-Za-z0-9_]* (or ${...}) in replacement position, or document and add # lint-renderer-safe: ok for literal ANSI-C escapes in that harness line
  - From Codex-Arch: Tighten the regex to require a variable expansion after the replacement dollar, or explicitly skip $'...' replacements, and add this exact safe fixture to the harness
  - From Cursor-Edge, Codex-Edge: Tighten the match to replacement variables only, for example `$name` or `${name}`, explicitly exclude `$'...'`, and pin the current ANSI-C case in the harness
  - From Cursor-Pragmatic, Codex-Pragmatic: Define the match as variable-derived replacement only, for example requiring $ followed by an identifier or ${...}, and pin this existing ANSI-C literal case in the harness
  - From Cursor-Requirements, Codex-Requirements: Revise the linter plan and harness so the replacement-side regex excludes $'...' literals, and include this existing line or an equivalent fixture as a pass case
  - From Cursor-dyn-linter-pattern-gap: After the grep match, skip when the replacement token after the second `/` is `$'` (ANSI-C); document that rule in `lint-renderer-substitution-safety.md` and add a harness pass case mirroring `test-check-review-changes.sh:119`
  - From Codex-dyn-linter-pattern-gap: Tighten the regex so the replacement must start with a variable form such as $name or ${name}, not $'...'; add fixture cases for ANSI-C pass and $arr[0] fail


### FINDING_3: Step 0b still lacks tier-derived run parameter assignments
- **Reviewer(s)**: Codex-Arch, Cursor-Edge, Codex-Edge, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: important
- **Concern**: The plan adds new `write-run-params.sh` flags but does not ensure Step 0b assigns the corresponding `design_classification_reason`, `sketch_budget`, `review_budget`, and `workflow_path` values before the canonical call. Normal SIMPLE/HARD runs can pass empty values, triggering the new abort path or incorrect downstream defaults.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add explicit tier mapping assignments before the write-run-params.sh call, matching flags.md: SIMPLE => reason/source plus sketch_budget=2 review_budget=full workflow_path=SIMPLE; HARD => sketch_budget=4 review_budget=full workflow_path=HARD
  - From Cursor-Edge, Codex-Edge: Either initialize non-empty reason/source before the Step 0b call, or implement these two flags with an empty-value-tolerant parser and add an empty-string regression test
  - From Codex-Innovation: Either set a non-empty design_classification_reason before this call, or make --reason/--source parsing accept empty strings and emit null, matching the plan edge case
  - From Cursor-Pragmatic, Codex-Pragmatic: Add the minimal SIMPLE/HARD mapping in Step 0b before the call: reason/source plus sketch_budget review_budget workflow_path, or pass literal values derived from design_classification inline


### FINDING_4: Optional writer flags reject empty values before null conversion
- **Reviewer(s)**: Codex-Arch, Cursor-Edge, Codex-Edge, Codex-Innovation
- **Severity**: important
- **Concern**: The proposed `${2:?}` parser contradicts the nullable optional-field contract because `--reason ""` or another empty optional value exits during shell expansion before `jq` can emit JSON `null`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Use a Bash 3.2-safe value reader that distinguishes missing argv from an empty string, then apply enum validation only when the captured value is non-empty
  - From Cursor-Edge, Codex-Edge: Either initialize non-empty reason/source before the Step 0b call, or implement these two flags with an empty-value-tolerant parser and add an empty-string regression test
  - From Codex-Innovation: Either set a non-empty design_classification_reason before this call, or make --reason/--source parsing accept empty strings and emit null, matching the plan edge case


### FINDING_5: `flags.md` still documents stale SIMPLE/HARD mapping
- **Reviewer(s)**: Codex-Innovation, Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: The normative flag reference is not updated consistently with the v3 schema and SIMPLE behavior. It still maps SIMPLE to existing sketch behavior, creating ambiguity about whether SIMPLE should persist sketches or skip sketches/dialectic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Update flags.md in the same change to describe the v3 fields and the intended SIMPLE/HARD mappings, or explicitly state that design_classification overrides sketch_budget for SIMPLE
  - From Cursor-Requirements, Codex-Requirements: Revise the plan to update the SIMPLE mapping to sketch_budget=0 and adjust the Step 2a prose/flags contract/tests accordingly, or explicitly change the acceptance criterion if two sketches are intended


### FINDING_6: Planned enum tests use unsupported equals-form flags
- **Reviewer(s)**: Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: important
- **Concern**: The plan asks tests to use `--sketch-budget=5` style arguments, but the writer parser only supports space-separated `--flag value` arguments, so tests may exercise unknown-flag handling instead of enum validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic, Codex-Pragmatic: Change the planned tests to use --sketch-budget 5, --review-budget medium, and --workflow-path MEDIUM unless equals-form support is intentionally added for every flag


### FINDING_7: v3 JSON field names for reason/source are underspecified
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: The plan adds `--reason` and `--source` but does not explicitly pin the required JSON keys `design_classification_reason` and `design_classification_source`, so an implementation could emit ambiguous `reason`/`source` keys instead.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements, Codex-Requirements: Spell out the five v3 field names in the write-run-params.sh, write-run-params.md, and test-write-run-params.sh plan bullets, including design_classification_reason and design_classification_source


### FINDING_8: New linter scripts may trip dead-script lint
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: The plan adds new linter and harness scripts but does not update the `agent-lint.toml` dead-script allowlist used by comparable Makefile/pre-commit-only linters, so `make lint` can fail even after wiring the targets.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements, Codex-Requirements: Add the new linter, harness, and sibling .md paths to agent-lint.toml using the same exclusion pattern as lint-readability-preamble and lint-foreground-markers


### FINDING_10: Flag-signature linter lacks multi-line invocation coverage
- **Reviewer(s)**: Codex-dyn-linter-pattern-gap
- **Severity**: important
- **Concern**: The planned flag-signature linter mentions continuation lines, but the harness does not include a multi-line fixture matching the current `write-run-params.sh` invocation shape, so tests could pass while missing the real drift pattern.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-linter-pattern-gap: Specify logical-command assembly for trailing-backslash lines and add a fixture mirroring the script line followed by flags on continuation lines


