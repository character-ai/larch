## Proposed Design Outline

### Goals
- Give `submodule-edit-required-out-of-scope` a permanent failure class (no retry) and operator warning in `stall-recovery-report.sh`.
- Document that Tier B `/implement` runs file stall-recovery reports to the public upstream larch repo using the operator's GitHub identity.
- Correct the Rebase Checkpoint Macro "Thin implementation" paragraph in `skills/implement/SKILL.md` to reflect that `1.r` is now absorbed into `python/cli.py bootstrap invoke`.
- Replace the duplicate inline jq reserved-slug filter in `dispatch-panel.sh` with a call to `python3 cli.py scout filter-manifest --mode review`.

### Non-goals
- Items 3 and 4 from the combined issue (already fixed / no change needed).
- Any change to the classification system beyond adding the one new `submodule-restricted` case.
- Adding new harness coverage for the SKILL.md doc edit.

### Approach sketch
- Item 1: add a `submodule-edit-required-out-of-scope)` arm in `classify_from_evidence()` (mirroring `protected-path-bail-token`) with a new class, retry cap of 1, and `safe_matched_pattern_value` allowlist entry.
- Item 2: add a short paragraph or bullet to the Tier B section of `docs/configuration-and-permissions.md`.
- Item 5: one-line qualification in the "Thin implementation" paragraph in `skills/implement/SKILL.md`.
- Item 6: add `--mode review` to `filter_manifest_main` in `python/plan_scout.py`; update `normalize_scout_manifest()` in `dispatch-panel.sh` to call the Python CLI and then apply the prompt_body repair step inline.

### Surfaces in scope
- `skills/implement/scripts/stall-recovery-report.sh`
- `docs/configuration-and-permissions.md`
- `skills/implement/SKILL.md`
- `skills/review/scripts/dispatch-panel.sh`
- `python/plan_scout.py`
- `python/cli.py` (filter-manifest dispatch)
- `python/test_plan_scout.py` (new test for --mode review)
- `skills/review/scripts/dispatch-panel.sh` sibling `.md` (if behavior changes)

### Open questions
- None.
