# Anchor Comment — Canonical Body

**Consumer**: `/implement` Steps 0.5 (anchor planting, fragment composition) and 11 (post-execution `execution-issues` refresh). Load this file when composing any anchor-section fragment, planting a seed anchor, or invoking `tracking-issue-write.sh upsert-anchor`.

**Contract**: canonical anchor body reference — anchor first-line marker, seed placeholder, full canonical template (all 11 sections including the three load-bearing literals and the `## Implementation Plan` synthesis source heading), section markers list, body-level collapse priority, voting tally extraction guidance, and compose-time sanitization rule. Single normative source for the anchor comment's shape.

**When to load**: before composing any anchor-section fragment or invoking `tracking-issue-write.sh upsert-anchor` at Steps 0.5 and 11. Do NOT load at Step 9a.1 — use `anchor-template-oos-pipeline.md` instead. Do NOT load at Step 2 Q/A upsert — use `anchor-template-execution-issues.md` instead.

**Sibling files**:
- `anchor-template-oos-pipeline.md` — Step 9a.1 OOS pipeline procedure
- `anchor-template-execution-issues.md` — execution-issues section format + sanitization (Step 2 Q/A)
- `anchor-template-quick-mode.md` — Quick-mode anchor guidance
- `anchor-comment-template.md` — thin overview: voting tally guidance, edit-in-sync pointers

---

## Anchor first-line marker

Every anchor comment begins with exactly this line (`<N>` is the tracking issue number):

```
<!-- larch:implement-anchor v1 issue=<N> -->
```

Rationale: the HTML-comment prefix renders invisibly in GitHub's comment UI but is machine-greppable by `tracking-issue-write.sh upsert-anchor`'s marker-search fallback when no explicit `--anchor-id` is passed. The `v1` version is strict: the write script matches only `<!-- larch:implement-anchor v1`-prefixed comments, and `tracking-issue-read.sh`'s anchor-marker filter uses the same strict prefix. Future anchor versions (v2, …) introduce a new marker handled by a new tool version.

Mixed-version state on a single issue (a legacy `<!-- larch:implement-anchor v1` comment alongside a hypothetical future `<!-- larch:implement-anchor v2`) fails closed: Phase 1's `upsert-anchor` exits 2 with `FAILED=true ERROR=multiple anchor comments found (ids: <list>)` any time it finds more than one v1-prefixed comment.

### Seed-only visible placeholder line

When `scripts/assemble-anchor.sh` walks `SECTION_MARKERS` and finds **every** fragment absent, zero-byte, or whitespace-only (the seed case at Step 0.5 Branch 2/3/4 plant), the assembled body carries one extra italic-markdown line between the first-line HTML marker and the first `<!-- section:plan-goals-test -->` open marker:

```
_/implement run in progress — sections below populate as the run proceeds._
```

This line is suppressed as soon as any fragment contains a non-whitespace byte — i.e., from the first progressive upsert at Step 1 onward, the populated-anchor body shape returns to the canonical template above. The placeholder exists solely so the freshly planted seed comment renders as visibly non-empty in GitHub's UI (issue #431); without it the seed body is 100% HTML comment markers and looks blank to humans. Because the line lives **outside** every section interior (between line 1 and the first `<!-- section:... -->`), it does not interact with `tracking-issue-write.sh`'s per-section truncation algorithm or with any consumer that parses sections by marker-pair boundaries. See `scripts/assemble-anchor.md` "Seed-only visible placeholder" for the predicate definition and the underlying contract.

## Canonical template

````markdown
<!-- larch:implement-anchor v1 issue=<N> -->

<!-- section:plan-goals-test -->
## Goal

<one-sentence objective>

## Implementation Plan

<full implementation plan body read from PLAN_FILE — approach, files to modify, edge cases, testing strategy. The `## Implementation Plan` / `## Goal` / `## Test plan` headings here are FRAGMENT-level wrapping written by /implement Step 1; do NOT assume PLAN_FILE itself contains those headings — /design writes plain plan content to plan.txt.>

## Test plan

<testing strategy extracted from the implementation plan>

<!-- section-end:plan-goals-test -->

<!-- section:plan-review-tally -->
## Plan Review Voting Tally

<per-finding YES/NO/EXONERATE counts and reviewer scoreboard from /design Step 3>

## Rejected Plan Review Findings

<entries from rejected-findings.md with [Plan Review] headers, or empty if none>

<!-- section-end:plan-review-tally -->

<!-- section:code-review-tally -->
## Code Review Voting Tally (Round 1)

<per-finding YES/NO/EXONERATE counts and reviewer scoreboard from /review>

## Rejected Code Review Findings

<entries from rejected-findings.md with [Code Review] headers, or empty if none>

<!-- section-end:code-review-tally -->

<!-- section:review-findings-full -->
## Review Findings (Full Payload)

<additive per-finding payload composed by scripts/compose-review-findings.sh
from accepted-plan-findings.md, plan-review entries of rejected-findings.md,
and code-review entries of rejected-findings.md. Each rendered finding is a
`### <id> — <category>` block with **Phase**, **Outcome**, **Reviewer**,
**Category**, and a blockquoted verbatim **Prose body** carrying the
file:line citation and suggested-diff prose authored by the reviewer.
When the inline payload exceeds 30 KB, the section body is replaced with
a pointer to docs/review-archive/issue-<N>.jsonl and a small count summary;
the JSONL archive carries one JSON object per finding for offline mining.
The existing tally tables in plan-review-tally and code-review-tally are
unchanged — this section is purely additive.>

<!-- section-end:review-findings-full -->

<!-- section:diagrams -->
## Architecture Diagram

```mermaid
<architecture diagram>
```

## Code Flow Diagram

```mermaid
<code flow diagram>
```

<!-- section-end:diagrams -->

<!-- section:version-bump-reasoning -->
## Version Bump Reasoning

<classification and justification from /bump-version>

<!-- section-end:version-bump-reasoning -->

<!-- section:oos-issues -->
## Accepted OOS (GitHub issues filed)

<one bullet per accepted OOS item: `- <short title> — #<issue-number>`>

## Rejected / Out-of-Scope Observations (not filed)

<one bullet per non-accepted OOS observation>

<!-- section-end:oos-issues -->

<!-- section:execution-issues -->
<details><summary>Execution Issues</summary>

<verbatim contents of $IMPLEMENT_TMPDIR/execution-issues.md — categorized entries: Pre-existing Code Issues, Tool Failures, Permission Prompts, External Reviewer Issues, CI Issues, Warnings, Q/A (Step 2 opportunistic questions + mid-coding ambiguity resolutions)>

</details>

<!-- section-end:execution-issues -->

<!-- section:run-statistics -->
## Run Statistics

| Metric | Value |
|---|---|
| OOS issues filed | <N> |
| Findings accepted | <N> |
| Findings rejected | <N> |
| CI wait duration | <mm:ss> |
| Rebase count | <N> |
| larch plugin version | <auto-injected from `.claude-plugin/plugin.json`, or `unknown`> |
| Claude model | <auto-injected from transcript, or `unknown`> |
| effort level | <auto-injected from `$CLAUDE_CODE_EFFORT_LEVEL` or `$CLAUDE_EFFORT`, or `unknown`> |

<!-- section-end:run-statistics -->

<!-- section:token-report -->
<!-- token-report-begin -->
## Token Report

### Claude

| Step | Skill | Claude Input | Claude Cache Read | Claude Cache Create | Claude Output |
|---|---|---:|---:|---:|---:|

### <Vendor>

| Step | Skill | Input | Output |
|---|---|---:|---:|

<!-- token-report-end -->
<!-- section-end:token-report -->

<!-- section:timing-report -->
<!-- timing-report-begin -->
## Timing Report

**Workflow path**: <HARD | SIMPLE>

## Per-Step Durations
| Skill | Step | Duration |
|---|---|---:|

## Vendor Task Averages
| Vendor | Task kind | Samples | Average | Range |
|---|---|---:|---:|---|

<!-- timing-report-end -->
<!-- section-end:timing-report -->
````

## Section markers — exact slug list

The `SECTION_MARKERS` array — sourced from `scripts/anchor-section-markers.sh` by both `scripts/tracking-issue-write.sh` (truncation algorithm) and `scripts/assemble-anchor.sh` (anchor-body assembly) — must list these exact eleven slugs in this order (truncation algorithm walks sections in this order for pass 1; assembly walk emits `<!-- section:<slug> -->` / `<!-- section-end:<slug> -->` pairs in the same order):

1. `plan-goals-test`
2. `plan-review-tally`
3. `code-review-tally`
4. `review-findings-full`
5. `diagrams`
6. `version-bump-reasoning`
7. `oos-issues`
8. `execution-issues`
9. `run-statistics`
10. `token-report`
11. `timing-report`

Every section is wrapped as `<!-- section:<slug> -->` ... `<!-- section-end:<slug> -->`. Both markers must appear on their own line; no other content may share a marker's line.

## Body-level collapse priority

When the composed anchor-comment body exceeds the 60000-char body-level cap (after per-section 14000-char caps have been applied), sections collapse to a single-line `[section '<slug>' truncated — see execution-issues.md locally]` placeholder in this priority order:

1. `execution-issues` (most ephemeral — reproducible from local `$IMPLEMENT_TMPDIR` tmpdir)
2. `review-findings-full` (large per-finding prose; reproducible from `docs/review-archive/issue-<N>.jsonl` when archive mode kicked in, otherwise from the local `$IMPLEMENT_TMPDIR/anchor-sections/` fragment)
3. `plan-review-tally`
4. `code-review-tally`
5. `oos-issues`
6. `token-report`
7. `run-statistics`
8. `timing-report`
9. `version-bump-reasoning`
10. `diagrams`
11. `plan-goals-test` (highest user-value — goal + test plan must survive)

Collapse stops as soon as the body fits the cap. Section markers themselves are preserved even when interiors collapse; Phase 3 consumers parse by these markers.
