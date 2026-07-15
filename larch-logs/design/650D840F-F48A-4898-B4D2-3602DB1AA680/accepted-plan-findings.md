### FINDING_1: Unify detector ScanError with engine ScanError
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements
- **Severity**: major
- **Concern**: The detector and corpus-preparation paths may raise a legacy local `ScanError` while the engine catches only `larch.lint.engine.ScanError`. Owner-validation, empty-reason, or preparation failures could therefore be wrapped as `detector raised for ...`, changing exit-2 diagnostics and exception matching.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In self_disarmable_gate_detector.py import ScanError from larch.lint.engine (match markdown_heading_fence_state_detector.py:19). Re-export that same class for compatibility. Raise only engine ScanError from preparation, resolve_optional_metadata, and _emit paths.
  - From Cursor-Innovation: In self_disarmable_gate_detector.py, import and raise larch.lint.engine.ScanError only (mirror unreachable_branch_detector.py:19). In the rewritten wrapper, re-export that same class as ScanError. State explicitly that corpus preparation and detect() must never raise the legacy RuntimeError subclass.
  - From Cursor-Requirements: In self_disarmable_gate_detector.py import ScanError from larch.lint.engine (match markdown_heading_fence_state_detector.py:19). Re-export that same class for compatibility. Raise only engine ScanError from preparation, resolve_optional_metadata, and _emit paths.


### FINDING_2: Preserve legacy syntax-error diagnostics during corpus preparation
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Concern**: Using `SourceFile.python_ast` directly for metadata preparation can raise a raw `SyntaxError`. Since `run_rule` catches only `ScanError`, malformed Python may escape with an unhandled exception or a diagnostic that differs from the legacy `cannot parse source` behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: In corpus preparation, probe syntax with SourceFile.python_syntax_error(); on error raise engine ScanError using the same cannot parse source message shape as legacy _read_parse. Use the parsed tree only after a clean probe.


