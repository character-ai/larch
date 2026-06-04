## Decision 1: Test-coverage / correctness section is OUT OF SCOPE
- **Question**: Issue #3458 §"Test coverage and correctness gaps" asks for many new tests (token-cost integration test against the real `token-cost.sh`, `plot-cost-over-time.py` schema validation + tests, `test_report_tokens_plot.py` subprocess-contract tests, `test_report_tokens_scan.py` malformed-fixture tests, `report_tokens_scan.py` SIMPLE/HARD classification dedup/parity vs `read-workflow-path.sh`, and `test_merge_bash_parity.py` / `test_checks_bash_parity.py` parity additions). Add them now?
- **Resolution**: DROP all of section 2 (test coverage and correctness-test additions) from this design. The team will migrate the underlying bash files (`token-cost.sh`, `merge-pr.sh`, the checks, `read-workflow-path.sh`) to Python shortly and develop new tests at that point; writing tests now — especially against bash that is about to be rewritten — is premature.
- **Source**: user

## Decision 2: In-scope work = Makefile CI fix + SECURITY.md docs only
- **Question**: Which issue sections remain in scope after dropping the test section?
- **Resolution**: Do only (a) the Makefile CI regression fix and (b) the SECURITY.md trust-boundary documentation. Everything under "Test coverage and correctness gaps" is deferred (Decision 1). No separate follow-up issue is filed; the deferred work travels with the planned bash→Python migration.
- **Source**: user

## Decision 3: Makefile fix removes the orphaned target entirely
- **Question**: When removing `test-merge-parity` from `test-harnesses-5:`, how to handle the now-orphaned `test-merge-parity:` target?
- **Resolution**: Remove `test-merge-parity` from the `test-harnesses-5:` shard line AND delete the standalone `test-merge-parity:` target + recipe AND its `.PHONY` entry. Coverage of `python/test_merge_bash_parity.py` is preserved by `make py-test` (the `python-tests` CI job runs `cd python && pytest`). Removing the target entirely keeps `test-harness-shards-coverage` green without adding a carve-out.
- **Source**: user + codebase (coverage-harness interaction)

## Decision 4: Security-review item is documentation-only
- **Question**: The security section asks to (1) add SECURITY.md trust-boundary docs for the report_tokens scan path and (2) "schedule a targeted security review" of `skills/report-tokens/scripts/plot-cost-over-time.py` / `python/ship.py` / `python/finalize.py`. How to handle part (2)?
- **Resolution**: Doc-only. Add the SECURITY.md trust-boundary section for the report_tokens scan path AND mention the pending targeted security review in SECURITY.md prose. Do NOT file a separate tracking issue and do NOT perform the review in this PR.
- **Source**: user
