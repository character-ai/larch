## Proposed Design Outline

### Goals
- Fix the CI regression: drop the suppressed/redundant `test-merge-parity` wiring from `test-harnesses-5` (coverage stays via `make py-test`).
- Document the report_tokens scan trust boundary in `SECURITY.md`.
- Note the pending targeted security review of the plot/ship/finalize surfaces in `SECURITY.md` prose.

### Non-goals
- No new tests or correctness-test additions (token-cost, plot schema, scan fixtures, classification/merge/checks parity) — deferred to the upcoming bash→Python migration.
- No bash→Python ports here; no separate follow-up issue filed.
- Do not perform the security review; doc-only.

### Approach sketch
- `Makefile`: remove `test-merge-parity` from the `test-harnesses-5:` line, delete the standalone `test-merge-parity:` target + recipe, and drop its `.PHONY` entry.
- Keep `python/test_merge_bash_parity.py` (still run by `make py-test` / the `python-tests` CI job).
- `SECURITY.md`: add a short "report_tokens scan trust boundary" subsection plus a one-line pending-review note.
- Leave the `requirements-test-harnesses.txt` pytest pin untouched unless it is the sole harness pytest user (verify in plan).

### Surfaces in scope
- `Makefile` (`.PHONY` line, `test-harnesses-5:` line, `test-merge-parity:` target)
- `SECURITY.md`

### Open questions
- None.
