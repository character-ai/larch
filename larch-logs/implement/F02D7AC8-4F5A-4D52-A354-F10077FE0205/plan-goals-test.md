## Goal
Implement issue #6991: [IMPLEMENTING] bug-treadmill [FEATURE] Migrate self-disarmable-gate.

## Implementation Plan
## Plan

## Approach

- Block this piece on Piece 1 landing `LintRule.prepare_corpus: Callable[[Sequence[SourceFile]], None] | None` in `python/larch/lint/engine.py`.
- Piece 1 must make `run_rule` load and filter the complete engine-discovered `Sequence[SourceFile]`, invoke `rule.prepare_corpus(sources)` exactly once, then begin the unary `rule.detect(source)` loop. Preparation failures must become the existing deterministic stderr diagnostic and exit code `2`.
- Fail closed in this port: construct the rule only after verifying the landed `LintRule.prepare_corpus` surface; if absent, emit a dependency diagnostic and return `2`. Do not add a local discovery pass, filesystem glob, `git ls-files`, or a per-detect metadata lookup.
- Build each production rule through a factory. Its preparation callback receives the engine’s complete discovered collection once, builds an in-memory prepared corpus, and its `detect()` closure reads only that captured corpus.

### NEW: python/larch/lint/self_disarmable_gate_detector.py

- Move the AST scanner, metadata resolution, suppression owner validation, and compatibility data types from the current rule.
- Import `ScanError` from `larch.lint.engine`, re-export that same class for compatibility, and raise only this engine exception from preparation, metadata resolution, and scan emission; do not retain or raise a local `RuntimeError`-derived `ScanError`.
- Define corpus preparation over `Mapping[str, SourceFile]` keyed strictly by engine repo-relative `SourceFile.path` values, including `python/larch/design/...`.
- Before consuming any `SourceFile.python_ast`, call `SourceFile.python_syntax_error()`; when it reports an error, raise engine `ScanError` with the exact legacy `_read_parse` `cannot parse source` diagnostic shape. Consume the cached AST only after this syntax probe succeeds.
- Make `resolve_optional_metadata` consume that mapping and cached `SourceFile.python_ast` values only; resolve local definitions and supported imports or re-exports without filesystem reads outside the supplied corpus.
- Return a prepared in-memory context containing the resolved `MetadataResolution` and metadata fields for all later scans; reject missing, unreadable, malformed, or incomplete `OptionalMetadata` definitions.
- Preserve malformed-definition failures, hard-trigger and presentation-softening detection, finding messages, qualified symbols, ordering, and owner-qualified suppression validation.
- Keep `scan_file`, `resolve_optional_metadata`, `Finding`, `ScanError`, and `MetadataResolution` available as compatibility exports, while making production scanning use repo-relative `SourceFile` paths and the prepared corpus rather than legacy `Path` discovery.

### REWRITTEN: python/larch/lint/lint_self_disarmable_gate.py

- Define `PATHSPECS = ("python/larch/design/*.py",)` and a source filter that retains only flat production modules directly under `python/larch/design/` and rejects `test_*.py`, matching the legacy `iter_gate_modules` scope.
- Define the engine rule with:
  - `rule_id=SUPPRESSION` and `suppression_token=SUPPRESSION`;
  - `syntax_policy="raise"` to preserve `ScanError` failure behavior;
  - `allow_inline_suppression=False`, so detector-only validation requires a non-empty reason naming the gate owner;
  - `require_baseline=False` and no baseline path or baseline CLI behavior.
- Use `build_rule()` to create a fresh preparation closure for each run. Its `prepare_corpus(sources: Sequence[SourceFile]) -> None` must:
  - receive the complete discovered and source-filtered sequence once;
  - key it by `source.path`;
  - call the detector’s corpus-only preparation once;
  - capture the resulting metadata context for `detect()`.
- In `detect(source)`, scan only the supplied source plus captured context; adapt each detector hit to engine `Finding` with `path=source.path`, preserving the hit line, message, and qualified symbol. Do not use legacy `larch/design/...` paths for engine findings.
- Keep `main(argv) -> int` registered through the existing CLI and call `run_rule(build_rule(), ...)` with the injected runner. Before construction, check that Piece 1’s `LintRule.prepare_corpus` contract exists and fail with exit `2` if it does not.
- Re-export `Finding`, engine `ScanError`, `MetadataResolution`, `SUPPRESSION`, `scan_file`, and `resolve_optional_metadata`.
- Keep this wrapper at or below approximately 250 lines.

### UPDATED: python/tests/lint/test_lint_self_disarmable_gate.py

- Convert rule-level coverage to repo-relative `SourceFile` fixtures, corpus preparation, `detect()`, and engine execution; build metadata maps from those fixtures rather than `Path` trees.
- Assert the engine call order: discovery and source filtering produce the full design corpus, preparation receives that exact collection once before detection, and no independent discovery or filesystem metadata resolution occurs.
- Assert the rule configuration exactly preserves flat design scope, test-module exclusion, `syntax_policy="raise"`, `allow_inline_suppression=False`, `require_baseline=False`, and `SUPPRESSION`.
- Retain regressions for hard-trigger short circuits, conditional replacement, AND-negation, compliant OR triggers, presentation softening, ordering, nested branches, and validation-only conditions.
- Cover local and re-exported `OptionalMetadata`, missing required fields, malformed definitions, empty suppression reasons, and missing owner attribution.
- Assert detector preparation, metadata resolution, owner validation, and scan failures raise the engine’s `ScanError` class rather than a local compatibility exception.
- Add malformed-Python corpus regressions that assert preparation probes `python_syntax_error()` before AST access, returns exit `2`, and preserves the legacy `cannot parse source` diagnostic.
- Add detector and engine-path regressions showing that a non-empty suppression reason naming the gate owner suppresses the finding and produces clean exit `0`.
- Assert repo-relative finding paths, baseline-free CLI behavior, deterministic engine rendering, and clean current-corpus output.

### UPDATED: python/tests/lint/test_lint_engine_equivalence.py

- Replace the legacy self-disarmable-gate adapter with `SourceFile` corpus construction, one preparation call, and the resulting `detect()` path.
- Preserve fixture identities and rendered golden output while asserting that engine findings use repo-relative `python/larch/design/...` paths.
- Ensure every synthetic design source participates in one prepared corpus before any self-disarmable-gate detection.
- Cover malformed Python through the engine path and assert the legacy parse diagnostic is rendered as an exit-`2` engine diagnostic.

### MAY_UPDATE: python/lint-module-manifest.json

- Add a detector record only if Piece 1 expands the manifest beyond `lint_*.py`.
- Under the current schema, do not add `self_disarmable_gate_detector.py`; it would be an invalid stale record because the manifest accepts only `lint_*.py` modules.

## Edge cases

- Reject missing, unreadable, malformed, or incomplete `OptionalMetadata` definitions.
- Probe cached source syntax before accessing a cached AST, preserving the legacy `cannot parse source` failure for malformed Python.
- Follow supported import and re-export forms from cached corpus ASTs only.
- Ignore non-design, nested-design, and test modules.
- Preserve suppression only when the reason is non-empty and names the gate owner.
- Keep metadata presentation softening legal while still flagging metadata-controlled hard-gate disarming.

## Failure modes

- Stop implementation if Piece 1 lacks `LintRule.prepare_corpus` or `run_rule` does not invoke it once after loading the complete discovered corpus and before detection.
- Do not work around a missing seam with filesystem globbing, a second `git ls-files`, or filesystem-backed `resolve_optional_metadata`.
- Raise only `larch.lint.engine.ScanError` for detector, preparation, syntax, metadata, and owner-validation failures so the engine preserves deterministic exit-`2` diagnostics.
- Treat golden-output drift, non-repo-relative finding paths, or newly introduced baseline handling as regressions.

## Testing strategy

- Run `make test-lint-self-disarmable-gate`.
- Run `make lint-self-disarmable-gate`.
- Run the self-disarmable-gate cases in `python/tests/lint/test_lint_engine_equivalence.py`.
- Run the module-manifest lint if its JSON changes.
- Confirm malformed-Python preparation reports the legacy parse diagnostic through engine exit code `2`.
- Confirm the production wrapper remains within the approximate 250-line limit.

## Acceptance

- Run `make test-lint-self-disarmable-gate`.
- Run `make lint-self-disarmable-gate`.
- Run the self-disarmable-gate cases in `python/tests/lint/test_lint_engine_equivalence.py`.
- Run the module-manifest lint if its JSON changes.
- Confirm malformed-Python preparation reports the legacy parse diagnostic through engine exit code `2`.
- Confirm the production wrapper remains within the approximate 250-line limit.

diff_added: 680
diff_deleted: 570
mechanical_churn: true
diff_lines: 1250

## Test plan
(no test plan section in plan-file)
