# Discussion Round 1 — Issue #6941 (/learn-from-bugs enhancements)

## Decision 1: `--file` filing scope
- **Question**: When `--file`/`-f` is passed, which proposal categories get grouped and filed as new issues?
- **Resolution**: ALL categories — proposed lints, invariants, guideline entries, the NEW regression-test proposals, and concrete still-broken-code items — are grouped into detailed, self-contained issues and filed via `/issue` without per-item approval. The existing Step 5 "apply" gates (append guideline, scaffold lint, create invariants file, update hooks) are NOT run under `--file`; `--file` only files issues. Applying remains the separate, default (no-`--file`) approval-gated path.
- **Source**: user

## Decision 2: Short flag
- **Question**: The issue writes the short flag as `--file/-s`, but `-s` has no mnemonic and risks confusion with `--search`. Which short form should the skill accept?
- **Resolution (superseded post-review)**: Accept `--file` and `-s` as the filing flag. Do NOT bind `-f`; `-f` and all other unrecognized tokens remain verbal GitHub-search text. Originally Step 1c chose `-f`; the Step 3 panel unanimously accepted FINDING_9, whose verbal-search-contract fix is letter-agnostic but whose resolution text used `-s` (the issue's literal notation). Operator reviewed the conflict and chose to accept the finding as-applied (`-s`). The verbal-search contract (recognize only the filing flag; preserve all other tokens as verbal search text) applies regardless of letter.
- **Source**: user (re-confirmed post-review)

## Decision 3: Test-suggestion dedup is prompt-level (hard constraint / scope)
- **Question**: How does the skill decide whether a covering regression test is "missing"? (Affects whether Python changes are needed.)
- **Resolution**: Prompt-level only. During synthesis, for each cluster the main agent reads/greps the TARGET repo's test files for the relevant symbol/behavior and proposes a test only when coverage is genuinely absent and a test would have caught the bug. `CoverageIndex` stays scoped to enforcement surface (guidelines, invariants, lints); tests are NOT added to it (tests verify, they do not prevent). NO Python change required for Enhancement 1.
- **Source**: codebase (CoverageIndex semantics in `python/larch/issue/learn_from_bugs.py`) + minimum-change principle

## Decision 4: Hard constraint — zero open questions in filed issues
- **Question**: How strictly to enforce "no open questions" for `--file` output?
- **Resolution**: Strict. Every filed issue must be 100% self-contained for a lesser model: full root-cause context + backing issue citations; guidelines/invariants spelled out at 100% (full imperative/Why/Deviate-when and full normative statement + invariants-file entry); lint specs exact; test proposals concrete (behavior, symbol, assertions, target test file). All research/decisions resolved BEFORE filing. If any ambiguity remains, fire ONE consolidated `AskUserQuestion` to resolve all of them, then file. No "to be resolved during /design" text in any filed issue.
- **Source**: user (issue #6941)

## Non-goals
- Do NOT change `learn-from-bugs` Python verbs (`prepare`, `coverage-index`, `read-state`, `write-state`) or the digest/coverage-index data model. Both enhancements are skill-prompt-level plus the existing `/issue` batch path.
- Do NOT wire `--file` to apply proposals directly (append/scaffold/create). `--file` files issues only.
- Do NOT add tests to the `CoverageIndex`.
