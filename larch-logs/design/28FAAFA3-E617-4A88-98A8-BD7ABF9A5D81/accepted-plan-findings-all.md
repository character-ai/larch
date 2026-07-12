### FINDING_1: `issue_wire.extract_scope_paths` still uses ###-only heading regex
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Cursor-dyn-Wire Compatibility Auditor, Codex-dyn-Wire Compatibility Auditor
- **Severity**: major
- **Concern**: The plan unifies `##`/`###` and bracket firm-heading forms in `plan_grammar`, but `extract_scope_paths` in `issue_wire.py` still matches only level-three colon headings (`^###\s+(NEW|UPDATED|REWRITTEN|MAY_UPDATE)\s*:`). Plans using accepted `##` or bracket firm headings can pass grammar-aware consumers while `dispatch_step2`, `scope_disposition`, `dirty_tree` scope-check, and related coverage gates see incomplete or empty scope paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add ### UPDATED: python/larch/issue/issue_wire.py to delegate extract_scope_paths to plan_grammar section iteration (marker APIs stay in issue_wire); extend python/tests/issue/test_issue_wire.py for ## and bracket parity
  - From Codex-Arch: Add `issue_wire.py` to the migration, use the shared heading matcher while retaining issue-wire ownership of `larch:plan` markers, and add compatibility tests for every accepted heading form through `extract_scope_paths`
  - From Cursor-Innovation: Add ### UPDATED: python/larch/issue/issue_wire.py delegating scope-path extraction to plan_grammar fence-aware heading/section iterators; extend python/tests/issue/test_issue_wire.py with ## and bracket firm-heading fixtures
  - From Codex-Innovation: Update issue_wire.extract_scope_paths to consume plan_grammar heading matches and add its integration tests; keep issue_wire as the marker owner
  - From Cursor-Pragmatic: Add an `UPDATED: python/larch/issue/issue_wire.py` step: keep Files-to-modify section bounds and path-tail extraction local, but delegate heading-kind recognition to `plan_grammar` (or a shared iterator). Extend compatibility fixtures so bracket/`##` headings inside the scope section parse the same paths command validation already accepts.
  - From Cursor-dyn-Wire Compatibility Auditor: Add ### UPDATED: python/larch/issue/issue_wire.py (or a single shared helper) delegating heading detection in extract_scope_paths to plan_grammar section iteration; keep marker ownership in issue_wire
  - From Cursor-dyn-Wire Compatibility Auditor: Add `### UPDATED: python/larch/issue/issue_wire.py` to import the shared compose/split/peel APIs from `plan_grammar` (or thin public wrappers), not from `design_step5c` privates.


### FINDING_2: Gate B review path still owns duplicate optional-trailer registry and parser
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-dyn-Wire Compatibility Auditor
- **Severity**: major
- **Concern**: `plan_review_common.py` and `plan_review_loop.py` are absent from the migration list but still define `OPTIONAL_TRAILER_KEYS` and `_trailer_map()` outside `plan_grammar`. Adding or changing a trailer key in the shared module can leave Gate B snapshot/dedup on a stale four-key set. Gate B also scans optional size keys on any plan line, not only the terminal contiguous trailer block used elsewhere, so a naive contiguous-only repoint would change live dedup behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: A new optional trailer key added only in plan_grammar will not update Gate B snapshot/dedup; post-migration grep will still find a second owner and trailer-key-dedup can false-fail or miss keys Add firm ### UPDATED rows for plan_review_common.py and plan_review_loop.py to import the shared optional-key subset and parse the final contiguous optional block via plan_grammar; keep existing Gate B dedup tests in python/tests/review/test_plan_review.py passing
  - From Codex-Arch: Add `plan_review_common.py` and `plan_review_loop.py` to the firm updated-file set, replace `OPTIONAL_TRAILER_KEYS` and `_trailer_map` with the shared parser or registry, and add focused tests for snapshot and dedup behavior
  - From Cursor-Innovation: Add ### UPDATED: python/larch/review/plan_review_common.py (and plan_review_loop if _trailer_map stays) importing the optional-size subset from plan_grammar; pin parity in existing gate-b-dedup tests under python/tests/review/test_plan_review.py
  - From Cursor-Pragmatic: Add explicit `UPDATED` steps for `plan_review_common.py` and `plan_review_loop.py` to import the shared registry/parser, and decide/document whether Gate B should keep whole-file scanning or align with contiguous final-block semantics. Add `python/tests/review/test_plan_review.py` Gate B cases for the full shared trailer set.
  - From Cursor-dyn-Wire Compatibility Auditor: Post-migration grep still finds a second trailer-key owner; gate-b snapshot/dedup can drift when keys are added only to plan_grammar Add ### UPDATED: python/larch/review/plan_review_common.py and ### UPDATED: python/larch/review/plan_review_loop.py to import a documented size-only subset from plan_grammar and replace _trailer_map with shared parsing
  - From Cursor-dyn-Wire Compatibility Auditor: Add updates for `plan_review_common.py` and `plan_review_loop.py`; import a documented size-only subset from `plan_grammar`, not the full registry.
  - From Cursor-dyn-Wire Compatibility Auditor: When repointing gate-b, either preserve explicit whole-file collection for the size-only subset or document and test the intentional shift to contiguous-block-only semantics.


### FINDING_4: `confidence:` trailer-span interaction with shared parser not specified
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: The plan does not state how non-registry `confidence:` lines interact with shared trailer-span detection in `difficulty.py`. A strict registry-only contiguous parser can change `plan_difficulty` and malformed-adjacent outcomes exercised in `python/tests/calibration/test_difficulty.py` because `confidence:` is excluded from `_PLAN_TRAILER_LINE_RE` but still scanned by `_adjacent_invalid_difficulty`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: difficulty.py today treats confidence: as legacy-adjacent (excluded from _PLAN_TRAILER_LINE_RE span, still scanned by _adjacent_invalid_difficulty). A strict registry-only contiguous parser can change plan_difficulty and malformed-adjacent outcomes exercised in python/tests/calibration/test_difficulty.py State in plan_grammar contract that confidence: is registry-excluded and does not extend the trailer span; keep difficulty-local adjacent invalid-tier logic on that helper, or add an explicit plan_grammar API for span boundaries that preserves current confidence behavior


### FINDING_6: `plan_quality` firm-heading size gate may diverge from shared grammar
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Concern**: The `plan_quality.py` update does not explicitly bind `_firm_heading_paths` to the same `plan_grammar` firm-kind iterator used for command parsing. `_heading_count` may move to `plan_grammar` while `_firm_heading_paths` keeps calling `issue_wire`, so firm-heading oversize reasons can disagree across consumers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In the plan_quality bullet require _firm_heading_paths/_firm_heading_count use the same plan_grammar firm-kind iterator as command parsing, with one consumer test proving parity across ###, ##, and bracket forms


### FINDING_8: Preflight blank-line tolerance conflicts with contiguous trailer parser
- **Reviewer(s)**: Cursor-dyn-Wire Compatibility Auditor
- **Severity**: major
- **Concern**: `implement/preflight.py` tolerates blank lines inside the final metadata window when locating `review_status` / `rounds_completed` / `difficulty`, but shared `parse_optional_metadata` stops at the first non-trailer line including blanks. Replacing the preflight local scan with the shared contiguous-block parser would drop metadata separated from size trailers by blank lines and break accepted plans.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-Wire Compatibility Auditor: Replacing _plan_review_meta_value with the shared contiguous-block parser would drop review_status/difficulty separated from size trailers by blank lines, breaking existing accepted plans In preflight.py keep policy-local scanning (or a plan_grammar lenient final-region accessor with blank-skip); use shared parser only where contiguous-block semantics match today
  - From Cursor-dyn-Wire Compatibility Auditor: In the preflight update, keep policy-local lenient final-region lookup (blank-tolerant) for `review_status` / `rounds_completed` / `difficulty`, and use the shared parser only where contiguous-block semantics are intended.


### FINDING_9: `plan_review_loop` `diff_lines` consumer uses divergent whole-plan scan
- **Reviewer(s)**: Codex-dyn-Wire Compatibility Auditor
- **Severity**: major
- **Concern**: The plan omits an active `diff_lines` consumer in `plan_review_loop.py` where `emit_plan` accepts the first matching line anywhere and continuation logic uses the last matching line anywhere, rather than the final contiguous trailer block. This preserves a second effective owner for `diff_lines` and can drive sidecar emission or structural-size decisions differently from the shared parser.
- **Suggested revisions (informational for voters; coder decides)**:


### FINDING_3: Scope extraction can terminate before valid headings and fenced examples
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: The planned scope extraction may apply a generic level-two section terminator before the shared fence-aware firm-heading iterator recognizes valid `## NEW: path` headings. Heading-like text inside fences may also terminate the section prematurely, causing dispatch and dirty-tree scope checks to miss valid paths accepted by the shared grammar.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Define section-bound precedence around the shared fence-aware iterator: recognize valid firm headings before generic section termination, and ignore all headings while inside fences. Add fixtures combining level-two headings, fenced heading-like text, and later scope entries.


