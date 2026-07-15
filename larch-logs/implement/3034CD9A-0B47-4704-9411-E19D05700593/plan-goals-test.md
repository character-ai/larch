## Goal
Implement issue #7210: [IMPLEMENTING] bug-treadmill [FEATURE] 6968.2: lint-module-manifest: seeded manifest, engine rule, registration, targets, and docs.

## Implementation Plan
## Plan

## Approach

Add a manifest-backed lint module with a frozen legacy baseline so only pre-existing lint modules may use the legacy exemption. Build on the shared lint engine (`python/larch/lint/engine.py`: `LintRule`, `Finding`, `run_rule`), which is already landed. The proposal-contract half of the parent issue is the independent sibling piece; neither blocks the other.

## Files to modify/create

### NEW: python/lint-module-manifest.json

- Use an explicit stable top-level JSON schema, including a schema version and sorted module records.
- Add one deterministic record for every existing `python/larch/lint/lint_*.py` module, shaped `{"module": "lint_example.py", "host_decision": "legacy" | "new-module-justified", "justification": "<one sentence>", "source_issue": <int>}`.
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
- Preserve the shared engine's clean, finding, and tool-error exit classes.

### NEW: python/tests/lint/test_lint_module_manifest.py

- Cover the committed seeded manifest, deterministic output, and parity between the manifest and live lint-module inventory.
- Cover missing entries, stale entries, duplicate records, malformed JSON, invalid schema/types, unsupported decisions, unsafe module names, symlink input, and unreadable input.
- Cover accepted seeded legacy rows and rejection of a non-seed or newly added on-disk module marked `legacy`.
- Cover empty justification, zero/negative/non-integer `source_issue`, and `source_issue: true` for `new-module-justified` rows.
- Exercise `main` through an injected or fake runner so tests remain offline.

### UPDATED: python/larch/cli.py

- Register `("lint", "module-manifest")` to the new module's `main`.

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

## Testing strategy

- Run `make test-lint-module-manifest`.
- Run `make lint-module-manifest`.
- Run focused pytest for the new test module.
- Run `make py-lint` and `make lint` for acceptance coverage.

## Acceptance

- Run `make test-lint-module-manifest`.
- Run `make lint-module-manifest`.
- Run focused pytest for the new test module.
- Run `make py-lint` and `make lint` for acceptance coverage.
- `docs/linting.md` documents the manifest contract.

diff_added: 490
diff_deleted: 0
mechanical_churn: true
diff_lines: 490

## Test plan
(no test plan section in plan-file)
