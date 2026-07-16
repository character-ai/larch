## Review Phase Detail

No review rounds completed.

## Architectural invariants

The changed code de-duplicates two issue-listing modules by extracting shared JSON emit/load/number-parse helpers and a frozen open-issue row type into a new `python/larch/issue/open_rows.py`, then reroutes both `combine_issues.py` and `deps_audit.py` plus a new test module through it. It touches no hard gate and its disarm inputs, no consumption of a persisted step result against its producing inputs, no pause snapshot or resume guard, no run-log flush, committed-field embedding, or outcome labeling, no panel slot accounting, no machine-ingested agent verdict, and no post-merge ship-recovery route. Assessed against every workflow-integrity, run-log, panel, agent-contract, and ship-lifecycle rule in the reference, the changed code holds clean with no violation.

## Architectural guidelines

The change centralizes previously duplicated open-issue listing logic into one shared owner: a frozen `OpenIssueRow` dataclass, the field set and limit defined once as module constants (`ISSUE_LIST_FIELDS`, `ISSUE_LIST_LIMIT`) in place of two inline copies, and the JSON emit/load/positive-int helpers moved verbatim out of the two modules that had copied them. Both consumers and a new test module route through the shared owner, and the added tests exercise the normalization, the malformed-row skip policy, duplicate-number preservation, and error propagation, covering more than the single surfacing site.

The read path (`open_issue_rows_read`) goes through the typed `gh.issue_list_read` wrapper and lets its `ShipError` propagate unchanged so each caller formats its own diagnostics, while `parse_open_issue_row` follows a documented, caller-handled skip policy that returns `None` for malformed or non-open rows rather than silently swallowing a real failure. The boundary helpers that accept untrusted parsed JSON narrow to the typed row at the first safe site.

The one observable output change is that the emitted `labels` field is normalized from raw GitHub label objects to a tuple of label-name strings. That change was applied to both producers in the same commit; the only label-content reader in the issue package (`_oos.issue_labels`) already tolerates both a mapping-with-`name` and a bare string, the two modules' own logic never inspects label content, and the existing consumer tests use empty label lists, so no reader's contract is broken. Assessed against the Python coding-practice, configuration-literal, wire-compatibility, and fix-discipline guidance, the changed code reads clean with no deviation.

## /implement run B2951A2B-99EB-4A61-8E98-DBA0C5F2DEBC: shipping

- **Outcome**: shipping
- Force: true
- **Duration**: 01:05:54
- **Cost**: 💰 TOTAL ~$17.81: Claude $17.54, Codex-5.6 $0.00, Codex-mini $0.00, Cursor $0.00, Claude (subprocess) $0.27  |  Tokens: 18673k
- **Issue**: #7480: https://github.com/character-ai/larch/issues/7480
- **Plan review**: N/A
- **Plan coverage**: 0/0 firm headings; band: advisory; disposition: none; todos_left: 0
- **Difficulty**: predicted MODERATE; applied MODERATE
- **Dynamic archetypes**: N/A
- **Code review**: self-review: 0 findings
- **Lines (PR diff)**: N/A
- **OOS filed**: 0
- **Exec issues**: 0
- **Warnings**: 0
- **Run logs**: `larch-logs/implement/B2951A2B-99EB-4A61-8E98-DBA0C5F2DEBC/`
- **Main agent model**: claude-opus-4-8
- **Effort**: max
- **Larch version**: 53.1.16

<!-- larch:run-summary v=1 -->
