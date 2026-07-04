### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-hook-clone-ownership-parity.sh
- **Concern**: Item 7 adds compare_renamed_pair but never wires it into the harness entrypoint for the renamed step-completion helpers. Scenario: Plan defines comment-stripped compare_renamed_pair yet leaves only the five same-name compare_function calls; marker_step_completed (hook-bg-poll-guard.sh) vs is_step_completed (hook-no-progress-guard.sh) still go unchecked and Item 7 acceptance is not met
- **Proposed resolution**: After implementing compare_renamed_pair, invoke it from the script bottom with per-hook names, e.g. compare_renamed_pair "$BG_HOOK" marker_step_completed "$NO_PROGRESS_HOOK" is_step_completed; document the call in scripts/test-hook-clone-ownership-parity.md

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_bg_wait_writer_parity.py
- **Concern**: FINDING_1 adjacency rule still omits live design writer shapes. Scenario: The planned rule requires .bg-wait-active and a write-context token on the same line; design_core.py writes via tmp.write_text plus tmp.replace(marker) and design-step3-review.sh uses multiline printf to a tmp file then mv, so no line satisfies the rule even though CLONE_PATH= is in the writer block. The repo-root acceptance test will fail until the implementer improvises
- **Proposed resolution**: Extend the plan rule to anchor on the writer function/block: treat a .bg-wait-active path assignment within the window as the anchor, or scan the enclosing function for CLONE_PATH= near write_text/printf/replace/mv marker promotion; keep the repo-root acceptance test as the gate **1. correctness — `scripts/test-hook-clone-ownership-parity.sh`** Item 7 adds `compare_renamed_pair` but never calls it. The script still only runs the five same-name `compare_function` checks, so `marker_step_completed` vs `is_step_completed` stay uncovered and Item 7 is not done. Wire an entrypoint call with per-hook names (for example `compare_renamed_pair "$BG_HOOK" marker_step_completed "$NO_PROGRESS_HOOK" is_step_completed`) and note it in `scripts/test-hook-clone-ownership-parity.md`. **2. correctness — `python/larch/lint/lint_bg_wait_writer_parity.py`** FINDING_1 is still incomplete. The planned rule needs `.bg-wait-active` and a write-context token on the same line. `design_core.py` uses `tmp.write_text` + `tmp.replace(marker)`, and `design-step3-review.sh` uses multiline `printf` to a tmp file then `mv`, so no line matches even though `CLONE_PATH=` is in the writer block. The repo-root acceptance test will fail until someone extends the rule. Anchor on the writer function/block: treat a `.bg-wait-active` path assignment in the window as the anchor, or scan the enclosing function for `CLONE_PATH=` near `write_text` / `printf` / `replace` / `mv` promotion.

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_bg_wait_writer_parity.py:41-48
- **Concern**: FINDING_1 fix still anchors only same-line literal marker writes. Scenario: The plan's replacement scan requires a non-comment line to contain both .bg-wait-active and a write indicator, but live writers use indirect temp paths: skills/design/scripts/design-step3-review.sh:155-171 writes CLONE_PATH to _bg_wait_tmp then mv's to _bg_wait_marker, and python/larch/design/design_core.py:175-197 assigns marker then tmp.write_text/tmp.replace(marker). The proposed lint can false-fail the live WRITERS inventory or force an ad hoc deviation from the plan.
- **Proposed resolution**: Revise _has_clone_path_emission to treat marker variable assignment plus temp-to-marker mv/replace/write_text in the same function or nearby block as the write context, then require CLONE_PATH= within that block/window; add a fixture for this indirect temp-writer shape.

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_bg_wait_writer_parity.py:41-48
- **Concern**: FINDING_1 adjacency rule still misses atomic tmp/mv/replace writers. Scenario: The plan anchors on lines that contain both `.bg-wait-active` and a write indicator on the same line. Live inventory writers `python/larch/design/design_core.py:175-193` and `skills/design/scripts/design-step3-review.sh:155-169` emit `CLONE_PATH=` in a `printf`/`write_text` block and publish via `tmp.replace(marker)` or `mv` to a variable assigned from `.bg-wait-active`, so no single line satisfies the stated predicate. The mandated repo-root acceptance test would fail or force ad-hoc rule drift.
- **Proposed resolution**: Extend write-context detection: treat a ±15-line window around any of `write_text(`, `printf`, `>`, `.replace(`, or `mv` as an anchor when the same window also references `.bg-wait-active` (literal or via a marker variable assigned from it); require `CLONE_PATH=` inside that window. Add fixtures mirroring `design_core.py` and `design-step3-review.sh`.

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: code-quality
- **Location**: scripts/test-hook-clone-ownership-parity.sh:14-49
- **Concern**: Item 7 defines `compare_renamed_pair` but does not require calling it. Scenario: The harness still only byte-compares same-named helpers (`compare_function canonical_dir`, etc.). Item 7 acceptance needs semantic equivalence for `marker_step_completed` vs `is_step_completed`, but the plan specifies the helper algorithm without an explicit invocation for that renamed pair, so the helper can land unused and item 7 stays unverified.
- **Proposed resolution**: After defining `compare_renamed_pair`, add a harness call that extracts `marker_step_completed` from `hook-bg-poll-guard.sh` and `is_step_completed` from `hook-no-progress-guard.sh`, runs comment-stripped comparison, and fails on executable-body drift.

### FINDING_6:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:83-91; skills/design/scripts/design-step3-review.sh:155-171; python/larch/design/design_core.py:175-194
- **Concern**: The prior FINDING_1 fix is still incomplete because the planned lint anchors only lines that contain `.bg-wait-active` and a write-context token, but live writers store the marker in variables and write via temp files or `.replace(marker)`.. Scenario: If `CLONE_PATH=` is removed from `design_bg_wait_marker_start` or `_bg_wait_marker_context`, the planned adjacency check may find no qualifying write-context anchor and either pass by vacuity or only protect the new simpler fixtures, so Item 1 still allows the false-negative it is meant to close.
- **Proposed resolution**: Make the lint function/block scoped for variable-backed writers, or explicitly track marker variables and temp-file moves/replaces. Add a negative fixture shaped like `design-step3-review.sh` or `design_core.py`, with `.bg-wait-active` assigned to a variable and an unrelated far `CLONE_PATH=` line.

### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_bg_wait_writer_parity.py:41-48
- **Concern**: Write-scoped CLONE_PATH anchor is underspecified for live design writers. Scenario: The plan requires `.bg-wait-active` on the same line as a write indicator (`write_text(`, `printf`, `>`, `.replace(`). `python/larch/design/design_core.py` writes via `tmp.write_text(...)` then `tmp.replace(marker)` with no literal `.bg-wait-active` on either line; `skills/design/scripts/design-step3-review.sh` uses a multiline `printf` redirected to `$_bg_wait_tmp` then `mv` to `$_bg_wait_marker`. Both are in WRITERS and the mandated repo-root acceptance test would false-fail despite valid CLONE_PATH emission.
- **Proposed resolution**: Define anchors as a ±15 window around either (a) a write-indicator line or (b) an assignment to a `*.bg-wait-active` path, and require `CLONE_PATH=` in that window; treat `mv`/`replace` promotion from a temp file as write context. Add fixture regressions mirroring `design_core.py` and `design-step3-review.sh` shapes.

### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: code-quality
- **Location**: python/larch/implement/step_7a.py:74-105
- **Concern**: Item 3 extraction omits explicit duplicate removal in step_7a. Scenario: `dispatch_commit_route.py` is told to delete `_clear_no_progress_sidecars`, `_read_keepalive_clone_path`, and `_write_bg_wait_marker`; `step_7a.py` only says to keep `_bg_wait_marker` and call the imported helper. An implementer can import `bg_wait._write_bg_wait_marker` while leaving byte-identical duplicate helpers in `step_7a.py`, defeating item 3 dedup.
- **Proposed resolution**: Add explicit step_7a cleanup: remove the local `_clear_no_progress_sidecars`, `_read_keepalive_clone_path`, and `_write_bg_wait_marker` bodies and import them from `larch.implement.bg_wait` (keep only the local `_bg_wait_marker` / `_write_terminal_sentinel` context wrapper).

### FINDING_9:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/implement/dispatch_commit_route.py:1038
- **Concern**: Plan names time as likely removable, but time remains live after marker extraction. Scenario: Following the plan literally can remove the time import while step5_resume_main still calls int(time.time()), causing the Step 5 resume timing path to raise NameError
- **Proposed resolution**: Revise the plan to keep import time unless the final diff proves all non-marker uses are gone

### FINDING_10:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/implement/bg_wait.py:1
- **Concern**: Shared bg-wait extraction omits pyright-clean handling for the new private helper module. Scenario: Copying the current helper body into a new file can trip strict pyright on ignored write_text and unlink call results, and step_7a's call to the imported underscored helper can trip reportPrivateUsage
- **Proposed resolution**: Add either exact pyright ignores or local unused-result assignments in bg_wait.py, and add an exact reportPrivateUsage ignore for the step_7a private-helper import or call

### FINDING_11:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-hook-clone-ownership-parity.sh
- **Concern**: Item 7 adds compare_renamed_pair but never invokes it for marker_step_completed vs is_step_completed. Scenario: The harness can pass with only the five byte-identical compare_function calls, leaving the renamed step-completion pair unverified and not meeting item 7 acceptance
- **Proposed resolution**: After compare_renamed_pair is defined, call compare_renamed_pair marker_step_completed is_step_completed (or equivalent) alongside the existing compare_function invocations

### FINDING_12:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/implement/step_7a.py
- **Concern**: Item 3 dedup is explicit for dispatch_commit_route.py but step_7a.py only says _bg_wait_marker should call the imported helper. Scenario: Implementer may leave dead copies of _clear_no_progress_sidecars, _read_keepalive_clone_path, and _write_bg_wait_marker in step_7a.py, partially failing item 3 and keeping a second drift surface
- **Proposed resolution**: Mirror the dispatch_commit_route.py instructions: remove the three duplicate helpers from step_7a.py and import _write_bg_wait_marker from larch.implement.bg_wait inside the local _bg_wait_marker context manager

### FINDING_13:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/implement/test_step_7a.py
- **Concern**: Plan tells the Step 7a marker test to call step_7a._write_bg_wait_marker after extraction removes that symbol. Scenario: The mandated test update conflicts with the extraction contract and can block implementation or reintroduce a per-module wrapper solely for tests
- **Proposed resolution**: Update test_step7a_bg_wait_marker_copies_keepalive_clone_path to exercise larch.implement.bg_wait._write_bg_wait_marker directly or to enter step_7a._bg_wait_marker and assert the marker fields; do not require step_7a._write_bg_wait_marker to remain The review found three in-scope plan gaps: the hook harness defines `compare_renamed_pair` but never calls it for the step-completion pair, `step_7a.py` dedup steps are underspecified compared to `dispatch_commit_route.py`, and the Step 7a test plan still references `step_7a._write_bg_wait_marker` after extraction removes it. Prior accepted items (lint adjacency, step-3 pre-cleanup, step3-only 10800s arming, liveness exclusion) look covered in the current plan.

### FINDING_14:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_bg_wait_writer_parity.py:41-48; skills/design/scripts/design-step3-review.sh:155-169; python/larch/design/design_core.py:175-193
- **Concern**: FINDING_1 fix still lacks a reliable writer-block anchor. Scenario: The live design writers put `.bg-wait-active` in a marker variable or Path assignment, then write through a temp var or `tmp.write_text`; a literal implementation either false-fails the live repo-root test or treats zero write anchors as pass and keeps Item 1's false-negative when the marker write is removed but unrelated `CLONE_PATH=` remains
- **Proposed resolution**: Define `_has_clone_path_emission` around writer blocks or functions: treat marker variable assignment plus temp write or mv, and Python marker Path plus write_text or replace, as qualifying writer blocks; require at least one qualifying writer block; make cleanup-only pass fixtures include a real writer elsewhere and add a no-write-anchor fixture that fails
