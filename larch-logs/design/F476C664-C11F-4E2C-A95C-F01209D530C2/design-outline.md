## Proposed Design Outline

### Goals
- Add blast-radius detection: extract changed symbols from fix diffs, grep for consumers outside touched files, widen later-history scans to include consumer files.
- Add class-completeness detection: new `class_complete`, `sibling_sites`, and `introduced_risk` fields in triage/verifier JSONL; ledger ingest accepts new schema strictly and legacy schema gracefully.
- Surface both signals in the report and in follow-up issue body.

### Non-goals
- No runtime code execution or automated filing.
- No changes to chronic-zone routing or analytics view logic.
- No changes to the prefetch/bundle selection strategy.

### Approach sketch
- In `build_bundle_record`: fetch diff first, extract symbols via regex, grep consumers, compute `all_scan_files = touched + consumer_paths`, widen `_later_history` and `_later_history_hash` inputs, append `## Consumers of changed symbols` section to bundle text.
- In `_parse_triage_row` / `_parse_deep_row`: accept old key set (mark `legacy_schema=True`) or new key set; reject any other shape.
- Add `introduced_risk`, `class_complete`, `sibling_sites`, `legacy_schema` fields to `LedgerRecord`, `TriageIngest`, `DeepIngest`.
- In `render_report`: add `## Introduced risk` and `## Instance fixed, class open` sections; append class-open rows to follow-up body.
- Update agent docs and SKILL.md preflight note.

### Surfaces in scope
- `python/larch/issue/analyze_bugs.py`
- `.claude/agents/bug-fix-triage.md`
- `.claude/agents/bug-fix-verifier.md`
- `.claude/skills/analyze-bugs/SKILL.md`
- `python/tests/issue/test_analyze_bugs.py`

### Open questions
- None.
