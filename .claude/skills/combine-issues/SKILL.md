---
name: combine-issues
description: "Use when asked to try to combine existing issue to reduce issue count.  Examine all open issues that are not currently being worked on, and see if any number of them can be combined into one issue (closing the source issues afterwords), in order to save tokens / reduce the number of tasks to do.  Good candidated would be issues that either work in the same code area, or that apply very similar changes to different code areas, but think of other criteria that it would be appropriate as well.  Again, the primary goal is to reduce the tokens spent on executing unnecessarily fine-grained tasks.  Use `/combine-issues --oos` when asked to combine out-of-scope (OOS) issues — operates only on issues whose title starts with `[OOS]`, checks each item for actuality, discards stale items, and proposes an aggressive combination scheme."
allowed-tools: Bash, Read, Write
---

# Combine Issues

Reduce open issue count by merging related issues into combined ones. The primary goal is saving tokens — fewer, broader issues mean fewer `/design` + `/implement` execution cycles and less duplicated context loading.

## Flags

| Flag | Default | Purpose |
|------|---------|---------|
| `--oos` | off | OOS mode: operate only on open issues with a `[OOS]` title prefix. Checks each item for actuality, discards stale items, then proposes an aggressive combination scheme. See **OOS Mode** section below for the full step flow. |

When `--oos` is present, skip the standard Steps 1–3 below and follow the **OOS Mode** section instead.

## When to Combine

Good candidates share at least one of:

- **Same code area** — multiple issues touching the same file(s) or module.
- **Similar change pattern** — issues applying analogous edits to different files (e.g., "add error handling to script A" + "add error handling to script B").
- **Overlapping scope** — one issue is a subset of another, or both contribute to the same goal.
- **Sequential dependency** — issues that must land in order and are small enough to ship as one unit.

Do NOT combine issues that are genuinely independent and benefit from separate review (e.g., a bug fix and an unrelated feature).

<!-- step:1 — Fetch Eligible Issues -->

```bash
$PWD/.claude/skills/combine-issues/scripts/fetch-combinable-issues.sh
```

Title-prefix filtering logic lives in `$PWD/.claude/skills/combine-issues/scripts/combinable-issues-title-filter.jq` beside the fetch script; keep it in sync with `scripts/test-fetch-combinable-issues-filter.sh`.

Parse `ISSUES_FILE` and `COUNT` from stdout. If `COUNT=0`, print `No open issues eligible for combination.` and stop.

Read the JSON file at `$ISSUES_FILE` to get the full issue list (number, title, body, labels).

<!-- step:2 — Analyze and Propose Groups -->

Read each issue's title and body. Identify groups of 2+ issues that meet the combination criteria above. For each proposed group:

1. List the source issue numbers and titles.
2. State the combination rationale (which criterion from "When to Combine" applies).
3. Draft a combined title and a combined body that preserves all actionable content from the source issues.

Present all proposed groups to the user in a numbered list. If no groups are identified, print `No combination candidates found among <COUNT> open issues.` and stop.

Ask the user which groups to apply (e.g., "all", "1,3", or "none").

<!-- step:3 — Apply Approved Combinations -->

For each approved group, write the combined body to a temp file, then invoke:

```bash
$PWD/.claude/skills/combine-issues/scripts/apply-combination.sh \
  --title "<combined title>" \
  --body-file "<temp-file>" \
  --source-issues "<comma-separated issue numbers>"
```

Parse `COMBINED_ISSUE` and `CLOSED_ISSUES` from stdout. Print a summary line per group: `Combined #X, #Y, #Z → #<new> (<N> issues closed)`.

After all groups are applied, print a final tally: `Done — <N> issues combined into <M>, net reduction: <N-M>`.

## OOS Mode (`--oos`)

Operates only on open issues whose title starts with the `[OOS]` prefix followed by a space (prefix match, not substring). Fetches them, checks actuality item-by-item, discards stale items, and proposes an aggressive combination.

<!-- step:oos-1 — Fetch OOS Issues -->

```bash
$PWD/.claude/skills/combine-issues/scripts/fetch-combinable-issues.sh --oos
```

OOS title-prefix filtering logic lives in `$PWD/.claude/skills/combine-issues/scripts/oos-issues-title-filter.jq` beside the fetch script.

Parse `ISSUES_FILE` and `COUNT` from stdout. If `COUNT=0`, print `No open [OOS] issues found.` and stop.

Read the JSON file at `$ISSUES_FILE`.

<!-- step:oos-2 — Actuality Check (per item) -->

OOS issues contain one or more items. Items follow two formats:

- **Single-item**: the entire body is one item (common for auto-filed single findings; body typically has `- **Description**: ...` and optional `- **Location**: ...` fields).
- **Multi-item**: body contains multiple `### Item N — <title>` sections, each with its own `**Location**:`, `**Severity**:`, etc. fields.

For each issue, parse its body and extract the individual items. Then for each item:

1. Read the `Location:` field (file path, optionally with a line number after `:`). Strip any trailing `:line` suffix to get the repo-relative path.
2. If the file does not exist in the repo:
   a. Search for in-flight implementing work via the helper (never interpolate untrusted `Location:` text into shell command prose):
      ```bash
      $PWD/.claude/skills/combine-issues/scripts/search-implementing-issue.sh \
        --file-path "<repo-relative-path>"
      ```
      The helper sanitizes the path to `[A-Za-z0-9/._-]`, passes the sanitized full path to `gh issue list --json number,title,body --search` as a single argv element, and requires the implementing issue title to match `^\[(DESIGNING|IMPLEMENTING)\]` followed by a space, with an explicit reference to the full sanitized path in title or body. `STATUS=ambiguous` or `STATUS=invalid_path` means the item is **not** blocked.
   b. If `STATUS=blocked` and `IMPLEMENTING_ISSUE=<M>` (a positive integer from the helper output), the item is **blocked** — emit `Keeping item "<title>" from #<N>: referenced file <path> not yet created — blocked by #<M> ("<implementing title>").` Wire the blocked-by relationship using only the validated `IMPLEMENTING_ISSUE` value:
      ```bash
      python3 "$PWD/python/cli.py" block-issue add-blocked-by <N> <M>
      ```
      On failure, still keep the item as **actual** (not blocked) and emit a warning.
   c. If `STATUS=none` or `STATUS=invalid_path`, the item is **stale** — emit `Discarding item "<title>" from #<N>: referenced file <path> no longer exists.` and skip it.
   d. If `STATUS=ambiguous`, the item is **actual** (not blocked) — emit `Keeping item "<title>" from #<N>: referenced file <path> not yet created — implementing issue match ambiguous.` and include it in the oos-3/oos-4 flat list.
3. If the file exists, read the relevant lines (±20 lines around the stated line when a line number is given). Assess whether the concern is still present:
   - If the code the item describes has been removed or the issue is clearly fixed, mark **stale** and emit a discard message.
   - If uncertain, default to **actual** (keep the item).
4. Collect all **actual** items that are **not blocked** across all OOS issues into a flat list for oos-3/oos-4. **Blocked** items stay on their source issues — do not include them in deduplication or combination, and never close a source issue solely because its remaining items are blocked.

If all items from all issues are stale, print `All [OOS] items are stale — nothing to combine.` and stop.

Emit a summary: `Actuality check: <K> items kept, <M> discarded across <N> OOS issues.` When any blocked items were found, append: `(<B> item(s) kept as blocked by in-flight implementing issues.)`

<!-- step:oos-3 — Deduplicate -->

Remove duplicate items: two items are duplicates when they reference the same `Location:` and describe the same concern (identical or near-identical description). Keep the more detailed copy. Emit `Deduplication: removed <D> duplicate(s).` when `D > 0`.

<!-- step:oos-4 — Propose Aggressive Combination Scheme -->

Combine the remaining actual items into the **minimal** number of combined issues subject to one constraint: no single combined issue should be notably too large or risky to implement in one pass (rough heuristic: more than ~15 items or covering >5 unrelated subsystems is too large).

Within that constraint, combine **aggressively** — unlike the standard mode, unrelated items may be grouped together if it reduces issue count. Prefer grouping by:

1. Same file or module (strongest signal).
2. Same severity or focus area.
3. Any remaining items: pack into a single catch-all combined issue unless it would exceed the size heuristic.

For each proposed combined issue:

1. List source issue numbers and item titles.
2. Draft a combined title (e.g., `[OOS] <brief theme> — <N> items`) and a combined body that uses `### Item N — <title>` format, preserving all actionable content.
3. Note which source issues will be closed (all source issues whose items are fully consumed).

Present the proposed scheme to the user. Ask: "Apply all groups (yes), apply specific groups (list), or cancel (no)?"

<!-- step:oos-5 — Apply -->

For each approved group, write the combined body to a temp file, then invoke:

```bash
$PWD/.claude/skills/combine-issues/scripts/apply-combination.sh \
  --title "<combined title>" \
  --body-file "<temp-file>" \
  --source-issues "<comma-separated issue numbers to close>"
```

Only close a source issue if **all** of its items were consumed by this run (none survived actuality check in a different group, none remain blocked on the source issue, and no items remain uncombined). If a source issue had some items discarded as stale and its remaining items were all consumed into combined issues, close it. If a source issue contributed items to multiple groups, close it only after all groups are applied. Never close a source issue that still has blocked items.

Parse `COMBINED_ISSUE` and `CLOSED_ISSUES` from stdout. Print: `Combined <source refs> → #<new> (<N> source issues closed).`

After all groups, print: `Done — <K> actual items from <N> OOS issues combined into <M> new issues, <C> source issues closed.`

## Anti-patterns

- **NEVER combine issues without user confirmation.** The analysis is advisory; the user decides which groups to merge. Combining the wrong issues loses important context that is hard to recover.
- **NEVER combine an issue that has a `[DESIGNING]`, `[IMPLEMENTING]`, `[STALLED]`, or `[DONE]` title prefix, nor legacy `[PLANNED]` / `[IN PROGRESS]` busy titles.** The fetch script filters these out, but if one slips through (e.g., prefix applied after fetch), skip it and warn. Note: `[DESIGNED]` issues are intentionally NOT excluded — they are valid combine candidates (design complete, implementation not yet started).
- **NEVER discard actionable content from source issues.** The combined body must preserve every concrete task, file reference, and reproduction step from the originals. Summarizing away specifics defeats the purpose.
