## Proposed Design Outline

### Goals
- Fix Step 5c publish-tail composed-plan validation to resolve repo-relative scripts against the consumer repo, ending false-positive `missing-script` defects.
- Make consumer-repo-root resolution a single shared definition so the Step 2b and Step 5c validation sites cannot drift again.
- Distinguish `missing-script` defects from genuinely unsafe tokens in the Step 5c operator-facing validator-defect message.

### Non-goals
- Changing Step 2b postplan validation behavior; it is already correct.
- Changing the dual-root existence-check semantics inside `plan_quality.py`.
- Removing the `--skip-validate` Override path or altering the Step 5c exit-code / result-env contract.

### Approach sketch
- Lift `_consumer_repo_root()` into a shared module; have `design_postplan.py` and `design_publish.py` both import that one definition.
- In `design_publish.py`, pass `--repo-root str(_consumer_repo_root() or plugin_root)` and set `CLAUDE_PLUGIN_ROOT` in the validate env, mirroring Step 2b exactly.
- Audit every `plan validate` / `validate-commands` caller; harmonize any that pass the plugin root as `--repo-root`.
- Surface a `missing-script` vs unsafe-token breakdown in the Step 5c validator-defect operator message.

### Surfaces in scope
- `python/design_publish.py` (defect site + operator message)
- `python/design_postplan.py` (reference; switch to shared import)
- `python/plan_quality.py` (likely home for the shared helper)
- `python/test_design_publish.py` (regression test)
- `skills/design/SKILL.md` shared validator-failure section (operator-message wording)

### Open questions
- Exact home for the shared helper (`plan_quality.py` vs a small repo-root util). Resolved during plan drafting.
