# test-analyze.sh

Purpose: regression harness for `.claude/skills/analyze-issues/scripts/analyze.py` behavioral output.

Primary callers: `make test-analyze`, and hand-run via `bash .claude/skills/analyze-issues/scripts/test-analyze.sh`.

Invariants: the assertion list mirrors the `test-fixture.json` row-to-code-path coverage matrix. The fixture pins:

- Tracking/umbrella detection (#1).
- `[OOS]` prefix stripping that participates in W1 duplicate-pair detection between #2 and #6 — `strip_prefixes` folds `[OOS] Bug fix: crash in foo` and `Bug fix: crash in foo` to the same key.
- Bug fix categorization (#2 by `bug`/`crash` keywords; #6 by the same; #7 also classifies as Bug fix because `default_category` walks `CATEGORY_RULES` in order and `fix` matches as a substring of `fixture` before the Test coverage rule is reached — pinning `Bug fix: 3 (` in the breakdown ensures regressions in either rule order or substring matching surface).
- Documentation/contract drift categorization (#3).
- Hardening/validation/security categorization (#4).
- `[STALLED]` waste detection (#5 → W3 count of 1). #5's body also matches the Refactor/code clarity rule (`cleanup` keyword), so the breakdown shows `Refactor/code clarity: 1` — kept as-is because the W3 stalled count is asserted separately and the category is incidental.
- Reviewer attribution parsing, vote-tally parsing, and the longest-first `codex`/`code` alternation (#7's body carries `- **Reviewer**: codex / generic` and `Vote tally: YES=2 NO=1 EXONERATE=0`; assertions confirm `codex: 1 findings` and the absence of `- code: 1 findings` / `- code / generic:`).

If `analyze.py` semantics change for any covered branch, update the fixture and assertions in the same PR.

Makefile wiring: `test-analyze` invokes this harness directly and is included in `test-harnesses-5`.

Edit-in-sync: when adding a new branch in `categorize`, `wasteful_findings`, or `reviewer_effectiveness`, extend `test-fixture.json` with one issue exercising it and add a stable-substring assertion in `test-analyze.sh`.
