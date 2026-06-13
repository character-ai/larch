## Proposed Design Outline

### Goals
- Unify `normalize_coder_scout_manifest` in `step2-implement.sh` with `filter_and_cap_manifest` by delegating to `scout-plan-archetypes-wrapper.sh --filter-manifest` (closes OOS_4)
- Investigate and close any remaining `parse-drafter-output.py` reserved-slug gap from OOS_2
- Verify OOS_1 and OOS_3 are fully covered and add missing test assertions if needed

### Non-goals
- Re-implementing or changing the scout manifest format
- Re-fixing OOS_1/OOS_2/OOS_3 core behavior (already addressed in #4061)
- Changing the scout archetype cap or reserved-slug set

### Approach sketch
- Replace inline jq in `normalize_coder_scout_manifest` with a shell-out to `scout-plan-archetypes-wrapper.sh --filter-manifest`
- Read `parse-drafter-output.py` to decide if it needs reserved-slug validation, then add it if so
- Check harness coverage for `normalize_coder_scout_manifest` in `test-step2-dispatch.sh` and update accordingly

### Surfaces in scope
- `skills/implement/scripts/step2-implement.sh` (normalize_coder_scout_manifest)
- `scripts/parse-drafter-output.py` (potential reserved-slug gap)
- `skills/implement/scripts/test-step2-dispatch.sh` (test coverage)
- Sibling `.md` files for any changed scripts

### Open questions
- Does `parse-drafter-output.py` need reserved-slug checking, or does the `--filter-manifest` step downstream make it redundant?
