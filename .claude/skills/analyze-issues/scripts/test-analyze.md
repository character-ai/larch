# test-analyze.sh

Purpose: regression harness for `.claude/skills/analyze-issues/scripts/analyze.py` behavioral output.

Primary callers: `make test-analyze`, and hand-run via `bash .claude/skills/analyze-issues/scripts/test-analyze.sh`.

Invariants: the assertion list mirrors the `test-fixture.json` row-to-code-path coverage matrix. The fixture pins:

- Tracking/umbrella detection (#1).
- `[OOS]` prefix stripping that participates in W1 duplicate-pair detection between #2 and #6 — `strip_prefixes` folds `[OOS] Bug fix: crash in foo` and `Bug fix: crash in foo` to the same key.
- Bug fix categorization (#2 by `bug`/`crash` keywords; #6 by the same; #10 `Docker build error` by the `\berror\b` whole-word match). `Bug fix: 3 (` is pinned in the breakdown to detect rule-order regressions and to ensure `fix` does NOT alias inside `fixture` (#7) or `prefix` (#8) under the word-boundary regex.
- Test coverage categorization (#7 `Test coverage: add fixture` — pinned at `Test coverage: 1 (` so a regression to substring matching that re-routes #7 into Bug fix surfaces).
- Other category fallback (#8 `prefix handling tweak` — pinned at `Other: 1 (` so a regression that alias-matches `fix` inside `prefix` surfaces).
- Documentation/contract drift categorization (#3 via `readme`/`contract` whole-word matches; #9 `Documentation drift in subsystem` via the explicit `documentation` keyword) — pinned at `Documentation/contract drift: 2 (`. The pin also asserts that #10 `Docker build error` does NOT classify as Documentation (the `\bdoc\b` whole-word boundary must reject `Docker` before the rule order reaches Bug fix).
- Hardening/validation/security categorization (#4).
- `[STALLED]` waste detection (#5 → W3 count of 1). #5's body also matches the Refactor/code clarity rule (`cleanup` keyword), so the breakdown shows `Refactor/code clarity: 1` — kept as-is because the W3 stalled count is asserted separately and the category is incidental.
- Reviewer attribution parsing, vote-tally parsing, and the longest-first `codex`/`code` alternation (#7's body carries `- **Reviewer**: codex / generic` and `Vote tally: YES=2 NO=1 EXONERATE=0`; assertions confirm `codex: 1 findings` and the absence of `- code: 1 findings` / `- code / generic:`).
- `load_issues` non-dict and malformed-number handling: temp fixtures pin the stderr warning for non-dict rows, missing/null `number`, non-numeric strings, Unicode digit strings, zero/negative integers, and bools. The warning-only fixtures keep one malformed row at exactly 5% of the input so the strict `>` threshold rule does not pre-empt the warning assertions. A one-row fixture pins ASCII digit-string acceptance and no warning.
- Unified skip threshold behavior: mixed non-dict + malformed-number corruption shares one counter, uses the widened `non-dict or malformed-number elements` abort phrase, fails above 5% without `--lenient`, and renders only valid rows with `--lenient`. An all-malformed fixture fails by default and returns `No issues to analyze.` with `--lenient`.
- No synthetic `#0` collapse: a scoped fixture with malformed-number rows plus valid W4/W5 evidence runs under `--lenient`; the harness extracts only the W4/W5 subsection and asserts that no `#0` token appears there. The assertion is intentionally scoped because issue titles or bodies outside those subsections could legitimately mention `#0`.
- Static analyzer-number guard: the harness greps `analyze.py` for the exact legacy fallback `int(issue.get("number") or 0)`. This is a backstop, not semantic proof; variants such as a different default expression or indirect key lookup would evade the grep and still require review.

If `analyze.py` semantics change for any covered branch, update the fixture and assertions in the same PR.

Makefile wiring: `test-analyze` invokes this harness directly and is included in `test-harnesses-5`.

Edit-in-sync: when adding a new branch in `categorize`, `wasteful_findings`, or `reviewer_effectiveness`, extend `test-fixture.json` with one issue exercising it and add a stable-substring assertion in `test-analyze.sh`.
