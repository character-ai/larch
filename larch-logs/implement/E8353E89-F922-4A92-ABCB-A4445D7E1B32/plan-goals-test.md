## Goal
Implement issue #4217: [IMPLEMENTING] [OOS] implement/review orchestration misc: stall recovery, cross-repo report, rebase-macro doc, dispatch jq — 6 items.

## Implementation Plan
## Plan

Four targeted fixes. Items 3 and 4 are skipped because they are already handled or need no change per Step 1c.

- **Item 1:** Add `submodule-edit-required-out-of-scope` as a distinct permanent-restriction class in `stall-recovery-report.sh`, parallel to `protected-path`.
- **Item 5:** Qualify the "Thin implementation" sentence in `skills/implement/SKILL.md` so only `4.r`, `7.r`, and `7a.r` are prompt-side foreground invocations; note that `1.r` arrives through the Step 0 bootstrap envelope.
- **Item 6:** Generalize `python/plan_scout.py` to accept `--mode review` in `filter_manifest_main`, then replace duplicate inline-jq normalization in `dispatch-panel.sh` with that Python helper.

Item 2 (`docs/configuration-and-permissions.md`) is already documented at lines 163-165 and 411. No change needed.

## Files to modify/create

### UPDATED: `skills/implement/scripts/stall-recovery-report.sh`

In `classify_from_evidence()`, add a new arm immediately after `protected-path-edit-required-out-of-scope)`:

```
submodule-edit-required-out-of-scope)
    MATCHED_CLASSIFIER_PATTERN=submodule-restricted-bail-token
    CLASSIFIED_FAILURE_CLASS=submodule-restricted
    return 0
    ;;
```

In `safe_matched_pattern_value()`, add `submodule-restricted-bail-token` to the allowlist.

In `safe_class_value()`, add `submodule-restricted` alongside `protected-path`.

In `retry_cap_for()`, add:

```
submodule-restricted) printf '1\n' ;;
```

In `code_retry_policy_lines()`, add `submodule-restricted` to the for-loop class list alongside `protected-path`.

### UPDATED: `skills/implement/scripts/stall-recovery-report.md`

In the **Retry Caps** table, add a row after `protected-path`:

```
| submodule-restricted | 1 | none |
```

In the explanatory sentence below the table, add: `` `submodule-restricted` means the external implementer hit a permanent submodule-edit restriction; Main Claude resumes Step 2 inline. ``

### UPDATED: `skills/implement/scripts/test-stall-recovery-report.sh`

Add regression cases near the existing `protected-path` cases.

Add a simple state-file classification case for `BAIL_REASON=submodule-edit-required-out-of-scope`. Assert:

- `FAILURE_CLASS=submodule-restricted`
- `BAIL_REASON=submodule-edit-required-out-of-scope`
- `MATCHED_CLASSIFIER_PATTERN=submodule-restricted-bail-token`
- `RESUME_HINT=step2-impl`

Add a stale transient-evidence precedence case mirroring `case7k2`:

- State file includes `BAIL_REASON=submodule-edit-required-out-of-scope` and stale transient evidence such as `NOTE=network timeout`.
- Assert `FAILURE_CLASS=submodule-restricted` and `MATCHED_CLASSIFIER_PATTERN=submodule-restricted-bail-token` (not transient-infra) — confirms the early bail arm beats stale transient evidence.

Add an argv-only precedence case mirroring `case7k3`:

- State file contains stale transient evidence (`NOTE=network timeout`).
- Pass `submodule-edit-required-out-of-scope` as the argv bail token.
- Assert the same pass as the state-file case above.

Add `submodule-restricted|1|none` to retry-policy expectation tables in the harness.

### UPDATED: `skills/implement/SKILL.md`

At the **Rebase Checkpoint Macro** "Thin implementation" line, change:

```
Each checkpoint is **one foreground Bash invocation** per Call-site registry row
```

to:

```
Checkpoints **4.r**, **7.r**, and **7a.r** are each one foreground Bash invocation per Call-site registry row. Checkpoint **1.r** is absorbed into `python/cli.py bootstrap invoke`; routing arrives through `ROUTE=` and `REBASE_RC=` in the Step 0 stdout envelope (see **Step 1.r routing** below).
```

In the Step 2 `STATUS=bailed` branch, add alongside the `protected-path-edit-required-out-of-scope` check:

- If `REASON=submodule-edit-required-out-of-scope`, print `**⚠ /implement: implementer bailed on submodule-restricted path; Main Claude will implement inline.**` and append the same sanitized warning to `Warnings` in `$IMPLEMENT_TMPDIR/execution-issues.md`.

In the escalation recording note for `FAILURE_CLASS=protected-path` with `RESUME_HINT=step2-impl`, extend to also cover `FAILURE_CLASS=submodule-restricted` with its own warning text: `**⚠ /implement: implementer bailed on submodule-restricted path; Main Claude will implement inline.**` (distinct from the protected-path `.claude-plugin/plugin.json` warning).

### UPDATED: `python/plan_scout.py`

Generalize `filter_plan_manifest` to accept `mode`:

```python
def filter_manifest(
    input_path: Path,
    output_path: Path,
    *,
    max_archetypes: int,
    mode: str = "plan-review",
) -> tuple[str, int]:
    ...
    result = validate_dynamic_manifest(data, max_archetypes=max_archetypes, mode=mode)
    ...
```

Keep existing call sites working by default.

In `filter_manifest_main`, add:

```python
parser.add_argument("--mode", default="plan-review")
```

Validate `--mode` against `{"review", "plan-review"}`. Raise `UsageError` for any other value. Pass the selected mode into the filter call.

### UPDATED: `skills/review/scripts/dispatch-panel.sh`

Replace the body of `normalize_scout_manifest()` with:

```bash
normalize_scout_manifest() {
    local input="$1" output="$2" max="${3:-3}" wrapper_out
    [[ -s "$input" ]] || return 1
    wrapper_out=$(python3 "${PLUGIN_ROOT}/python/cli.py" scout filter-manifest \
        "$input" "$output" --max-archetypes "$max" --mode review 2>/dev/null) || return 1
    local scout_status
    scout_status=$(awk -F= '$1=="SCOUT_STATUS"{print substr($0, index($0,"=")+1)}' <<< "$wrapper_out")
    case "$scout_status" in
        ok|empty) [[ -r "$output" ]] || return 1 ;;
        *) return 1 ;;
    esac
}
```

Keep `scout_manifest_is_valid()` as-is. Remove the old inline jq helpers (`def reserved:`, `def has_unsafe_wrapper_tag:`, `def has_unsafe_plan_delimiter:`, `def has_unsafe_rationale:`, and the `reduce .archetypes[]?` jq body).

### UPDATED: `python/test_plan_scout.py`

Add a test for `filter_manifest_main --mode review`:

- Input manifest has archetype name `arch` (reserved for `plan-review`, allowed for `review`).
- Assert `SCOUT_STATUS=ok` and the output manifest retains the `arch` archetype.

Add a test for `filter_manifest_main --mode plan-review`:

- Same input manifest.
- Assert `SCOUT_STATUS=ok` and `arch` is absent (or the archetype count drops).

### UPDATED: `skills/review/scripts/test-dispatch-panel.sh`

Add a pre-scouted-manifest case using `arch`:

- Input manifest with one `arch` archetype and one valid archetype.
- Run `dispatch-panel.sh --pre-scouted-manifest ... --dynamic-archetypes 2`.
- Assert `SCOUT_STATUS=pre-scouted`, normalized manifest contains `arch`, and dynamic slots are synthesized.

### UPDATED: `skills/review/scripts/dispatch-panel.md`

Update the pre-scout normalization paragraph: `normalize_scout_manifest()` now delegates reserved-slug filtering to `python3 python/cli.py scout filter-manifest --mode review`. Falls back to static-only review on failure. `scout_manifest_is_valid()` remains the downstream defensive validator.

## Edge cases

- **Lint parity:** `stall-recovery-report.sh lint` compares `doc_retry_policy_lines` to `code_retry_policy_lines`; both must include `submodule-restricted|1|none` or lint exits 1.
- **Stale transient evidence:** the new early bail arm at `protected-path-edit-required-out-of-scope` position in `classify_from_evidence()` runs before the transient-infra grep; test fixtures confirm it beats `NOTE=network timeout` evidence.
- **prompt_body repair:** `validate_dynamic_manifest()` in `python/plan_scout.py` already appends `REQUIRED_CLOSING_SENTENCE` (lines 194-195) when missing. No additional repair needed in `dispatch-panel.sh`.
- **normalize_scout_manifest fallback:** when the Python CLI exits non-zero or omits `SCOUT_STATUS=ok/empty`, the function returns 1; callers fall back to `SCOUT_STATUS=parse-failed` and static-only review.
- **review mode reserved slugs:** `arch`, `edge`, `innovation`, `pragmatic`, `requirements` remain reserved only in plan-review mode. Review mode accepts them as valid dynamic archetypes.

## Failure modes

1. **Retry-policy lint drift:** if `stall-recovery-report.md` table and `code_retry_policy_lines()` disagree, `bash skills/implement/scripts/stall-recovery-report.sh lint` exits 1.
2. **Python CLI unavailable in dispatch-panel.sh:** `normalize_scout_manifest` returns 1; review proceeds static-only. Acceptable degradation.
3. **PLUGIN_ROOT:** `dispatch-panel.sh` derives it at line 7 from `CLAUDE_PLUGIN_ROOT`; no new risk.

## Testing strategy

Run in order:

1. `bash skills/implement/scripts/test-stall-recovery-report.sh`
2. `bash skills/implement/scripts/stall-recovery-report.sh lint`
3. `python3 -m pytest python/test_plan_scout.py -v -k "filter_manifest or review_mode"`
4. `bash skills/review/scripts/test-dispatch-panel.sh`
5. `bash scripts/relevant-checks.sh`

Optional smoke:

```
python3 python/cli.py scout filter-manifest /tmp/m.json /tmp/out.json --mode review --max-archetypes 3
python3 python/cli.py scout filter-manifest /tmp/m.json /tmp/out.json --mode plan-review --max-archetypes 3
```

## Acceptance

- `FAILURE_CLASS=submodule-restricted` appears in the classification output for `bail=submodule-edit-required-out-of-scope`.
- `RESUME_HINT=step2-impl` is emitted for that class.
- `stall-recovery-report.sh lint` exits 0 with the new `submodule-restricted` row in both code and doc retry tables.
- `python3 -m pytest python/test_plan_scout.py` passes including the new `--mode review` test.
- `bash scripts/relevant-checks.sh` passes.

diff_lines: 215

## Test plan
(no test plan section in plan-file)
