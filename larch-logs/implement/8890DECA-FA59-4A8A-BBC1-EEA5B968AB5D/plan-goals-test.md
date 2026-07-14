## Goal
Implement issue #7316: [IMPLEMENTING] [BUG] Guideline-debt sweep from committed assessment warnings: fence-scanner reuse, RECONCILE_STATUS constants, codex-gate signal typing, issue-close read-back (4 items).

## Implementation Plan
## Summary

Four small, independent guideline deviations were recorded as pre-push architectural-assessment Warnings in committed `/implement` run logs and are still present on latest main. Each is a localized fix (roughly 10 to 40 lines plus tests). They are combined into one issue to keep the backlog small; one PR can fix all four. Every item below carries its own evidence, exact locations, fix, and acceptance so they can be implemented mechanically and independently.

## Item 1: assessment_kind re-derives markdown fence state instead of reusing the shared scanner (G-Md-3)

- **Evidence**: run `E9EF765D-F7AF-4E58-AFC1-FF0F5EEFC809` (issue #6998) pre-push warning: "assessment_kind._parse_entries re-derives Markdown fence state instead of reusing _balanced_fence_line_indices."
- **Current state**: `python/larch/core/assessment_kind.py::_parse_entries` (def at line ~38) hand-rolls fence tracking with a local `fence: tuple[str, int] | None` state machine (lines ~44-67). The canonical scanner, consolidated by #7075, is `python/larch/design/plan_grammar.py::balanced_fence_line_indices` (def at line ~58).
- **Fix**: refactor `_parse_entries` to consume `balanced_fence_line_indices` (precompute the fenced-line index set, then skip heading detection on fenced lines). `assessment_kind` lives in `larch.core` while `plan_grammar` is a domain module, so use a function-level import with a layering pragma, mirroring the accepted pattern at `python/larch/core/redact.py:540` (`# noqa: PLC0415 ... # lint-layering: ok ...`). If the layering lint cannot accept even a function-level import here, the alternative is moving the scanner to a `larch.core` leaf module and re-exporting from `plan_grammar` for existing consumers; prefer the function-level import first.
- **Acceptance**: no local fence tuple state remains in `_parse_entries`; existing `assessment_kind` tests pass; add one test where a `### `-style heading inside a fenced block is not parsed as an entry and one where a longer closing fence is honored (the current stronger length-matched closing behavior must be preserved; `balanced_fence_line_indices` already implements it).

## Item 2: RECONCILE_STATUS machine tokens are raw literals (G-Cfg-1)

- **Evidence**: run `BC924651-1917-490B-8B08-B658D1E0A00D` (issue #7059) pre-push warning: reconcile_manual_merge_main emits RECONCILE_STATUS=ok and RECONCILE_STATUS=failed as hardcoded literals with no Final constants.
- **Current state**: `python/larch/implement/ship_recovery.py::reconcile_manual_merge_main` (def at line ~205) emits `_emit(key="RECONCILE_STATUS", value="failed")` at lines ~266 and ~270 and `_emit(key="RECONCILE_STATUS", value="ok")` at line ~273. `RECONCILE_STATUS` is machine-consumed stdout KV grammar (G-Cfg-1 line 82 in `ARCHITECTURAL_GUIDELINES.md` requires wire literals defined once as Finals).
- **Fix**: define in `python/larch/core/config.py`: `RECONCILE_STATUS_KEY: Final = "RECONCILE_STATUS"`, `RECONCILE_STATUS_OK: Final = "ok"`, `RECONCILE_STATUS_FAILED: Final = "failed"`. Consume them at the three emit sites and in any test oracle that asserts the strings. Keep byte-identical stdout (G-Wire-1); this is a pure constant extraction.
- **Acceptance**: `rg 'RECONCILE_STATUS' python/larch/` shows the key name literal only in `config.py`; stdout grammar unchanged (existing tests keep passing); a test asserts the constants are used by importing them as the oracle.

## Item 3: codex CLI gate signal is stringly typed and its vocabulary is re-listed (G-Cfg-1, G-Py-3)

- **Evidence**: run `9F8D6992-ACD1-4B21-9156-EF36E6D3D6E0` (issue #7072) pre-push warning: the signal literals "model-metadata-not-found" and "newer-codex-required" cross module boundaries, produced in _launch_failure.py and validated against a hardcoded set in _auth.py; CodexGateDetail.signal is a bare str.
- **Current state**: `python/larch/agents/_launch_failure.py` builds the signal inline (`signal = "model-metadata-not-found" if metadata is not None else "newer-codex-required"` at line ~60, `CodexGateDetail(model=..., signal=..., message=...)` at line ~69). `python/larch/agents/_auth.py::_parse_codex_gate_detail` re-lists the set at line ~320: `or signal not in {"model-metadata-not-found", "newer-codex-required"}`.
- **Fix**: declare `CodexGateSignal = Literal["model-metadata-not-found", "newer-codex-required"]`, type `CodexGateDetail.signal: CodexGateSignal`, and derive the single runtime set once via `frozenset(get_args(CodexGateSignal))` next to the type (module Final; or host the two value constants in `config.py` and build the Literal from them if the codebase prefers config ownership, per G-Cfg-1). Point both the producer branch and the `_auth.py` validator at the shared definition. Persisted gate-detail payloads on disk keep the same strings, so no wire migration is needed (G-Wire-1).
- **Acceptance**: exactly one definition site for the vocabulary (grep shows the two literals only at the definition); pyright passes with the Literal; a test asserts `_parse_codex_gate_detail` rejects an unknown signal and accepts both known ones.

## Item 4: gh issue-close and label mutations accept success without read-back (G-Py-8)

- **Evidence**: run `F1BFA841-BF5E-4B97-9424-FEA0531462CC` (issue #7053) pre-push warnings: "Several changed issue-close and label-mutation paths accept successful gh wrapper results without re-reading the mutated issue or label surface, including close_priors_main, _close_combined_away_issue, and _apply_priority_label" and "including _close_combined_away_issue and close_original_issue."
- **Current state**: `python/larch/issue/combine_issues.py::_close_combined_away_issue` (line ~727) and `_close_stale_issue` (line ~732) return the `gh.issue_close(...)` CommandResult directly; `python/larch/issue/audit_runs.py::close_priors_main` (line ~1283) and `python/larch/issue/oos_filer.py::_apply_priority_label` (line ~641) likewise accept wrapper success. G-Py-8 (`ARCHITECTURAL_GUIDELINES.md` line 47) asks for postcondition re-verification after integrity-critical mutations; these closes and labels drive workflow state (an issue that silently stayed open re-enters selection scans).
- **Fix**: after each successful mutation, re-read the surface through the existing typed wrappers (`gh.issue_view_field_read` for `state`, the labels field for `_apply_priority_label`) and handle a postcondition miss loudly: raise or return a failed result with a distinct machine reason (for example `close-postcondition-unverified`), and record a Warning where the caller already has an execution-issues log in scope. Scope strictly to the four named call sites; do not add read-backs elsewhere (G-Fix-1 covers the named class only, and gold-plating other mutations is out of scope).
- **Acceptance**: each named path verifies `state == "closed"` (or the label present) after mutation; stubbed tests cover the success branch and the postcondition-violation branch for all four sites; failure surfaces are loud, not silent.

## Shared acceptance

- One PR may carry all four items; each item's tests are independent so partial landings are reviewable.
- `make py-lint`, `make py-test` pass; no new bare suppressions (G-Py-11: every new `# noqa` / `# type: ignore` / pragma carries an inline reason).
- Each item's diff traces only to that item; no drive-by refactors.

## Related work (do not duplicate)

- #7075 (DONE) consolidated fence-state consumers onto `plan_grammar.balanced_fence_line_indices`; item 1 finishes the one consumer it left behind.
- #7072 (DONE) added the codex gate detection itself; item 3 is only the typing and single-definition follow-up its assessment note recorded.
- The suppression-reason lint and baseline (#6750, DONE) own the separate bare-suppression debt class; that class is intentionally NOT part of this issue.
- #7276 (open, not in flight) will repoint cli self-reentry in the issue/OOS modules; it touches the same files as item 4, so a blocking edge is being recorded (this bug blocks #7276 per bug-first ordering).

## Test plan
(no test plan section in plan-file)
