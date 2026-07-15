### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/self_disarmable_gate_detector.py:45-47
- **Concern**: Detector ScanError is not unified with engine ScanError (prior-round fix incomplete). Scenario: Legacy lint_self_disarmable_gate.py defines ScanError(RuntimeError) (lint_self_disarmable_gate.py:45-47). Engine _scan_source only re-raises larch.lint.engine.ScanError; other exceptions become generic detector raised wrappers (engine.py:641-646). With allow_inline_suppression=False, empty-reason and missing-owner failures still raise inside detect(); a separate detector ScanError changes exit-2 stderr text and can break pytest.raises(lint.ScanError) on the engine path.
- **Proposed resolution**: In self_disarmable_gate_detector.py import ScanError from larch.lint.engine (match markdown_heading_fence_state_detector.py:19). Re-export that same class for compatibility. Raise only engine ScanError from preparation, resolve_optional_metadata, and _emit paths. ### 1. [correctness] `python/larch/lint/self_disarmable_gate_detector.py:45-47` — Detector ScanError is not unified with engine ScanError (prior-round fix incomplete) **Concern:** Round 1 flagged ScanError type divergence; the revised plan still lists `ScanError` as a compatibility export but does not require the detector to raise `larch.lint.engine.ScanError`. Legacy code uses `ScanError(RuntimeError)`; ported detectors (`markdown_heading_fence_state_detector.py`) import the engine type. With `allow_inline_suppression=False`, owner-validation failures still originate in `detect()`. Engine `_scan_source` catches only `engine.ScanError`; a distinct detector class gets wrapped as `detector raised for …`, altering deterministic exit-2 diagnostics and risking test mismatches. **Suggested revision:** In `### NEW: python/larch/lint/self_disarmable_gate_detector.py`, add `from larch.lint.engine import ScanError`, re-export that alias, and state that preparation and `_emit` must raise only engine `ScanError`. Drop a separate `RuntimeError` subclass. **Policy:** G-Py-4 (fail closed with deterministic diagnostics).



### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/self_disarmable_gate_detector.py
- **Concern**: The plan still does not pin a single ScanError type for detector, preparation, and engine execution.. Scenario: Round 1 left ScanError typing neutral; the updated plan still only says to re-export ScanError while the legacy rule defines `class ScanError(RuntimeError)` (`lint_self_disarmable_gate.py:45-46`). `engine._scan_source` re-raises only `larch.lint.engine.ScanError` and wraps every other exception as `detector raised for {path}: {exc}` (`engine.py:641-646`). The same split will apply to Piece 1 `prepare_corpus` handling in `run_rule` (`engine.py:1476-1478`). Owner-validation and empty-reason failures would change message shape and may no longer match `pytest.raises(lint.ScanError, match=...)`, and preparation failures may not reliably map to exit code 2.
- **Proposed resolution**: In `self_disarmable_gate_detector.py`, import and raise `larch.lint.engine.ScanError` only (mirror `unreachable_branch_detector.py:19`). In the rewritten wrapper, re-export that same class as `ScanError`. State explicitly that corpus preparation and `detect()` must never raise the legacy RuntimeError subclass.



### FINDING_3:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Focus area**: code-quality
- **Location**: python/larch/lint/lint_self_disarmable_gate.py:main
- **Concern**: [SCOPE-REDUCTION] Remove the runtime Piece 1 API probe. Scenario: The issue is explicitly blocked on Piece 1, so a missing prepare_corpus surface cannot occur in the landed dependency graph; the probe and alternate exit-2 path add dead compatibility behavior.
- **Proposed resolution**: Rely on the declared dependency and construct the engine rule directly; retain the implementation-time dependency check only.



### FINDING_4:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/self_disarmable_gate_detector.py
- **Concern**: Detector ScanError type is still unspecified after round 1. Scenario: The plan preserves ScanError behavior and re-exports ScanError, but never requires the detector/preparation code to raise larch.lint.engine.ScanError. Sibling detectors (unreachable_branch_detector, markdown_heading_fence_state_detector) import engine.ScanError; legacy self-disarmable-gate defines a separate ScanError. If the new detector keeps a local class, engine._scan_source wraps it as detector raised for {path}: {exc}, changing exit-2 stderr text and breaking tests that match legacy empty-reason / gate-owner messages.
- **Proposed resolution**: In NEW self_disarmable_gate_detector.py, import ScanError from larch.lint.engine; raise it from preparation, resolve_optional_metadata, and scan paths. Re-export that same class for compatibility.



### FINDING_5:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/self_disarmable_gate_detector.py
- **Concern**: Corpus metadata prep is told to use SourceFile.python_ast. Scenario: The NEW detector section says resolve_optional_metadata should consume cached SourceFile.python_ast. That property re-raises bare SyntaxError (engine.py:153-154). Legacy _read_parse converts parse failures to ScanError with cannot parse source. Uncaught SyntaxError during prepare_corpus may escape run_rule (which only catches ScanError) or get wrapped with a different diagnostic than legacy/tooling expects.
- **Proposed resolution**: In corpus preparation, probe syntax with SourceFile.python_syntax_error(); on error raise engine ScanError using the same cannot parse source message shape as legacy _read_parse. Use the parsed tree only after a clean probe. ### 1. [correctness] `python/larch/lint/self_disarmable_gate_detector.py` — Detector `ScanError` type is still unspecified Round 1 FINDING_7 flagged that legacy and engine `ScanError` differ. The revised plan says `syntax_policy="raise"` preserves `ScanError` behavior and lists `ScanError` among compatibility exports, but it never pins the detector to `larch.lint.engine.ScanError`. Ported detectors already use the engine type. A local `ScanError` would be wrapped by `_scan_source` as `detector raised for …`, altering exit-code-2 stderr and likely failing suppression-validation tests that match exact legacy strings. **Suggested revision:** In the NEW detector module, `from larch.lint.engine import ScanError` and raise only that type from preparation and scan paths; re-export it from the wrapper unchanged. ### 2. [correctness] `python/larch/lint/self_disarmable_gate_detector.py` — Corpus prep must not use `SourceFile.python_ast` for syntax probing The plan instructs corpus `resolve_optional_metadata` to use `SourceFile.python_ast`. That property raises raw `SyntaxError` on bad input. Legacy `_read_parse` converts the same failure into `ScanError`. `run_rule` catches only `ScanError` at the top level, so preparation that follows the plan literally risks an unhandled `SyntaxError` or a different diagnostic than the legacy rule and equivalence goldens. **Suggested revision:** During corpus preparation, call `python_syntax_error()` first; if present, raise `engine.ScanError` with the legacy-style `cannot parse source` message before reading ASTs for metadata resolution. --- **Prior-round ledger:** Accepted findings 1–3, 5–6 look addressed in the current plan (prepare_corpus seam, rule config, repo-relative paths, corpus-only metadata, positive suppression tests). FINDING_7 remains incomplete on `ScanError` typing (finding 1 above). FINDING_4, FINDING_8, and OOS_1 were not re-raised. No additional in-scope gaps found beyond the two items above.



