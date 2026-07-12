### FINDING_2: Origin scanning must use an explicit, unsqueezed root-cause allowlist
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements, Cursor-dyn-Origin Contract Auditor
- **Severity**: major
- **Concern**: The origin input is not concretely restricted to the intended diagnostic sources. Scanning all retained sections can classify markers from `summary` or suggested-fix text, while limiting the scan to squeezed sections can miss markers beyond the caps. The contract must explicitly include title, root-cause sections, and `_freeform` where applicable, while excluding non-diagnostic sections and `_title_only`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Define the body input as normalized title plus only root-cause keys already produced by `_pick_sections` (`root cause analysis`, `root cause`, and `_freeform` fallback), explicitly excluding summary and suggested-fix sections; add a unit test that markers in excluded sections do not change origin
  - From Cursor-Innovation: Name the exact allowlist in the plan and code: only normalized title plus section keys whose names start with `root cause` (and `_freeform` / `_title_only` fallbacks). Add a negative test where a marker appears only in `summary` or `suggested fix(es)` and origin stays `unknown`.
  - From Cursor-Requirements: Name the origin input sources explicitly: normalized title, section keys matching root-cause headings (`root cause`, `root cause analysis`), and `_freeform` when present; keep `_title_only` title-only.
  - From Cursor-Requirements: Restrict body scanning to title plus root-cause section keys and `_freeform`; exclude `summary`, `suggested fix`, `suggested fix(es)`, and `_title_only` value text.
  - From Cursor-Requirements: Add a freeform-body fixture with a referenced regression marker in `_freeform`, assert expected `origin`, and assert summary-only marker text does not classify when root-cause sections are absent.
  - From Cursor-dyn-Origin Contract Auditor: Run origin classification from diagnostic_prefix plus unsqueezed root-cause section bodies (and title) before caps; persist the origin field on BugDigest separately from squeezed sections.
  - From Cursor-dyn-Origin Contract Auditor: Add parameterized cases where the only regression marker or heuristic phrase sits in summary or suggested fix(es) and origin remains unknown.


### FINDING_4: `--zones` and `--search` conflict behavior is undefined
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Origin Contract Auditor
- **Severity**: minor
- **Concern**: The search-source precedence rules address `--search` and verbal text but do not define what happens when `--zones` is combined with `--search`. Zones may be silently ignored, applied twice, or resolved inconsistently, violating the one-search-source contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend Step 1 precedence to `--search` > `--zones` > verbal > default; reject `--zones` when `--search` is present with a clear argument error before preparation
  - From Cursor-Innovation: Add the same hard error used for zones+verbal when both `--zones` and `--search` appear, or document and harness-pin that `--search` wins and `--zones` is ignored.
  - From Cursor-Pragmatic: Add an explicit Step 1 rule: when `--search` is present, reject `--zones` with a clear argument error; pin the same conflict in `scripts/test-learn-from-bugs-structure.sh`.
  - From Cursor-Requirements: Document and enforce mutual exclusion: reject `--zones` whenever `--search` is present, with the same hard error style as the zones-plus-verbal case; pin it in the structural harness.
  - From Cursor-dyn-Origin Contract Auditor: Hard-error when `--zones` and `--search` are both present (mirror the zones-plus-verbal rule), and pin that conflict in `scripts/test-learn-from-bugs-structure.sh`.


### FINDING_7: `--zones` translation lacks executable coverage
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-dyn-Origin Contract Auditor
- **Severity**: minor
- **Concern**: Structural checks of documentation cannot verify that zone parsing actually produces the required query or handles trimming, empty elements, exact OR grouping, conflicting sources, and argument-safe forwarding.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add a focused test for the zone-resolution contract, covering `design,implement` translation, whitespace trimming, empty elements, and conflicts with `--search` or verbal search text; keep the structural assertions for documentation alignment
  - From Codex-Innovation: Define a small deterministic search-resolution seam, or explicitly add a structural harness test that validates the complete translation and conflict contract instead of claiming an executable translation test. Ensure the test covers trimming, empty elements, `--search` precedence, and the exact OR-group output.
  - From Codex-dyn-Origin Contract Auditor: Add an executable argument-resolution fixture or harness covering the exact query, whitespace, empty values, conflicting sources, and argv-safe forwarding.


### FINDING_9: Report headline and prose-only contracts lack deterministic tests
- **Reviewer(s)**: Codex-Requirements, Cursor-dyn-Origin Contract Auditor, Codex-dyn-Origin Contract Auditor
- **Severity**: major
- **Concern**: The planned marker and structural tests do not verify the generated report contract. A prompt can contain the required wording while output still misorders the headline, omits counts or percentages, reverses chains, miscomputes denominators or ratios, or fails to emit the prose-only mechanical-alternative line.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add a report-fixture test or equivalent deterministic report-contract harness that feeds synthetic digest records and asserts headline ordering, counts and percentages, chain direction, regression ratio, and the prose-only marker with its mechanical-alternative line
  - From Cursor-dyn-Origin Contract Auditor: Either add a minimal pure headline/chain formatter in learn_from_bugs.py with unit tests, or explicitly demote acceptance 1-2 to manual-only in the plan Testing strategy and align the issue Tests wording so the contract is not claimed as pytest-verified.


### FINDING_10: Origin extraction must run before section truncation
- **Reviewer(s)**: Cursor-dyn-Origin Contract Auditor
- **Severity**: major
- **Concern**: `build_digest` stores capped section text before origin extraction. Referenced markers appearing after `ROOT_CAUSE_CAP` or `FREEFORM_CAP` can therefore be discarded and classified as `unknown`, violating the required origin extraction behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-Origin Contract Auditor: Run origin classification from diagnostic_prefix plus unsqueezed root-cause section bodies (and title) before caps; persist the origin field on BugDigest separately from squeezed sections.


### FINDING_7: Repeated Root Cause sections are lost by dictionary-based parsing
- **Reviewer(s)**: Codex-Pragmatic, Codex-Requirements
- **Severity**: minor
- **Concern**: The planned origin helper relies on `_split_sections()`, which overwrites repeated headings. When an issue contains multiple Root Cause sections, only the last body remains, so markers in earlier sections are missed and the required document-order classification becomes incorrect.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Add a minimal origin-specific ordered section iterator, or adjust section parsing to preserve repeated headings, then test a marker in the first of two root-cause sections
  - From Codex-Requirements: Add an ordered, unsqueezed section iterator or extend the splitter to preserve duplicate sections, then classify every allowed root-cause body in document order.

