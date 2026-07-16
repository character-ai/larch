## Goal
Implement issue #7479: [IMPLEMENTING] contract-unification [DEDUP] Share report Markdown block replacement.

## Implementation Plan
#### Problem

`report/tokens.py::_replace_block` and `report/timing.py::_replace_block` separately implement marker search, lone-start and lone-end recovery, absent-marker append, temporary writes, and replacement. Their warning text differs, but the state machine and write contract are the same.

#### Goal

Add a small report-local Markdown block upsert helper with typed begin/end markers and a caller-supplied diagnostic label. Migrate both reports. Use the shared atomic write owner. Preserve exact output for paired markers, malformed lone markers, missing final newline, and CRLF input.

#### Required implementation

- Add a leaf module under `python/larch/report/`; it must not import `tokens.py`, `timing.py`, or a report facade.
- Model begin marker, end marker, replacement block, and diagnostic label explicitly. Validate non-empty, distinct markers before reading the target.
- Preserve the current state machine for: one valid pair; no markers; lone begin; lone end; end before begin; multiple pairs; empty file; missing final newline; and CRLF input.
- Preserve caller-specific warning prefixes by passing a label or warning callback. The helper must not know token or timing terminology.
- Use `larch.io.atomic_write` with a same-directory temporary file. Preserve file mode and leave the original intact on failure.
- Repoint only `report/tokens.py::_replace_block` and `report/timing.py::_replace_block`. Do not generalize unrelated named-block or issue-body writers into this helper.

#### Verification

Create one table of input, block, expected bytes, and expected warning, and run it through both public caller paths. Add write-failure and unreadable-target cases. Assert that neither caller retains marker-index or temporary-replace logic.

#### Size and acceptance

Expected change: 350-600 lines with a net reduction. A shared table-driven test must run the same cases against both migrated callers. Marker parsing and recovery logic must exist in one production function.

## Test plan
(no test plan section in plan-file)
