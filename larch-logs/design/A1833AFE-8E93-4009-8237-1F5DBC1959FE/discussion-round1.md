# Discussion Round 1 — issue #6873

Source issue is a paste-ready, verbatim adoption spec from a `/larch:learn-from-bugs` run. No scope/constraint/done-criteria ambiguities required operator input; Step 1c questions suppressed. Scope decisions below are derived directly from the issue body (source: issue/codebase), not from an operator Q&A walk.

## Decision 1: Single filing scope (no decomposition)
- **Question**: Does the operator want this split into separate issues, or kept as one filing?
- **Resolution**: Keep as one filing. The issue explicitly states "This issue is one filing with three independent work items." The work items (guidelines, invariant, lints) may land as separate commits/PRs at `/implement` time, but `/design` produces ONE plan for #6873 covering all three. Sprawl heuristic not fired — operator intent is unambiguous, and the three items share the learn-from-bugs-preventions theme.
- **Source**: issue

## Decision 2: Verbatim text, no edits to existing entries
- **Question**: May the plan rephrase or reorder existing guideline/invariant entries?
- **Resolution**: No. Guidelines and invariant blocks are pasted verbatim from the issue. Do not change any existing entry. Append each new entry immediately after its named sibling (`G-Wire-2`, `G-Ext-3`, `G-Md-2`, `G-CLI-2`, `G-IO-2`, `G-Obs-5`; `I-Flush-1`).
- **Source**: issue

## Decision 3: Naming/casing hard constraints
- **Question**: Are the new IDs fixed, or is there numbering latitude?
- **Resolution**: Fixed. Use `G-Wire-3`, `G-Ext-4`, `G-Md-3`, `G-CLI-3` (uppercase `CLI`, matching `G-CLI-1`/`G-CLI-2`), `G-IO-3`, `G-Obs-6` (do NOT reuse unused `G-Obs-4`), and invariant `I-Commit-1` under `## Run-log integrity` after `I-Flush-1`.
- **Source**: issue

## Decision 4: Guideline bullet shape and the `Deviate when:` requirement
- **Question**: What shape must guideline entries take?
- **Resolution**: Match existing family bullet shape exactly: a `- Why:` line, optional `- Guidance:` line, and a `- Deviate when:` line. Every new entry has a real `Deviate when:` clause so `lint guideline-no-exception` passes. Invariant `I-Commit-1` has NO `Deviate when:` clause (invariants have heading + prose + `Evidence of violation:` + `Mechanical backing:`).
- **Source**: issue

## Decision 5: Lint scaffolding contract (template + registration + wiring)
- **Question**: What is the required structure for each new lint?
- **Resolution**: Each of the three lints (`markdown-heading-fence-state`, `self-disarmable-gate`, `unreachable-branch`) mirrors `python/larch/lint/lint_tempfile_dir.py` (module with `SUPPRESSION` constant, `main(argv) -> int`, argparse `prog="cli.py lint <name>"`, baseline regen only if baseline-backed) and its test `python/tests/lint/test_lint_tempfile_dir.py`. Register each via a dispatch row in `python/larch/cli.py`. Add `make lint-<name>` + `make test-lint-<name>`, wire into `py-lint-checks-fast` and the pre-commit hook set per `docs/linting.md`.
- **Source**: issue

## Decision 6: Per-lint baseline policy is implementation-time, not pre-decidable
- **Question**: Hard-ban or baseline for each lint?
- **Resolution**: Decided by running the lint on the current tree during implementation, per the issue's per-lint policy: `markdown-heading-fence-state` ships hard-ban if zero violations else shrinking baseline; `self-disarmable-gate` ships hard-ban if legacy suppression channels are gone else shrinking baseline; `unreachable-branch` ships with a shrinking baseline unconditionally (do not hard-ban on first run). The plan specifies both branches; the implementer picks based on actual scan results.
- **Source**: issue

## Non-goals (explicit operator refusals)
- Do NOT wire the new lints into required CI status checks in this issue (merge gate is local `make lint` + `make py-lint` + pre-commit, consistent with how other in-repo lints are introduced).
- Do NOT merge until `make py-lint` and `make lint` are green.
- Do NOT change any existing guideline or invariant entry.
- Do NOT reuse `G-Obs-4`.

## Must-have requirements (minimum viable outcome)
- Six guideline entries appended to `ARCHITECTURAL_GUIDELINES.md`, each passing its family's shape and `lint guideline-no-exception`.
- `I-Commit-1` appended to `ARCHITECTURAL_INVARIANTS.md`, surfaced by the invariant reader, passing `lint shared-convention-regex`.
- Three lint modules + tests + dispatch registration + Makefile targets + pre-commit wiring, each passing its acceptance check.
- All four acceptance blocks in the issue (work item 1, 2, 3, and notes) satisfiable.
