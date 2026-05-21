## Goal
Fix manifest.json schema: remove post-flush fields, add steps_ran flags, fix OUTCOME default, update audit tools

## Implementation Plan

Goal: Fix manifest.json schema (remove post-flush fields pr_number/status, add steps_ran), fix
OUTCOME="bailed" default in write-final-report.sh, and make audit tools work without pr_number.

### 1. scripts/larch-log.sh — manifest template and commit

**write_manifest_file** (lines ~170-196):
- Remove `"pr_number": null,` from the JSON template
- Remove `"status": "$status",` from the JSON template (status param was "in-progress" at init)
- Add `"steps_ran": {}` to the template (additive field for per-step flags)
- Remove the `$status` parameter from `write_manifest_file` call at line 224

**manifest subcommand** (lines ~380-430):
- Add special handling for dotted key `steps_ran.<step>`: parse the step name after the dot
  and use jq `(.steps_ran[$step] = true/false)` syntax to set nested flags
- Keep existing flat-key handling unchanged

**commit subcommand** (lines ~432-500):
- Before copying files from tmpdir to repo (line ~456), add jq to refresh `updated_at`:
  `jq --arg ts "$(now_utc)" '.updated_at = $ts' "$src_path/manifest.json" > tmp && mv tmp "$src_path/manifest.json"`
  so the committed manifest reflects flush time, not initial-write time

**larch-log.md**: Remove pr_number from schema docs, add steps_ran description, update the
manifest command note about `pr_number` being numeric.

### 2. scripts/implement-finalize.sh — teardown function (~line 1493)

Current branching sets `status` and `pr_number` fields via `larch-log.sh manifest`. Remove:
- `--field "status=stalled"` 
- `--field "status=done"`
- `--field "pr_number=$pr_number"`
Keep:
- `--field "stalled_at_step=$stall_step"` (not a post-flush field, set on stall path)

The entire `elif [ -n "$pr_number" ]` branch that only set status+pr_number can be removed.
The `stall_tracking` branch stays but only writes `stalled_at_step`.
The `design_only` branch that only wrote `status=done` can be removed entirely.

### 3. skills/implement/scripts/write-final-report.sh — OUTCOME default

Line 123: Remove `OUTCOME="bailed"` — replace with `OUTCOME=""`
The existing if/elif chain sets OUTCOME to stalled/forked-dry-run/design-only/merged/etc.
When none match (bailed before any of those), OUTCOME stays "".
Line 140: `if [ "$BAIL_USER" = "true" ] && [ "$OUTCOME" = "" ]` → set `OUTCOME="bailed-needs-user-input"`
When OUTCOME is empty and BAIL_USER=false, it means the run bailed early; render as "bailed" or
omit the Outcome line.

Actually simpler: keep the `OUTCOME="bailed"` but only emit the Outcome: line in render-run-summary.sh
when OUTCOME is not one of the "success" outcomes. OR: replace the default with `OUTCOME="bailed"` 
only AFTER the if/elif chain when no condition matched.

Best approach: move `OUTCOME="bailed"` to after the chain as a fallthrough:
```
OUTCOME=""
if stall → "stalled"
elif forked → "forked-dry-run"
...
fi
if [ -z "$OUTCOME" ]; then OUTCOME="bailed"; fi
```
Then suppress PR: N/A and Outcome: bailed lines ONLY when they aren't informative.

For the "PR: N/A" suppression: in render-run-summary.sh, only emit the PR line when 
`$pr_disp != "N/A"`.

For the "Outcome: bailed" suppression: emit Outcome line only when outcome is NOT empty 
and NOT "pr-created" or "merged" (i.e., only on bad outcomes). Actually, the issue says
"its absence then means the run reached flush successfully". So:
- Remove Outcome: line entirely from render-run-summary.sh header 
- Only add Outcome: line via the notes_tmp section when OUTCOME is "bailed*" or "stalled"

Actually simplest fix: in render-run-summary.sh, suppress the Outcome: line when OUTCOME 
is one of the success variants (merged, admin_merged, pr-created, pr-created-draft, design-only,
forked-dry-run). Or: only show it when OUTCOME starts with "bailed" or is "stalled".

### 4. scripts/render-run-summary.sh — suppress Outcome/PR lines conditionally

Lines 187-195:
- Line 188: `printf -- '- **Outcome**: %s\n'` → wrap in a condition:
  `case "$OUTCOME" in bailed*|stalled) printf -- '- **Outcome**: %s\n' "$OUTCOME" ;; esac`
- Line 195: `printf -- '- **PR**: %s\n' "$pr_disp"` → only print when `$pr_disp != "N/A"`

### 5. .claude/skills/audit-runs/scripts/audit-scan-run.sh — steps_ran gate

`scan_required_file_presence` (lines ~68-105):
- Before the while loop, read manifest.json to load `steps_ran`:
  `steps_ran_json=$(jq -r '.steps_ran // empty' "$RUN_DIR/manifest.json" 2>/dev/null || echo "{}")`
- In the loop, after parsing `_condition`, check if condition is non-empty and non-"always":
  `step_ran=$(printf '%s' "$steps_ran_json" | jq -r '.[env.COND] // empty' 2>/dev/null || true)`
  If `step_ran = "false"`, skip the missing check and continue (not a FAIL).

### 6. .claude/skills/audit-runs/scripts/audit-map-runs.sh — swap primary/fallback

Current: primary=pr_number, fallback=parent-issue.md+Closes#N

New order:
1. **Primary**: `gh pr view PR_NUM` → extract `Closes #N` → find `parent-issue.md` with `ISSUE_NUMBER=N`
2. **Fallback**: scan manifest.json for `pr_number == PR_NUM` (for old-format runs)

The swap is mechanical: move the existing fallback block to before `pick_newest_manifest_among_pr`.

### 7. Test updates

**scripts/test-larch-logs-manifest.sh**:
- Remove the `.status == "in-progress"` assertion
- Add: no `.pr_number` field, `.steps_ran` is an object, `updated_at` refreshed after manifest cmd

**tests/test-audit-runs.sh** — add Test 50 and Test 51:
- Test 50: `required-file-presence` does NOT fail when `manifest.json` has `steps_ran.step9a1=false`
  and `oos-issues.ndjson` / `run-statistics.md` are absent
- Test 51: `required-file-presence` DOES fail when `manifest.json` has no `steps_ran` 
  and `oos-issues.ndjson` is absent (step9a1 default = ran)

### Sibling .md updates
- `scripts/larch-log.md`: schema section
- `scripts/implement-finalize.md`: teardown section  
- `.claude/skills/audit-runs/scripts/audit-scan-run.md`: steps_ran gate
- `.claude/skills/audit-runs/scripts/audit-map-runs.md`: primary/fallback swap
- `scripts/render-run-summary.md`: Outcome/PR conditional
- `skills/implement/scripts/write-final-report.md`: OUTCOME logic


## Test plan
- `make test-larch-logs-manifest` passes
- `bash .claude/skills/audit-runs/scripts/test-audit-runs.sh` passes
- `/relevant-checks` passes
