## Proposed Design Outline

### Goals
- Remove the LLM-driven grep/count prose from `SKILL.md` item 8.5 and the `--accepted`/`--rejected` literal threading in item 9.
- Have `write_self_review_tally` compute accepted/rejected counts internally from the two known artifact files.

### Non-goals
- No changes to `voting write-tally`, `audit_runs`, or any downstream consumer of `code-review-tally.json`.
- No changes to the scripted review loop (item 11+) or any other self-review prose beyond items 8.5 and 9.

### Approach sketch
- Add an internal count helper inside `write_self_review_tally` that reads `self-review-accepted.md` and `rejected-findings.md` from `--implement-tmpdir`, counts matching header lines, and treats missing files as 0.
- Remove `--accepted` and `--rejected` from the argparser (breaking change to CLI surface; SKILL.md is the only caller).
- Update SKILL.md: remove item 8.5 entirely; strip `--accepted <ACCEPTED_COUNT> --rejected <REJECTED_COUNT>` from the item 9 fence.
- Update tests: replace explicit `--accepted`/`--rejected` arguments with file-based setup; update `test_self_review_prompt_reconciles_tally_counts_from_artifacts` assertions.

### Surfaces in scope
- `python/review_and_fix.py` (`write_self_review_tally`)
- `python/test_review_and_fix.py` (two artifact tests + one SKILL.md contract test)
- `skills/implement/SKILL.md` (items 8.5 and 9)

### Open questions
- None.
