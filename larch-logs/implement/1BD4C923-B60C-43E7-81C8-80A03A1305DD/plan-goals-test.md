## Goal
Add stderr breadcrumb to parse-input.sh and authoring-caution doc note to SKILL.md

## Implementation Plan

Goal: Add a stderr breadcrumb to `parse-input.sh` and authoring-caution doc note to `SKILL.md`, plus update the test harness.

### Files to modify

1. `skills/issue/scripts/parse-input.sh` — add breadcrumb + PARSE_MODE tracking
2. `skills/issue/SKILL.md` — add authoring-caution note in batch-mode section; append preview-parse note to --dry-run flag
3. `skills/issue/scripts/test-parse-input.sh` — pin breadcrumb shape for single-item and multi-item generic batches
4. `skills/issue/scripts/parse-input.sh.md` — update sibling doc to mention breadcrumb behavior
5. `skills/issue/scripts/test-parse-input.sh.md` — update sibling doc to mention new test cases

### 1. parse-input.sh changes

**PARSE_MODE tracking**: initialize `PARSE_MODE=generic` alongside other state variables (around line 150).
In the OOS heading branch at line 397 (`CURRENT_MODE="oos"`), also set `PARSE_MODE=oos`.

**Breadcrumb**: After the final `emit_kv ITEMS_TOTAL "$ITEM_INDEX"` (line 495), add a bash block using `larch_errf` (already available via lib-quiet.sh source) to emit:
```
▶ parse-input: N items parsed (mode=<oos|generic>): 1=<title-truncated-60>, 2=<title-truncated-60>, …
```

Bash implementation (placed after `emit_kv ITEMS_TOTAL "$ITEM_INDEX"`, before the final implicit exit 0):
```bash
{
    larch_errf '▶ parse-input: %s items parsed (mode=%s)' "$ITEM_INDEX" "$PARSE_MODE"
    if (( ITEM_INDEX > 0 )); then
        larch_errf ':'
        for i in $(seq 1 "$ITEM_INDEX"); do
            title_var="ITEM_${i}_TITLE"
            t="${!title_var}"
            # Truncate to 60 chars with ellipsis on overflow
            if (( ${#t} > 60 )); then t="${t:0:60}…"; fi
            sep=" "
            if (( i > 1 )); then sep=", "; fi
            larch_errf '%s%s=%s' "$sep" "$i" "$t"
        done
    fi
    larch_errf '\n'
}
```

However, note that `larch_errf` writes to FD 4 (the original stderr) when quiet mode is active, or to stderr (&2) otherwise. This is exactly what we want: the breadcrumb goes to the caller's visible stderr, not the quiet log.

**Important**: `larch_errf` takes printf format strings, so the format and data must be separate. The simple alternative using `larch_err` (which takes literal strings):
```bash
_breadcrumb="▶ parse-input: ${ITEM_INDEX} items parsed (mode=${PARSE_MODE})"
if (( ITEM_INDEX > 0 )); then
    _breadcrumb+=":" 
    for i in $(seq 1 "$ITEM_INDEX"); do
        title_var="ITEM_${i}_TITLE"
        t="${!title_var}"
        if (( ${#t} > 60 )); then t="${t:0:60}…"; fi
        sep=" "
        if (( i > 1 )); then sep=", "; fi
        _breadcrumb+="${sep}${i}=${t}"
    done
fi
larch_err "$_breadcrumb"
```

Using `larch_err` (string concatenation into a single string, then one call) is cleaner and avoids printf format-string risks with user-supplied data.

### 2. SKILL.md changes

**Batch mode section** (after line 110, which ends the parser description): Insert after the existing paragraph about `Parser regression coverage lives in ...`:

> **Authoring caution (generic fallback)**: in batch-mode files using the generic `### <title>` + body fallback, body content must not start a line with `### ` — that token is the item-boundary separator. Use `####` or deeper for subsections within body sections, or use a different markup convention (lists, bold leaders) for sub-items. OOS-formatted input files do not have this constraint because the OOS-specific absorption rules disambiguate `### <subheading>` inside an OOS Description; the constraint applies only to the generic fallback path. Use `--dry-run` to preview a parse before creating; the stderr breadcrumb (`▶ parse-input: …`) emitted on every parse also shows the item count.

**`--dry-run` flag description** (line 37, append to existing bullet): Append after "no `ISSUE_<i>_GO_POSTED` lines are emitted.":

> **Preview-parse use case**: when authoring batch-mode input files by hand, run with `--dry-run` first to inspect `ITEMS_TOTAL` and per-item titles on stderr (via the `▶ parse-input: …` breadcrumb) and stdout (`ITEM_<i>_TITLE=…` lines) before committing to the create pass.

### 3. test-parse-input.sh changes

Add two test cases after the existing negative tests (before the final Summary line):

**Test A — single-item generic breadcrumb**: create a one-item generic batch, run parser, capture stderr, assert it contains `▶ parse-input:` prefix with `1 items parsed` and the title.

**Test B — two-item generic breadcrumb**: create a two-item generic batch (with `### A.` subsection in body to replicate the foot-gun scenario), run parser, capture stderr, assert `▶ parse-input:` with `12 items parsed` (documenting the known behavior) or a simpler 2-item batch to assert `2 items parsed`.

Actually per the issue acceptance criteria: "pin the prefix `▶ parse-input:` so future drift is caught". The test should be on a clean 2-item input that parses as 2 items (not the foot-gun case, which would parse as 12).

Test cases:
- Single-item generic: `### My title\nbody text` → stderr contains `▶ parse-input: 1 items parsed (mode=generic): 1=My title`
- Two-item generic: two sections → stderr contains `▶ parse-input: 2 items parsed (mode=generic):`
- Single-item OOS: one OOS item → stderr contains `(mode=oos)`

### 4+5. Sibling .md updates (parse-input.sh.md and test-parse-input.sh.md)

Read both sibling .md files and add brief mentions of the new breadcrumb behavior and test coverage respectively.


## Test plan

- `bash skills/issue/scripts/test-parse-input.sh` passes (new assertions green)
- `/relevant-checks` passes (pre-commit + agent-lint)
- No changes to stdout contract (breadcrumb goes only to stderr)
