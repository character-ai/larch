# Anchor Comment Template

**Consumer**: `/implement` Phase 3 (umbrella #348) — the canonical anchor-comment markdown template written via `scripts/tracking-issue-write.sh upsert-anchor` and parsed from issue comments by consumers. Active consumers wired in Phase 3: Step 0.5 (resolve tracking issue, hydrate fragments, plant seed anchor on adoption OR Branch 4 first-remote-write: create-issue + seed anchor + sentinel), Anchor-section accumulation at Steps 1 / 2 / 5 / 7a / 8 / 9a.1 / 11, Step 2 progressive `execution-issues` upsert for Q/A entries, Step 9a.1 OOS pipeline (anchor section population), Step 11 post-execution `execution-issues` refresh.

**Contract**: single normative source for (1) the eleven canonical section markers, (2) the first-line HTML anchor marker literal, (3) the Voting Tally extraction guidance, (4) the Step 9a.1 OOS pipeline procedure in anchor-comment context, (5) the Quick-mode anchor guidance, and (6) the three load-bearing string literals pinned by `scripts/test-implement-structure.sh` assertion (9a) (`Accepted OOS (GitHub issues filed)`, `| OOS issues filed |`, `<details><summary>Execution Issues</summary>`). Section headers and HTML comment markers must NOT drift — the executable source of truth for `SECTION_MARKERS` is `scripts/anchor-section-markers.sh` (sourced by both `scripts/tracking-issue-write.sh` for truncation ordering and `scripts/assemble-anchor.sh` for assembly ordering); `scripts/tracking-issue-write.sh`'s inline `COLLAPSE_PRIORITY` array is a permutation of the same slug set (body-cap collapse priority). The template below must list the same eleven slugs. `test-implement-structure.sh` assertion (9a) pins these literals; assertion (9b) pins a ≥3 reference floor for `anchor-comment-template.md` in SKILL.md; assertions (9d)-(9h) pin Step 9a.1 procedure text including flags, paths, cap integration, Rule A/B cascade literals, and the grouping-worksheet contract.

**When to load**: before composing any anchor-section fragment or invoking `tracking-issue-write.sh upsert-anchor`. Do NOT load outside Step 0.5 (including Branch 4 first-remote-write), the Anchor-section accumulation procedure, Step 2 (progressive `execution-issues` upsert for Q/A), Step 9a.1, and Step 11's post-execution anchor refresh.

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

<!-- section-end:run-statistics -->

<!-- section:token-report -->
<!-- token-report-begin -->
## Token Report

### Claude

| Step | Skill | Claude Input | Claude Output |
|---|---|---:|---:|

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

## Voting Tally extraction guidance

The `plan-review-tally` and `code-review-tally` sections contain per-finding vote counts and per-reviewer competition scoreboards. For Phase 3+:

- The tally table format matches the scoreboard format in `skills/shared/voting-protocol.md`.
- Future consumers extracting tallies from an existing anchor comment should use the section-open / section-end markers as the extraction boundary (not prose heuristics).
- If a tally section is present but its interior is collapsed to the `[section '...' truncated — see execution-issues.md locally]` placeholder, treat the tally as unavailable and degrade gracefully — do NOT fabricate counts.

## Step 9a.1 OOS pipeline procedure (canonical, anchor-comment context)

The canonical Step 9a.1 procedure lives here (Phase 3+). The anchor comment is the single source of truth for report content — the PR body is a slim projection (see `skills/implement/references/pr-body-template.md` for the slim-PR scaffold).

Step 9a.1's sequence in anchor context:

1. Read `$IMPLEMENT_TMPDIR/oos-accepted-*.md` artifact files (one per phase: `oos-accepted-design.md`, `oos-accepted-review.md`, `oos-accepted-main-agent.md`). **A missing file MUST be treated as empty** (no entries from that phase) — none of the three artifacts is mandatory: `/design` quick mode skips review and never writes `oos-accepted-design.md`; `/review` may produce zero accepted OOS and skip writing `oos-accepted-review.md`; the main-agent dual-write only fires when something was appended. Treat missing-file and empty-file identically; do NOT error on missing.
   - After reads normalize in memory, before the step-2 empty-batch test and before step 3.3 dedup, defensively filter out any `### OOS_N:` block whose content contains the canonical token `focus-area\s*=\s*security` case-insensitively, with optional whitespace around `=`. This is defense-in-depth: `skills/design/references/plan-review.md` and `skills/review/references/voting.md` diff mode are the canonical public-boundary exclusion sites; this is the last-line backstop before public `/issue` filing. Route filtered security findings through SECURITY.md's private disclosure flow instead. After this security filter, evaluate emptiness on the post-filter entry list.
2. If all artifacts are missing-or-empty, or if the post-filter entry list is logically empty after security re-exclusion, emit `Accepted OOS (GitHub issues filed)` as an empty bulleted list. The post-filter empty path follows the same early-exit/idempotency behavior as the missing-or-byte-empty path.
3. Idempotency guard: if `$IMPLEMENT_TMPDIR/oos-issues-created.md` sentinel exists, recover prior URLs from it and skip the `/issue` invocation (deterministic byte-exact guard). Do NOT double-file.
3.3. Build the working batch: concatenate the three source artifacts (in fixed phase order — design, review, main-agent) into a single in-memory list of `### OOS_N:` blocks, then apply cross-phase dedup so byte-equivalent or trivially-equivalent titles from different artifacts collapse to one entry. This produces the merged batch consumed by step 3.4.
3.4. Combine pass (orchestrator-side, automatic — NOT an interactive `/combine-issues` invocation): write the final batch to `$IMPLEMENT_TMPDIR/oos-combined.md`. Combining proceeds without user confirmation because every input entry is already an accepted OOS staged inside `$IMPLEMENT_TMPDIR`; the orchestrator owns the call. The cascade is `Rule A -> Rule B -> existing criteria 1-4 (independence-respect carve-out intact) -> criterion 5 (medium-bug, hard combine) -> criterion 6 (moderate-doc, hard combine)`; each layer further collapses survivors from the previous layer. Criteria 1-4 mirror `/combine-issues`; Rules A and B and criteria 5-6 are Step 9a.1-only hard-combine policy that intentionally diverges from `/combine-issues`'s independence-respect convention because Step 9a.1 is unilateral and runs without user confirmation.

**Rule A — same logical concern**: Group accepted-OOS entries by LLM-judged logical concern — a thematic area like `OOS pipeline`, `anchor-comment lifecycle`, `/issue dedup`, `Slack announce`. Concern is a thematic judgment, not a strict file/path match (path-based grouping is criterion 1, which still cascades later). **Rule A is HARD COMBINE: it OVERRIDES the existing "do NOT combine genuinely independent entries" carve-out**, in the same way criteria 5 and 6 already override it. Independence is intentionally overridden here to drive aggressive issue-count reduction. Every concern group with 2+ entries collapses to ONE combined entry. Title summarizes the shared logical concern. Description preserves every source ENTRY's actionable content verbatim — every concrete task, file ref, line range, reproduction context, and suggested-fix option. **However, lines that begin (column 0) with the literal sequence `###` followed by one space, `- **Description**:`, `- **Reviewer**:`, `- **Vote tally**:`, or `- **Phase**:` from a SOURCE entry MUST be indented (prefix with one space) or fenced** so they do not re-trigger `skills/issue/scripts/parse-input.sh` heading detection. NEVER discard actionable content while merging; structural escaping is the only permitted modification.

Before materializing `oos-combined.md`, the orchestrator MUST write a `$IMPLEMENT_TMPDIR/oos-grouping-worksheet.md` artifact for every non-empty, non-sentinel-recovery merged batch (`ITEMS_TOTAL >= 1`). The worksheet's row identity is the post-3.3 merged-batch ordinal (`INPUT_<i>`, 1-based after cross-phase dedup), NOT raw source `OOS_N` IDs from `oos-accepted-design.md` / `oos-accepted-review.md` / `oos-accepted-main-agent.md` (those collide because each phase artifact starts at `OOS_1`). When provenance is useful, also include `source=<phase> original=OOS_<j>` after the canonical `INPUT_<i>` token. Add a one-line banner at the top of the worksheet stating that worksheet indices and group IDs describe the pre-cap batch only; after `oos-issue-cap.sh` rewrites `oos-combined.md` (renumbered + possible synthetic aggregate entry), do NOT align worksheet `INPUT_<i>` to post-cap `oos-combined.md` `OOS_N` headings or to `oos-intra-batch-deps.tsv` row indices without replaying the cap transform.

Worksheet format: one entry per `INPUT_<i>` using a key-per-line block to avoid `|`-as-delimiter collision with concern labels, justifications, or paths:

```text
### INPUT_<i>
- concern: <label>
- group: <group-id>
- justification: <one-line rationale, drawn ONLY from already-sanitized source text>
- sources: <phase>:OOS_<j> (optional provenance)
```

Every input INPUT_<i> MUST appear exactly once. Group IDs are short stable tokens (e.g., `g-oos-pipeline`, `g-singleton-1`). Singletons (group of 1) MUST receive a group ID of the form `g-singleton-<i>`. Only group IDs with 2+ members participate in Rule A's hard combine. The `justification` field MUST be derived only from already-sanitized source text (post-secrets / internal-URL / PII redaction). Paraphrase or summary text MUST be sanitized at compose-time using the same rules applied to `oos-combined.md` body fields. Worksheet is human/review-only: `oos-issue-cap.sh`, `oos-file-conflict-deps.sh`, and `/issue --input-file` continue to consume `oos-combined.md` exclusively. The worksheet is NOT passed to any of these. **`oos-grouping-worksheet.md` is a tmpdir-only audit artifact — it stays under `$IMPLEMENT_TMPDIR` and is NOT one of the `anchor-sections/*.md` data fragments**.

**Rule B — leaked SIMPLE entries**: **Let S be the set of entries that remained as singleton `### OOS_N:` blocks after Rule A and are classified SIMPLE.** Rule B applies ONLY to entries in S; it does NOT re-classify, re-merge, or otherwise mutate Rule A combined rows. An entry is **SIMPLE** iff its Description implies a doc-drift change OR a small-bug code change of `< ~30 LOC`. The `~` is intentional — the LOC estimate is a natural-language judgment matching the threshold convention already used by criteria 5 and 6 and by the SKILL.md OOS triage policy. Rule B backstops leakage from `/design` / `/review` voting acceptance and from Step 9a.1 manifest harvest. Security tagging and public-boundary exclusion are now addressed at `/design` plan-review.md, `/review` voting.md diff mode, and the Step 9a.1 defensive re-exclusion above; rules-1-2 fold-inline triage at the /design and /review voting writers remains open. Propagating that triage upstream remains the durable fix; Rule B is the filing-time backstop. **Rule B is HARD COMBINE: same independence-override semantics as Rule A.** If `|S| >= 2`, replace S with one combined entry; entries outside S (including all Rule A combined rows and all non-SIMPLE singletons) are unchanged. If `|S| < 2` (zero or one SIMPLE singleton), Rule B is a no-op — a lone SIMPLE singleton passes through unchanged to criteria 1-6.

For criteria 1-4, when the total non-malformed OOS entry count across the merged batch survivors is greater than 1, analyze and group using: same code area (multiple entries touching the same files / module), similar change pattern (analogous edits to different files), overlapping scope (one entry is a subset of another), or sequential dependency (must land in order and is small enough to ship as one unit). For these four similarity criteria, do NOT combine entries that are genuinely independent or that benefit from separate review. Criterion 5 then combines all medium-bug-class entries (Description implies a code change >= ~30 LOC) into ONE combined entry; minimum count 2. Criterion 6 then combines all moderate-doc-class entries (Description implies a doc change ~30-100 lines) into ONE combined entry; minimum count 2. Criteria 5 and 6 OVERRIDE the independence carve-out: all entries in each of those size classes combine into a single issue even when they are independent — the policy goal of one filed-OOS issue per medium-bug class and per moderate-doc class is the explicit override.

For each group with 2+ source entries, compose ONE merged entry whose title summarizes the shared theme and whose Description preserves every concrete task, file reference, line range, reproduction context, and suggested-fix option from each source; NEVER discard actionable content while merging. Set `Reviewer` to `Combined: <constituent reviewer attributions>`, `Vote tally` to `N/A — combined from <count> entries`, and `Phase` to the lexically-earliest constituent phase (`design < implement < review`); the Phase field is informational only. Apply the same compose-time sanitization as the source artifacts (secrets → `<REDACTED-TOKEN>`, internal URLs → `<INTERNAL-URL>`, PII → `<REDACTED-PII>`). Emit the file in the `### OOS_N: <title>` / `- **Description**:` / `- **Reviewer**:` / `- **Vote tally**:` / `- **Phase**:` schema accepted by `skills/issue/scripts/parse-input.sh`, renumbering `OOS_N` sequentially from 1. When `ITEMS_TOTAL == 1` or no 2+ entry groupings are identified, `$IMPLEMENT_TMPDIR/oos-combined.md` is byte-equivalent to the merged input, modulo sequential `OOS_N` renumbering when needed. In the sentinel-recovery branch above, do NOT run combining because the original session already chose and filed the batch. This skip applies to **Rules A and B as well as criteria 1-6**, for the same reason — the original session already chose the batch and re-running combine would corrupt the cross-session record. The **sentinel branch does NOT write `oos-grouping-worksheet.md`** — the worksheet is a per-session artifact tied to the same combine that produces `oos-combined.md`, and rewriting it on recovery would falsely imply a second grouping decision was made. Downstream steps consume `$IMPLEMENT_TMPDIR/oos-combined.md` as the merged-batch path after step 3.4b's cap pre-pass: the file-conflict pre-pass serializes capped/combined entries that share files, `/issue` Phase 2 discovers semantic dependencies among the capped/combined items, and `--blocked-by-issue $ISSUE_NUMBER` forwarding remains unchanged for every combined OOS issue.
3.4b. Per-run issue cap pre-pass (orchestrator-side, automatic): run `bash ${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/oos-issue-cap.sh --input-file "$IMPLEMENT_TMPDIR/oos-combined.md"` immediately before step 3.5. The helper rewrites `oos-combined.md` in place when `ITEMS_TOTAL > OOS_ISSUES_PER_RUN_CAP` (default `5`): it keeps the first `(cap-1)` entries byte-faithfully, replaces the surplus tail with one synthetic `### OOS_<cap>:` aggregate entry whose Description enumerates the rolled-up titles plus bounded UTF-8-safe excerpts (default 200 characters per entry via `OOS_ISSUE_CAP_EXCERPT_MAX`), each followed by a per-bullet `[Files: <paths>]` list extracted from the full rolled-up body so step 3.5's file-conflict pre-pass can still emit serialization edges, and renumbers headings to `OOS_1..OOS_<cap>`. The cap operates on the merged batch produced by step 3.4 and is the LAST mutation of `oos-combined.md` before indices are frozen for step 3.5's file-conflict pre-pass and step 4's `/issue --input-file` invocation. Pass-through is byte-equivalent when `ITEMS_TOTAL <= cap` (covers `<count`, `==count`, and empty input). On non-zero exit (parser failure, missing input, parser-heading parity mismatch, non-OOS-shaped input, or invalid `OOS_ISSUES_PER_RUN_CAP` / `OOS_ISSUE_CAP_EXCERPT_MAX`), the helper is **fail-closed**: print the warning `**⚠ /implement: oos-issue-cap helper failed (exit <N>) — OOS batch NOT filed; review accepted-OOS Descriptions and re-run with corrected env, or have the items filed manually**`, append a `Tool Failures` entry to `$IMPLEMENT_TMPDIR/execution-issues.md`, do NOT write the `$IMPLEMENT_TMPDIR/oos-issues-created.md` sentinel, SKIP step 3.5 and step 4 for the OOS batch, replace the `Accepted OOS (GitHub issues filed)` section's placeholder with `_OOS issue filing skipped this run: cap helper failed (exit <N>); see Tool Failures section for details._`, set the `| OOS issues filed |` row in `run-statistics` to `0`, and print the breadcrumb `❌ 9a.1: oos-issue-cap helper failed — issue filing skipped`. The fail-closed posture differs intentionally from step 3.5's degraded-continue behavior: file-conflict edges are best-effort hints whereas the per-run cap is a hard policy guard against issue-spam. In the sentinel-recovery branch (step 3 above), do NOT run the cap helper — the batch was already chosen and filed in a prior session, so re-capping would corrupt the cross-session record.
3.5. File-conflict pre-pass: run `bash ${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/oos-file-conflict-deps.sh --input-file "$IMPLEMENT_TMPDIR/oos-combined.md" --output "$IMPLEMENT_TMPDIR/oos-intra-batch-deps.tsv"` against the post-cap `oos-combined.md` immediately before the `/issue` invocation in step 4. The helper delegates item parsing to `skills/issue/scripts/parse-input.sh` (so its 1-based indices are byte-identical to `/issue --input-file`'s) and emits all-pairs edges for same-file conflict clusters. Inside the helper: Tier 1 degrades any cluster that would emit more than `OOS_FILE_CONFLICT_CLUSTER_CAP` (default 200) all-pairs rows to a chain `i → i+1` (lower robustness under SCC pruning, but bounded row count); Tier 2 exits non-zero when the post-degradation total exceeds `OOS_FILE_CONFLICT_GLOBAL_CAP` (default 500), leaving no observable TSV at the stable output path. The orchestrator captures the helper's exit code: on non-zero exit (Tier 2, invalid env cap, parser failure, missing regex lib, or any other failure), print the user-facing warning `**⚠ /implement: oos-file-conflict pre-pass failed (exit <N>) — proceeding without caller-supplied serialization edges; review accepted-OOS Descriptions before greenlighting parallel workers**`, append a `Tool Failures` entry to `$IMPLEMENT_TMPDIR/execution-issues.md` (visible in the anchor comment's `execution-issues` section), and continue without `--intra-batch-deps-file`. On exit 0 with non-empty TSV (file size > 0), the next step's invocation includes `--intra-batch-deps-file "$IMPLEMENT_TMPDIR/oos-intra-batch-deps.tsv"`. On exit 0 with empty TSV, omit the flag.
4. Invoke `/issue` in batch mode with the combined accepted OOS entries. The invocation MUST forward `--input-file "$IMPLEMENT_TMPDIR/oos-combined.md"` and `--title-prefix "[OOS]"` so every auto-filed OOS issue receives the `[OOS]` title prefix without manual retitling. The invocation MUST NOT pass the `/issue` label flag; the `[OOS]` title prefix is sufficient, and out-of-scope-style labels typically do not exist in consumer repos and produce per-invocation stderr warnings from `/issue`'s create-one.sh label-existence probe. When `$ISSUE_NUMBER` is non-empty AND `deferred=false` AND `repo_unavailable=false`, the invocation MUST also forward `--blocked-by-issue $ISSUE_NUMBER` so every newly created OOS issue acquires a native GitHub `blocked_by` edge to the current `/implement` tracking issue. In any of the three degraded modes (`deferred=true`, `repo_unavailable=true`, `$ISSUE_NUMBER` unset), do NOT forward `--blocked-by-issue` — there is no resolved blocker target, and OOS issues are filed without the policy edge. Forward `--intra-batch-deps-file <path>` only when step 3.5's helper produced a non-empty TSV; the file carries caller-supplied high-confidence file-conflict edges that are merged (unioned) with `/issue` Phase-2 LLM dep-analysis output, then pass through validation, DUPLICATE override, and SCC cycle resolution. Caller edges and LLM edges have no precedence in cycle resolution. Inter-OOS dependencies among the batch items are the union of (a) caller-supplied file-conflict edges from step 3.5 and (b) `/issue`'s existing Phase 1/2 analysis, then applied as native `blocked_by` POSTs by `add-blocked-by.sh`. `/issue`'s `create-one.sh` already idempotently double-prefix-normalizes case-insensitively, so entries whose titles already start with `[OOS]` are safe. Parse stdout for `ISSUES_CREATED`, `ISSUES_FAILED`, `ISSUES_DEDUPLICATED`, per-issue `ISSUE_<i>_NUMBER=`, `ISSUE_<i>_URL=`.
5. Write the sentinel `$IMPLEMENT_TMPDIR/oos-issues-created.md` with the per-issue URLs for rerun idempotency.
6. Replace the `oos-issues` section's `Accepted OOS (GitHub issues filed)` placeholder with one bullet per created issue (`- <short title> — #<number>`) plus any `— filed as #<N>` annotations linking prior rejected findings to newly-filed follow-ups.
7. Update the `run-statistics` section's `| OOS issues filed |` row with the count of newly-created issues (recovered-from-sentinel count is NOT included — sentinel recovery means "previously filed this session, not filed again this step").

## Quick-mode anchor guidance

Quick mode (`/implement --quick`) skips `/design` and `/review`, so the `plan-review-tally` and `code-review-tally` sections have no standard content. Quick-mode consumers should:

- Leave the `plan-review-tally` and `code-review-tally` sections present (with section markers preserved) but populate the interior with `(plan review skipped — quick mode)` / `(single-reviewer loop — no voting panel)` as appropriate.
- Populate `diagrams` with only the Architecture Diagram (Code Flow Diagram is skipped in quick mode per SKILL.md Step 7a).
- All other sections are populated normally.

This keeps the anchor-comment shape stable across mode-selection so a Phase 3+ consumer can parse by section marker regardless of mode.

## Compose-time sanitization rule

Every fragment composed into the anchor-comment body must apply prompt-level sanitization at compose time, parallel to the rule stated in `skills/implement/SKILL.md` "Execution Issues Tracking" section:

- Redact session tmpdir paths → `<TMPDIR>`.
- Redact secrets / API keys / OAuth / JWT / passwords / certificates → `<REDACTED-TOKEN>`.
- Internal hostnames / URLs / private IPs → `<INTERNAL-URL>`.
- PII (emails, names, account IDs linked to a real user) → `<REDACTED-PII>`.

This is a defense-in-depth layer above `scripts/redact-tmpdir-paths.sh` and `scripts/redact-secrets.sh`'s outbound scrubbers: the scrubbers catch session tmpdir paths and covered token families mechanically, but internal URLs and PII are out of their coverage and MUST be sanitized at compose time. `tracking-issue-write.sh`'s structural choke point (compose → redact → truncate) ensures no bypass path exists, but it does NOT invent redactions the helpers do not cover — compose-time prompt-level sanitization is the first and primary defense for those classes.

## Edit-in-sync pointers

| File | Relationship |
|---|---|
| `scripts/anchor-section-markers.sh` | Single source of truth for the `SECTION_MARKERS` array (sourced by `tracking-issue-write.sh` and `assemble-anchor.sh`); slug set must match the list here. |
| `scripts/tracking-issue-write.sh` | Inline `COLLAPSE_PRIORITY` array must be a permutation of the slug list here (same set, body-cap collapse priority order). Enforced by a test-harness invariant in `scripts/test-tracking-issue-write.sh`. |
| `${CLAUDE_PLUGIN_ROOT}/scripts/compose-review-findings.sh` | Composes the additive `review-findings-full` fragment from `accepted-plan-findings.md`, plan-review rejected entries, and code-review rejected entries; falls back to `docs/review-archive/issue-<N>.jsonl` archive at the 30 KB inline threshold. Sibling contract: `scripts/compose-review-findings.md`. Invoked by `skills/implement/SKILL.md` Step 5 after `/review` returns or the quick-mode review loop completes. |
| `scripts/assemble-anchor.sh` | Consumes `SECTION_MARKERS` via the shared helper; emits marker pairs and the first-line HTML marker documented here. |
| `scripts/read-plugin-version.sh` | Supplies the best-effort larch plugin version row auto-injected into `run-statistics`. |
| `scripts/timing-report.sh` | Writes the sentinel-bracketed `timing-report` fragment consumed by the anchor section. |
| `scripts/tracking-issue-read.sh` | Anchor-marker filter uses the same strict `<!-- larch:implement-anchor v1` prefix. |
| `skills/implement/references/pr-body-template.md` | Sibling slim-projection template for the PR body (Summary + Diagrams + Test plan + `Closes #<N>` + footer only); Phase 3+ the anchor comment is canonical for rich content. |
| `scripts/test-implement-structure.sh` | Phase 3 test-harness assertion (9a) pins the three load-bearing literals here (`Accepted OOS (GitHub issues filed)`, `\| OOS issues filed \|`, `<details><summary>Execution Issues</summary>`); assertion (9b) pins a ≥3 reference floor for `anchor-comment-template.md` in SKILL.md; assertion (9d) pins the Step 9a.1 procedure flag contract (must document `--title-prefix "[OOS]"`; must not pass any `--label` flag; must document `--blocked-by-issue $ISSUE_NUMBER` forwarding only when `$ISSUE_NUMBER` is set, `deferred=false`, and `repo_unavailable=false`, with the explicit degraded-mode skip rule); assertion (9e) pins `--intra-batch-deps-file` forwarding in this procedure; assertion (9f) pins the literal `oos-combined.md` (combine-pass output path consumed by `oos-file-conflict-deps.sh` and `/issue --input-file`) in this procedure; assertion (9g) pins `oos-issue-cap.sh`, `OOS_ISSUES_PER_RUN_CAP`, the fail-closed warning string, and the step 3.5 / step 4 skip wording for the per-run cap pre-pass; assertion (9h) pins Rule A/B literals, cascade order, override-independence, worksheet path, sentinel-skip clauses, and worksheet-contract sub-pins. |
