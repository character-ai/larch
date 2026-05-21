## Goal
Fix aggregate-findings.sh validator: treat zero FINDING blocks as valid clean pass and normalize slot labels with trailing parentheticals

## Implementation Plan

### Objective
Fix the aggregate-findings.sh inline Python validator to correctly handle two failure shapes observed in production (issue #2536):
1. Zero FINDING blocks in aggregator output should be treated as a valid clean pass (not a validation failure)
2. Reviewer slot labels with trailing parenthetical suffixes like `(via C.2 coverage gap)` should be normalized before matching against the input slot set

### Files to Modify
- `skills/review/scripts/aggregate-findings.sh` — inline Python validator (`validate_py` heredoc)
- `skills/review/scripts/test-aggregate-findings.sh` — regression harness

### Approach

#### Fix 1 (zero FINDING blocks)
In the inline Python validator (`validate_py`), change:
```python
    blocks = output_blocks(outtext)
    if not blocks:
        print("no output FINDING blocks", file=sys.stderr)
        return 1
```
to:
```python
    blocks = output_blocks(outtext)
    if not blocks:
        return 0
```
Zero output FINDING blocks is a legitimate state when the aggregator determines all input findings are duplicates or otherwise resolved. The validator should treat this as a clean pass; the bash code that follows will copy `cand` to `FINDINGS_FILE` and `MERGED_COUNT` will be 0.

#### Fix 2 (labelled slot normalization)
Add a `normalize_slot` function before `main()`:
```python
def normalize_slot(sl):
    return re.sub(r'\s*\([^)]*\)\s*$', '', sl).strip()
```
Then in the output block loop:
- Use `normalize_slot(sl)` when checking `oos_only_slots`: `if normalize_slot(sl) in oos_only_slots:`
- Use `normalize_slot(sl)` when checking `input_slot_set` and adding to `all_out_slots`:
```python
        for sl in slots:
            normalized = normalize_slot(sl)
            if normalized not in input_slot_set:
                print("unknown reviewer slot in merge output: %r" % (sl,), file=sys.stderr)
                return 1
            all_out_slots.add(normalized)
```
This strips `(via C.2 coverage gap)` and similar suffixes from output slot names before matching. Input slots are not normalized (they come from collect-findings.sh and should already be clean).

#### sibling doc update
Update `skills/review/scripts/aggregate-findings.md` to document the new behavior:
- Zero output FINDING blocks is now a valid clean pass
- Slot names in output are normalized (trailing parentheticals stripped) before matching

#### Regression tests
Add two test cases to `test-aggregate-findings.sh`:

1. **zero_findings test**: New `AGGREGATE_STUB_MERGE_KIND=zero_findings` stub writes narrative text (no FINDING blocks) to the output file. Test asserts `AGGREGATED=true`, `REASON=ok`, `MERGED_COUNT=0`, and zero FINDING blocks in the updated findings file.

2. **labelled_slot test**: New `AGGREGATE_STUB_MERGE_KIND=labelled_slot` stub writes a finding with `cursor-a-output.txt (via C.2 coverage gap)` as a reviewer slot (while input has `cursor-a-output.txt`). Test asserts `AGGREGATED=true`, `REASON=ok`, `MERGED_COUNT=1`.

### Testing Strategy
Run `make test-aggregate-findings` to verify all existing tests still pass and new tests pass. Also run `/relevant-checks` (which includes `make lint`).

### Edge Cases
- `normalize_slot` uses `re.sub(r'\s*\([^)]*\)\s*$', '', sl).strip()` — this handles the space before `(` and only strips the last parenthetical, leaving the base filename intact.
- When `not blocks` returns 0, the bash code copies `cand` to `merged_tmp`; if `cand` is non-empty (has narrative text), `[[ -s "$merged_tmp" ]]` passes and `FINDINGS_FILE` is updated with zero FINDING blocks.
- `all_out_slots` stores normalized names so the `missing` check (comparing to `input_slot_set` which has original names) works correctly.

diff_lines: ~50

## Test plan
(no test plan section in plan-file)
