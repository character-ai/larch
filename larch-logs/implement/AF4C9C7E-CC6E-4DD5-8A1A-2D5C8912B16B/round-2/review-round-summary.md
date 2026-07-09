# Review Round 2

- Mode: `diff`
- 1 accepted, 3 rejected (1 neutral)

## Accepted Findings

### FINDING_1: pyright comma-split identities no longer match the baseline
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing, dyn-dyn-suppression-parser
- **Severity**: major
- **Concern**: `_pyright_report_segments()` now splits comma-separated `# pyright: report…=false` headers into per-clause findings, but `python/suppression-reason-baseline.json` still stores the old combined-header identities. That leaves check mode with stale baseline rows plus new unbaselined findings, so the scanner, baseline, and write/rebuild path need to be realigned.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Regenerate python/suppression-reason-baseline.json with make regen-suppression-reason-baseline after split logic; add a test asserting main() exits 0 against the committed baseline.
  - From codex-specialist-correctness: Regenerate the baseline from the final scanner semantics or change scanner identity to match the committed baseline.
  - From cursor-specialist-edge-cases: Regenerate or migrate python/suppression-reason-baseline.json to per-clause identities and add an integration test that expects exit 0 against the committed baseline.
  - From codex-specialist-edge-cases: Commit an aligned baseline in this PR or teach _records_for_write to split legacy combined pyright keys and reuse their reasons for derived clauses.
  - From cursor-specialist-testing: Regenerate or migrate baseline rows to per-clause identities preserving reasons, then verify check mode exits 0 before merge.
  - From cursor-specialist-testing: Add a repo-root smoke test or harness asserting lint suppression-reason exits 0 against the committed baseline.
  - From codex-specialist-testing: Keep the full pyright header as one scan identity, or regenerate the baseline and affected tests to the same granularity before shipping.
  - From dyn-dyn-suppression-parser: Pick one identity model and align scanner, tests, and baseline: either stop splitting pyright report headers (treat the whole comment as one suppression, extend `PYRIGHT_REPORT_STRICT_RE` to accept comma-chained `report…=false` plus one trailing `# reason`), or keep splitting and regenerate `suppression-reason-baseline.json` so every row’s `text` matches the post-split normalized clause.


