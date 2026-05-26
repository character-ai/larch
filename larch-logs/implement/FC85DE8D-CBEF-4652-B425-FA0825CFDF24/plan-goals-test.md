## Goal
Update the make test-step-7a inventory row in docs/linting.md to use qualitative-coverage prose instead of a hardcoded case count.

## Implementation Plan
## Plan

Update the `make test-step-7a` inventory row in `docs/linting.md` to drop the hardcoded `Covers N cases:` count and use qualitative-coverage prose that matches sibling inventory rows, addressing the root cause flagged by `.claude/rules/drift-prone-prose-in-docs.md`.

**Files to modify**:

### UPDATED: `docs/linting.md`

Replace the `make test-step-7a` row (currently line 263; identify by the row's leading code-span `` `make test-step-7a` `` so the edit survives line drift) with a rewritten version that:

1. Drops the `Covers 18 cases:` literal prefix.
2. Switches to qualitative-coverage prose matching sibling rows (`test-finalize-sanity-check`, `test-restore-finalize-state`, `test-step-8a-changelog`) — verbs `Exercises`/`Covers` followed by a category list, no numeric totals and no spelled-out cardinalities (no "all four", "both", "the three", etc.).
3. Covers all 21 runtime cases produced by `skills/implement/scripts/test-step-7a.sh` — 19 direct `new_case` call sites, with the sanitizer-rejection-token loop expanding one site into 3 runtime cases for a total of 21 — including the three not currently mentioned in the row (`diagram-failure-sanitizer`, `rebase-unexpected-rc`, `quiet-diagram-skip-contract`).
4. Replaces the factually-incorrect "sanitizer skip-upsert coverage" phrase: the harness `diagram-rejected*` and `diagram-failure-sanitizer` cases assert `tracking-issue-summary.sh` still runs and a placeholder summary comment is still posted. The replacement prose must reflect that sanitizer rejection swaps in a placeholder summary, not that the upsert is skipped.
5. Preserves the trailing sentence about the `test-harnesses-N` shard partition unchanged.

Proposed new row text (single table row on one physical line in the file, three pipe delimiters total — leading, between the two columns, trailing — matching sibling-row shape):

```
| `make test-step-7a` | Run the offline regression harness for `/implement` Step 7a's consolidated body helper `step-7a.sh`. Exercises the green path (diagram + comment + rebase + flush), diagram-skip (small/non-runtime classifier), sanitizer rejection-token variants where the placeholder summary is still posted, diagram-generation-failure and its sanitizer-token variant, summary-upsert failure, flush failure with and without `--no-logs-commit`, no-logs-commit honoring, forked-target rebase argv, ISSUE_NUMBER empty gate, generator crash handling, rebase conflict/failure/unexpected-rc exit propagation, quiet contract replay for rebase-outcome and diagram-skip paths, and argv error. A `make lint` prerequisite via the `test-harnesses-N` shard partition. |
```

**Approach** — single-row prose rewrite via the `Edit` tool with `old_string` anchored on the unique leading code-span. Match sibling-row style: verb-led category enumeration, no numeric totals or spelled-out cardinalities. Group mechanically-similar variants (sanitizer rejection tokens; rebase exit codes; quiet-mode paths) so the row stays readable.

**Edge cases** — preserve backticked literals byte-identically (MD038 risk); single table row with three pipe delimiters total (leading, between-column, trailing) matching adjacent rows; `old_string` must include enough surrounding context to make it unique (leading code-span is already unique).

**Testing strategy** — `bash scripts/relevant-checks.sh` (preferred) or `make lint` per AGENTS.md is the mandatory validation gate after the edit (covers markdown linters, repo-wide policy hooks, secret scanning). `markdownlint` alone is acceptable only as an optional faster diagnostic if the mandatory gate fails. The harness itself is untouched so `make test-step-7a` is not a required gate.

**Failure modes** — (1) `old_string` not unique → re-anchor with longer context; (2) MD038 violation introduced by stray whitespace inside a code span → caught by the mandatory gate; (3) table malformation → visually verify three pipe delimiters before running the gate.

**Out-of-scope (filed separately)** — sibling `skills/implement/scripts/test-step-7a.md` is also stale (lists 19 cases, misses `rebase-unexpected-rc` and `quiet-diagram-skip-contract`, misstates `diagram-failure-sanitizer` upsert behavior). Filed as #2862 (blocked by this issue); two duplicate OOS findings were deduplicated against it.

## Acceptance

The implementation lands when ALL of the following hold:

1. `docs/linting.md` contains a rewritten `make test-step-7a` row that:
   - Does NOT contain the literal substring `Covers 18 cases:` (or any "Covers N cases:" literal where N is a digit sequence).
   - Does NOT contain spelled-out cardinalities for derived coverage counts — specifically not `all four`, `both rebase-outcome and diagram-skip`, `the three`, or similar (the `drift-prone-prose-in-docs.md` rule).
   - Does NOT contain the literal phrase `sanitizer skip-upsert` (factually wrong per the harness; the upsert always runs when ISSUE_NUMBER is set).
   - Mentions category coverage for all 21 runtime cases produced by the harness, including the three previously omitted (`diagram-failure-sanitizer`, `rebase-unexpected-rc`, `quiet-diagram-skip-contract`).
   - Preserves the trailing sentence `A \`make lint\` prerequisite via the \`test-harnesses-N\` shard partition.` unchanged.
   - Is a single physical line in the source file with three `|` pipe delimiters total, matching adjacent inventory rows.
2. `skills/implement/scripts/test-step-7a.sh` is unchanged in this PR (no functional or test edits).
3. `skills/implement/scripts/test-step-7a.md` is unchanged in this PR (sibling-doc drift is tracked separately as #2862).
4. `bash scripts/relevant-checks.sh` (or `make lint`) passes on the changed file with no new errors or warnings introduced.

diff_lines: 2

## Test plan
(no test plan section in plan-file)
