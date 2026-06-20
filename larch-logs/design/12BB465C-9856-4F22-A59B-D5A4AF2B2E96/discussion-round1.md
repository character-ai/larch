## Decision 1: #4886 no-issues salvage breadth
- **Question**: How broadly should `research_eval.py::validate_structured_reviewer_output` rescue a `{"no_issues_found": true}` sentinel that appears after narration prose?
- **Resolution**: Conservative. Treat as a clean no-findings pass only when (a) no structured JSONL/TSV findings records were recovered AND (b) exactly one standalone non-blank line is the sentinel (or a bare `NO_ISSUES_FOUND`). If structured records exist, return them as today. Do NOT accept a sentinel that co-occurs with other content beyond pure narration.
- **Source**: user

## Decision 2: #4886 recovered-pass signal
- **Question**: When a clean pass is recovered from a post-narration sentinel, should it be silent or emit a non-failure warning?
- **Resolution**: Emit a low-severity, NON-failure warning/diagnostic so reviewer/prompt preamble-drift stays visible. The slot must still count as a clean effective reviewer (exit 0, empty sidecar, NOT `NOT_SUBSTANTIVE`, NOT logged as an external-reviewer failure). The warning is informational only.
- **Source**: user

## Decision 3: #4888 hardcoded-site scope
- **Question**: Fix only the reviewer-launch hardcoded site (`"review Step 2"`), or also the sibling `--site "2"` at `agents.py:4931`?
- **Resolution**: Fix BOTH in this change. Thread a caller-provided site into `_review_append_launch_failure` (default `review Step 2`); normalize the sibling `_append_implement_launch_failure` site `"2"` -> `"implement Step 2"`. Launch-failure and collector-failure entries for the same panel must agree on the site label.
- **Source**: user

## Decision 4: Codex/Cursor parity (codebase finding)
- **Question**: Does a Codex-only no-issues normalizer need the same broadening as the Cursor one?
- **Resolution**: No. Only `_review_cursor_normalize_no_issues` exists; there is no Codex equivalent. The Codex collect path relies solely on the shared `validate_structured_reviewer_output`, so the `research_eval.py` fix covers Codex. Only the Cursor pre-fix normalizer needs broadening for parity.
- **Source**: codebase

## Decision 5: /research safety (codebase finding)
- **Question**: Does `/research` depend on the strict leading-sentinel behavior such that broadening salvage would regress it?
- **Resolution**: No. Only `collect_results.py:746` and `review_pipeline.py:1318` pass `--structured-reviewer-mode`; `/research`'s own validation path never does. The new salvage only fires when zero structured records are recovered, so all consumers (Codex + Cursor collect, review pipeline) are safe.
- **Source**: codebase

## Decision 6: Hard constraint — preserve the findings-format gate
- **Question**: What existing behavior must not break?
- **Resolution**: Do NOT weaken the strict leading/zero-preamble gate for FINDINGS output. Only broaden the unambiguous no-issues salvage. The reviewer prompt (`rendering.py`) still demands zero preamble; this change rescues only the clean no-issues case, never partial-findings output.
- **Source**: issue + codebase

## Decision 7: Combined scope
- **Question**: One plan/PR for both bugs, or split?
- **Resolution**: One plan. The umbrella issue #4891 deliberately combined #4886 and #4888 because they touch the same file (`python/agents.py`), the same plan-review panel, and the same launcher test harnesses.
- **Source**: issue
