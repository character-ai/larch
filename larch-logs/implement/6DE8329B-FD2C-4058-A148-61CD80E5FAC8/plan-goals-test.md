## Goal
Fix duplicate Implementation Plan header and broaden test-plan extractor in compose-plan-goals-test.sh

## Implementation Plan
## Implementation Plan

Two targeted fixes to `scripts/compose-plan-goals-test.sh` plus test and doc updates.

### Fix 1 — G6: strip duplicate Implementation Plan header

In `compose-plan-goals-test.sh`, the body-printing awk block (currently line 74) passes the raw plan file through, including any leading `## Implementation Plan` line that `/design` emits. The composer already outputs `## Implementation Plan` on line 72, so the header appears twice.

**Change**: extend the awk body-printer to skip the first occurrence of any `#{1,3} Implementation Plan` heading:

```bash
awk '/^#{1,3}[[:space:]]+Implementation[[:space:]]Plan[[:space:]]*$/ && !seen++ { next }
     /^#{1,3}[[:space:]]+[Tt]est[[:space:]][Pp]lan[[:space:]]*$/ { exit }
     { print }' "$PLAN_FILE"
```

`!seen++` evaluates true on the first match only (before increment), so the very first Implementation Plan heading is skipped; subsequent occurrences (if the plan body intentionally contains sub-section content) are printed normally.

### Fix 2 — G7: broaden test-plan section extractor

Expand the awk extractor (currently lines 59-63) to match these heading names at `##` or `###` depth: `Test plan`, `Tests`, `Testing`, `Verification`, `Test strategy`, `Verification strategy`. Add an exit-on-next-heading guard so the extracted content stops at the next heading rather than running to EOF.

```bash
test_plan="$(
    awk '
        found {
            if (/^#{1,3}[[:space:]]/) exit
            print
            next
        }
        /^#{1,3}[[:space:]]+([Tt]est[[:space:]][Pp]lan|[Tt]ests|[Tt]esting|[Vv]erification|[Tt]est[[:space:]][Ss]trategy|[Vv]erification[[:space:]][Ss]trategy)[[:space:]]*$/ { found = 1 }
    ' "$PLAN_FILE"
)"
```

### Files to modify

- `scripts/compose-plan-goals-test.sh` — both fixes above
- `scripts/test-compose-plan-goals-test.sh` — add 3 new test cases
- `scripts/compose-plan-goals-test.md` — update doc to reflect broadened extractor

### New test cases

(a) Plan with `## Implementation Plan` as first line → output has `## Implementation Plan` exactly once.
(b) Plan with `### Verification` section → content appears under `## Test plan` in output.
(c) Plan with `## Testing` section → content appears under `## Test plan`.
(d) Plan with `### Verification` but no `## Implementation Plan` header → no duplicate header (regression guard).

### Verification

Run `bash scripts/test-compose-plan-goals-test.sh` — all assertions pass.
Run `/relevant-checks` — pre-commit + agent-lint clean.

## Test plan
(no test plan section in plan-file)
