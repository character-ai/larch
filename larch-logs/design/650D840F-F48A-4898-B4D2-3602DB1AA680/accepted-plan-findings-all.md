### FINDING_1: Corpus-preparation seam is unspecified
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Behavior Parity Auditor
- **Severity**: major
- **Concern**: The plan requires one corpus-wide preparation step before unary detection, but does not name the Piece 1 API, call order, inputs, outputs, or fail-closed dependency check. Without an engine seam, metadata may be resolved per file or through a second discovery pass.
- **Suggested revisions (informational for voters; coder decides):**
  - From Cursor-Arch: In Approach/REWRITTEN, pin the landed Piece 1 symbols (e.g. optional LintRule.prepare plus run_rule call order) and the dependency gate that aborts when that hook is missing
  - From Cursor-Arch: Pin the exact Piece 1 contract (prepare callback, context carrier, and `run_rule` ordering) in Approach and REWRITTEN, plus the dependency check that stops when it is missing.
  - From Cursor-Innovation: Name the Piece 1 contract in Approach (symbol, inputs, outputs) and add wrapper bullets: engine prepares exactly once after loading the discovered collection and before the detect loop; wrapper detect() reads only prepared meta_fields/context; forbid filesystem glob or second git ls-files in the wrapper/detector
  - From Cursor-Pragmatic: Add ### UPDATED python/larch/lint/engine.py with a minimal prepare-once seam (e.g. optional LintRule.prepare_corpus plus invocation between discovery and per-file detect), or pin the exact exported symbol/tests Piece 1 must land before this piece and keep the hard stop when absent
  - From Cursor-Requirements: In Approach and REWRITTEN sections, name the exact Piece 1 contract (symbol, module, and call order), e.g. optional `LintRule.prepare_corpus(sources)` invoked once before the per-file loop, plus a fail-closed import/runtime check for that surface.
  - From Cursor-dyn-Behavior Parity Auditor: In REWRITTEN, spell the production flow: engine discovery yields all sources; Piece 1 prep API runs exactly once on that collection; detect reads captured meta_fields via a factory-built RULE or module state set in main before run_rule. Forbid per-detect filesystem resolve_optional_metadata(design_dir).
  - From Cursor-dyn-Behavior Parity Auditor: Pin the exact Piece 1 deliverable (module path, function name, args: full Sequence[SourceFile], returns: in-memory path map plus MetadataResolution) and the startup import/assert that aborts when missing.
  - From Cursor-dyn-Behavior Parity Auditor: In REWRITTEN, document the production sequence: discover all sources → Piece 1 prep API → capture `meta_fields` → `run_rule` with a `detect` closure that reads the prepared metadata. Do not call filesystem `resolve_optional_metadata(design_dir)` on the production path.
  - From Cursor-dyn-Behavior Parity Auditor: Pin the exact Piece 1 symbol (module, function, argument types, return values) and the import-time probe that stops the port when it is absent.


### FINDING_2: Engine rule configuration and discovery scope are under-specified
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: The rewritten baseline-free `LintRule` does not explicitly pin syntax-error behavior, suppression handling, baseline behavior, suppression token, or the legacy flat design-module scope. Defaults could change exit semantics, suppression behavior, baseline requirements, or scanned files.
- **Suggested revisions (informational for voters; coder decides):**
  - From Cursor-Arch: Mirror lint_unreachable_branch.py: syntax_policy=raise, allow_inline_suppression=False, require_baseline=False, suppression_token=SUPPRESSION, pathspecs=(python/larch/design/*.py,)
  - From Cursor-Arch: Add an explicit `RULE = LintRule(...)` bullet list matching the sibling ports, including `require_baseline=False` and the flat design pathspec.
  - From Cursor-Pragmatic: Pin syntax_policy=raise on RULE alongside allow_inline_suppression=False, matching unreachable-branch and legacy ScanError behavior
  - From Cursor-Pragmatic: Name PATHSPECS=("python/larch/design/*.py",) and a source_filter that rejects test_* basenames, mirroring iter_gate_modules
  - From Cursor-Requirements: In the REWRITTEN section, pin `pathspecs` to `("python/larch/design/*.py", "python/larch/design/**/*.py")`, a design-only `source_filter` that excludes `test_*.py`, `syntax_policy="raise"`, `require_baseline=False`, and `allow_inline_suppression=False`; add matching assertions in the UPDATED test section.


### FINDING_3: Source-path normalization is not pinned
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: major
- **Concern**: The plan does not define whether corpus keys and findings use engine repo-relative `SourceFile.path` values or legacy `larch/design/...` paths. This can cause import-resolution misses and engine validation failures for `Finding.path`.
- **Suggested revisions (informational for voters; coder decides):**
  - From Cursor-Arch: In detect(), set Finding.path=source.path and keep qualified_symbol/message/line from detector hits; do not reuse legacy relative_to(larch_dir.parent) paths
  - From Cursor-Arch: State in REWRITTEN that `detect()` maps hits to engine `Finding` with `path=source.path`.
  - From Cursor-Innovation: Add explicit path-key rule: prepared corpus is keyed by engine repo-relative SourceFile.path; detector import resolution and wrapper adaptation use that grammar; legacy larch/design/ shapes exist only at compatibility re-export boundaries (scan_file/tests)


### FINDING_5: Metadata resolution must be corpus-only
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Concern**: The plan does not define the `resolve_optional_metadata` input contract. Retaining its disk-backed `Path` behavior could reintroduce filesystem reads and independent discovery instead of resolving imports and re-exports from the prepared `SourceFile` corpus.
- **Suggested revisions (informational for voters; coder decides):**
  - From Cursor-Requirements: In the NEW detector section, specify `resolve_optional_metadata` (and preparation) take a `Mapping[str, SourceFile]` keyed by repo-relative paths, resolve imports/re-exports from cached ASTs only, and forbid filesystem reads outside that map; update the UPDATED tests section to build the map from `SourceFile` fixtures instead of `Path` trees.


### FINDING_6: Positive owner-qualified suppression lacks regression coverage
- **Reviewer(s)**: Codex-Requirements
- **Severity**: minor
- **Concern**: The planned tests do not explicitly verify that a valid non-empty suppression reason naming the gate owner suppresses the finding on both detector and engine paths.
- **Suggested revisions (informational for voters; coder decides):**
  - From Codex-Requirements: Add a detector and engine-path test that a non-empty suppression reason naming the gate owner produces no finding and exit 0.


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


