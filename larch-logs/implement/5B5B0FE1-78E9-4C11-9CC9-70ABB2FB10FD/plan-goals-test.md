## Goal
Insert one missing operator-facing row for make test-read-design-review-budget-invoke in docs/linting.md between the test-parse-plan-commands and test-validate-plan-commands rows.

## Implementation Plan
## Plan

Add one operator-facing row to `docs/linting.md` for the harness `make test-read-design-review-budget-invoke`.

### Context

Issue #2686 was filed during a `/implement` run for #2674 (Lesson 5: /design plan-command syntax validator). The OOS body names two harness targets as needing rows in `docs/linting.md`:

- `make test-parse-plan-commands`
- `make test-validate-plan-commands`

Both rows already exist in `docs/linting.md` under the operator-facing harness table (added by PR #2706, the same PR that introduced the validator). The remaining genuine discoverability gap from PR #2706 is the sibling harness `make test-read-design-review-budget-invoke`: the Makefile recipe and `.PHONY` membership exist, the harness script is non-trivial (it exercises `read-design-review-budget.sh` + `invoke-plan-validator-if-not-quick.sh`), but no row was added to `docs/linting.md`.

Per Step 1c clarification, scope is extended to add this one missing sibling row — same pattern, same PR origin, same "Discoverability gap only" rationale that motivated the OOS.

### Files to modify

#### UPDATED: `docs/linting.md`

Insert one new operator-facing table row for `make test-read-design-review-budget-invoke`, placed between the existing `make test-parse-plan-commands` and `make test-validate-plan-commands` rows so docs/linting.md ordering matches the Makefile ordering (test-parse-plan-commands → test-read-design-review-budget-invoke → test-validate-plan-commands).

Row content (single markdown table line):

```
| `make test-read-design-review-budget-invoke` | Run the offline harness for `skills/design/scripts/read-design-review-budget.sh` and `skills/design/scripts/invoke-plan-validator-if-not-quick.sh`. Covers explicit `review_budget=quick`/`full` parsing, the `sketch_budget=0` quick heuristic, the `python3` → `jq` → grep-literal fallback chain, and the validator dispatch contract (quick tier exits silently; full tier emits `VALIDATE_STATUS=ok` and `STEP_COMPLETED=VALIDATE_PLAN_COMMANDS`). A `make lint` prerequisite via the `test-harnesses-N` shard partition. |
```

The `test-harnesses-N` (generic) annotation matches the surrounding rows for the same-shard peer harnesses (`test-parse-plan-commands`, `test-validate-plan-commands`, `test-emit-plan`, `test-emit-design-plan-preview`). The cost-pipeline cluster lower in the file uses the specific `test-harnesses-12` form; both conventions coexist and the generic form is the convention for `/design`-cluster rows.

### Approach

Single `Edit` tool call inserting the new row immediately after the existing `make test-parse-plan-commands` row. Match the style of adjacent rows: backticked target name in the first column, prose description naming the script(s) under test plus a short summary of coverage, and the trailing `make lint` / shard-partition sentence.

No other files change. The Makefile, `.PHONY` list, and the `test-harnesses-12` shard list already include this target; the only missing artifact is the docs row.

### Edge cases

- **Row ordering**: the existing rows for `test-parse-plan-commands` and `test-validate-plan-commands` are adjacent; place the new row between them to match Makefile recipe order. Markdown tables are unordered structurally — ordering is for human readability only.
- **Backtick code spans**: all backticked identifiers in the row are non-whitespace-bordered (no `MD037` / `MD038` violation).
- **Stale prose warning**: per `.claude/rules/drift-prone-prose-in-docs.md`, do NOT reference Makefile line numbers in the docs prose — the description names scripts by path only.

### Testing strategy

- `markdownlint` (via `make markdownlint` / pre-commit) validates the row.
- `make test-quick-mode-docs-sync` covers structural drift between `docs/linting.md` and other public docs (not a coverage check for harness rows specifically, but a guard against accidental nearby breakage).
- The harness `make test-read-design-review-budget-invoke` itself is not modified.
- After the edit, run `bash scripts/relevant-checks.sh` (or `make lint`) per AGENTS.md to confirm no lint regression.

No new test is added; the harness already exists and is exercised by the shard partition.

## Acceptance

- `docs/linting.md` contains exactly one new operator-facing table row for `make test-read-design-review-budget-invoke`, inserted between the existing rows for `test-parse-plan-commands` and `test-validate-plan-commands`.
- Row description names both `skills/design/scripts/read-design-review-budget.sh` and `skills/design/scripts/invoke-plan-validator-if-not-quick.sh` and references the `test-harnesses-N` shard partition.
- `bash scripts/relevant-checks.sh` (or `make lint`) passes after the edit.
- No other files modified.

diff_lines: 1

## Test plan
(no test plan section in plan-file)
