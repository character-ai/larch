## Final Design Plan

## Plan

## Approach

Extend the `/learn-from-bugs` proposal and filing contracts with enforceable host, cost, and cheaper-mechanism semantics. Add a manifest-backed lint module with a frozen legacy baseline so only pre-existing lint modules may use the legacy exemption.

## Files to modify/create

### UPDATED: skills/learn-from-bugs/SKILL.md

- Require **Host**, **Size budget**, and **Cheaper alternative** for Step 4 sections 4 and 7, and section 5 proposals whose `best-home` is `lint` or `hook`.
- Define **Host** as an existing lint rule, module, hook, or harness being extended. Permit `Host: New module` only when the proposal also names the closest existing host and gives one sentence explaining why it cannot absorb the rule.
- Define **Size budget** as estimated new non-test lines; require an explicit justification above 150 lines.
- Define **Cheaper alternative** as the nearest cheaper mechanism—such as extending an existing rule, a manifest/table entry, invariant test, or hook line—plus one sentence explaining why it is insufficient.
- Require the three fields and their conditional explanations in Lint, Hook-contract, and Regression test filing body contracts.
- Make the pre-filing completeness pass fail closed for missing, blank, or semantically incomplete applicable fields, including missing over-150-line justification.
- Require default-mode Step 5 operator approval for every proposal whose Size budget exceeds 400 lines.
- Require filing mode to split every proposal whose Size budget exceeds 400 lines before filing; do not allow filing to proceed with the oversized proposal intact.

### UPDATED: python/tests/skills/_structure_learn_from_bugs_specialized.py

- Pin the exact field names `Host`, `Size budget`, and `Cheaper alternative`.
- Pin the Host exception requirement naming the closest existing host and why it cannot absorb the rule.
- Pin the Cheaper alternative requirement naming the nearest cheaper mechanism and why it is insufficient.
- Pin the fields and semantics in the applicable report and Lint, Hook-contract, and Regression test filing contracts.
- Pin fail-closed completeness behavior, the over-150-line justification threshold, the default-mode Step 5 approval gate above 400 lines, and filing-mode split-before-filing behavior above 400 lines.

### UPDATED: ARCHITECTURAL_GUIDELINES.md

- Append a `## Prevention discipline` section matching the repository’s heading and bullet style.
- Add `### G-Prevent-1: Prevention machinery names its host before it is commissioned`.
- State the host-first rule, expected size disclosure, preference for extending existing mechanisms, the 2026-07 evidence including #6873, #6881, and #6955, and the narrow new-surface deviation.

### NEW: python/lint-module-manifest.json

- Use an explicit stable top-level JSON schema, including a schema version and sorted module records.
- Add one deterministic record for every existing `python/larch/lint/lint_*.py` module.
- Seed only pre-commission modules as `host_decision: "legacy"` with `source_issue: 0`, without retroactive justification.
- Add `lint_module_manifest.py` as `new-module-justified`, with a non-empty one-sentence justification and the positive feature commissioning issue number.
- Keep module names as safe basenames and records sorted by module name.

### NEW: python/larch/lint/lint_module_manifest.py

- Expose `main(argv) -> int` and use the shared `LintRule`, `Finding`, and `run_rule` engine.
- Define a code-level frozen `LEGACY_SEED_MODULES` set containing exactly the lint-module basenames that existed when this feature was commissioned; do not derive it from the manifest or current filesystem.
- Validate the manifest schema before inventory comparison: malformed JSON, wrong top-level or record shapes, bad field types, duplicate modules, unsupported `host_decision` values, and unsafe module names are contract errors.
- Reject manifest symlinks, unreadable manifest input, and symlinked or otherwise unsafe `lint_*.py` inventory entries rather than silently skipping them.
- Compare the validated manifest to regular `lint_*.py` files and emit deterministic findings for missing entries and stale entries.
- Emit a finding when any `legacy` record is outside `LEGACY_SEED_MODULES`, preventing newly added modules from claiming the legacy exemption.
- Require every `new-module-justified` record to have a non-empty justification and a positive integer `source_issue`; reject booleans explicitly with `isinstance(value, int) and not isinstance(value, bool)`.
- Keep only allowlisted legacy rows exempt from retroactive justification.
- Preserve the shared engine’s clean, finding, and tool-error exit classes.

### NEW: python/tests/lint/test_lint_module_manifest.py

- Cover the committed seeded manifest, deterministic output, and parity between the manifest and live lint-module inventory.
- Cover missing entries, stale entries, duplicate records, malformed JSON, invalid schema/types, unsupported decisions, unsafe module names, symlink input, and unreadable input.
- Cover accepted seeded legacy rows and rejection of a non-seed or newly added on-disk module marked `legacy`.
- Cover empty justification, zero/negative/non-integer `source_issue`, and `source_issue: true` for `new-module-justified` rows.
- Exercise `main` through an injected or fake runner so tests remain offline.

### UPDATED: python/larch/cli.py

- Register `("lint", "module-manifest")` to the new module’s `main`.

### UPDATED: Makefile

- Add phony `lint-module-manifest` and `test-lint-module-manifest` targets.
- Add `module-manifest` to `py-lint-checks-fast`.
- Add the lint target to local `make lint` so both documented lint paths enforce the manifest.

### UPDATED: docs/linting.md

- Document the manifest path, schema, record fields, allowed host decisions, and frozen seeded-legacy policy.
- Document missing, stale, invalid legacy, and new-module justification failures.
- List the CLI and Make targets and note fast-lint integration.

## Edge cases

- The manifest lint includes its own new module as `new-module-justified`.
- JSON booleans do not count as positive integer issue numbers.
- Only the frozen pre-commission baseline may use `legacy`.
- Basenames cannot contain separators, traversal segments, or unsafe filesystem forms.
- A deleted lint module leaves a stale-entry finding until its manifest row is removed.
- A new lint module cannot bypass commissioning evidence by adding a legacy row.

## Failure modes

- Return the tool-error exit for malformed, unsafe, or unreadable manifest and inventory input.
- Return findings for validly parsed policy violations, including missing/stale entries, non-seed legacy rows, and incomplete new-module justification.
- Do not silently skip missing manifests, symlinked lint modules, duplicate records, or unsafe paths.
- Keep proposal filing blocked until every applicable field, conditional explanation, threshold justification, and oversized-proposal action is complete.

## Testing strategy

- Run `make test-learn-from-bugs-structure`.
- Run `make test-lint-module-manifest`.
- Run `make lint-module-manifest`.
- Run focused pytest for both changed test modules.
- Run `make py-lint` and `make lint` for acceptance coverage.

difficulty: HARD
diff_added: 735
diff_deleted: 5
mechanical_churn: true
oversize_override: operator
diff_lines: 740
