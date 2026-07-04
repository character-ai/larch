### FINDING_1: BG-wait writer lint uses the wrong anchor
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: blocking
- **Concern**: The bg-wait writer-parity lint keys off any `.bg-wait-active` mention with a fixed eight-line window, so cleanup-only references and multiline writers in the live inventory false-fail; the current regression coverage also leans on synthetic one-line fixtures, so the broken rule can still ship if real writer shapes are not exercised.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Tune the adjacency rule against every WRITERS path on disk before merge (design_core.py and design-step3-review.sh included), or anchor on the full marker-write block rather than a fixed eight-line window; add a repo-root acceptance check or multiline fixtures so pytest cannot pass while real writers fail
  - From Cursor-Innovation: Scope adjacency to writer-emission evidence only (e.g. `>…/.bg-wait-active`, `.bg-wait-active").write_text`, `tmp.replace(marker)`, or a grouped printf redirected to the marker). Require at least one qualifying emission line per inventoried writer; ignore cleanup `rm`, variable assignments, and `.bg-wait-active.tmp` temp paths. Add a fixture mirroring `design-step3-review.sh` multiline emission
  - From Cursor-Pragmatic: Anchor adjacency on writer evidence only (redirect/`write_text`/`replace(marker)`/`mv` to the marker path), or scan the enclosing function/block; tune the window against real writer files; add a repo-root acceptance test that runs `lint bg-wait-writer-parity` on the live tree, not only synthetic `writer_text` fixtures.
  - From Cursor-Requirements: Define adjacency on writer blocks only: ignore cleanup `rm` references, or require one passing write block per file. Pair `CLONE_PATH=` with the `printf`/`write_text`/`mv` that materializes the marker. Size the window from the live inventory (≥15 lines) or use function-scoped pairing. Add a repo-root fixture test that runs the lint against real `design-step3-review.sh` and `design_core.py`, not only synthetic one-line `printf` stubs.


### FINDING_2: Liveness rename compare needs an exclusion or shared core
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Cursor-dyn-Bg Wait Lifecycle
- **Severity**: blocking
- **Concern**: `compare_renamed_pair` on `marker_is_live` vs `is_marker_live` assumes rename-only drift, but the live bodies still diverge in parent-guard, reset helper, marker-step metadata, missing-marker handling, and return-code behavior; a full-body compare will fail unless the harness documents an exclusion or narrows comparison to a shared core.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Before adding the liveness compare_renamed_pair call, audit whether the divergence is intentional; if yes, document an explicit harness exclusion with rationale and limit renamed-pair coverage to marker_step_completed or is_step_completed only; if no, add a reconcile step to the plan before enabling the comparison
  - From Codex-Arch: Compare only the shared live-state logic, or add an explicit documented exclusion for this renamed pair and keep its behavior covered by existing hook tests
  - From Cursor-Innovation: Limit renamed semantic compare to `marker_step_completed`/`is_step_completed` (bodies already match). For Item 8 either document an explicit harness exclusion with rationale, or compare only a shared extracted fragment both hooks must keep identical—not full `marker_is_live`/`is_marker_live` bodies
  - From Codex-Innovation: Strip comment lines or compare a code-only projection for the renamed pairs, or add an explicit exclusion comment if you intend to skip comment parity.
  - From Cursor-Pragmatic: Limit renamed-pair comparison to `marker_step_completed` / `is_step_completed` (shared sentinel table), or document an explicit harness exclusion for the liveness pair with rationale; do not byte-compare liveness helpers without normalizing hook-specific reset/parent-guard differences you do not intend to equate.
  - From Codex-Pragmatic: Add pair-specific normalization for the known extra reset/comment lines, or compare only the shared decision block after stripping the no-progress-only init/reset lines
  - From Cursor-Requirements: Document allowed per-hook deltas and normalize only those tokens (`reset_probe_counter_for_step`↔`reset_no_progress_state`, optional preamble blocks), or compare a shared core slice both hooks must keep identical. Add a harness fixture that runs `compare_renamed_pair` on the live hook sources and assert the expected pass/fail baseline before merge.
  - From Cursor-dyn-Bg Wait Lifecycle: Extend normalization to map reset_probe_counter_for_step↔reset_no_progress_state (and any other paired tokens), or drop the liveness compare_renamed_pair and document an explicit exclusion in scripts/test-hook-clone-ownership-parity.md with rationale


### FINDING_3: Step-completion rename compare still needs comment stripping
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-dyn-Bg Wait Lifecycle, Codex-Requirements
- **Severity**: blocking
- **Concern**: `compare_renamed_pair` on `marker_step_completed` vs `is_step_completed` still sees comment-only drift, so the harness needs to strip comments or compare only the executable/case body before diffing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Strip `#` comment lines (or compare only the `case`/`esac` body) in `compare_renamed_pair` before diffing; keep byte-identical checks for the already-covered same-name helpers.
  - From Cursor-dyn-Bg Wait Lifecycle: Strip # comment lines before diff, or sync/truncate comments in one hook, or compare only from the first local/case line
  - From Codex-Requirements: Compare only executable lines, or strip comment-only lines before diffing, then normalize the renamed function and callee names.


### FINDING_5: Step-3 bg-wait arming skips pre-cleanup
- **Reviewer(s)**: Codex-dyn-Bg Wait Lifecycle
- **Severity**: important
- **Concern**: `run_step_checks_main` arms bg-wait without the wrapper's pre-arm cleanup, so stale `.completed/step-3-terminal` or probe-denial counters can make the new marker look already released or clamp-stuck.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-Bg Wait Lifecycle: Before entering the marker context, clear the step-3 terminal sentinel and its probe-denial counter, or factor that cleanup into the shared helper


### FINDING_6: run_step_checks_main uses the wrong self-review marker tuple
- **Reviewer(s)**: Codex-dyn-Bg Wait Lifecycle
- **Severity**: blocking
- **Concern**: `run_step_checks_main` reuses the composite self-review marker tuple and timeout instead of the step3-only values, so a checks-only call can mint the wrong terminal marker and outlive the actual checks phase.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-Bg Wait Lifecycle: Keep run_step_checks_main step3-only with the 10800-second timeout from run-step-checks.sh, and leave step5-self-review ownership in checks_commit_route_main


### FINDING_1: Renamed-pair parity is defined but never exercised
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: The harness adds a renamed-pair comparison helper, but the step-completion pair still is not invoked, so one-sided drift in `marker_step_completed` / `is_step_completed` can still slip through.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: After implementing compare_renamed_pair, invoke it from the script bottom with per-hook names, e.g. compare_renamed_pair "$BG_HOOK" marker_step_completed "$NO_PROGRESS_HOOK" is_step_completed; document the call in scripts/test-hook-clone-ownership-parity.md
  - From Cursor-Innovation: After defining compare_renamed_pair, add a harness call that extracts marker_step_completed from hook-bg-poll-guard.sh and is_step_completed from hook-no-progress-guard.sh, runs comment-stripped comparison, and fails on executable-body drift.
  - From Cursor-Requirements: After compare_renamed_pair is defined, call compare_renamed_pair marker_step_completed is_step_completed (or equivalent) alongside the existing compare_function invocations


### FINDING_3: step_7a still needs explicit duplicate-helper cleanup
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The dedup plan leaves room for local copies of the bg-wait helpers to survive in `step_7a.py`, preserving a second drift surface even after `dispatch_commit_route.py` is cleaned up.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add explicit step_7a cleanup: remove the local `_clear_no_progress_sidecars`, `_read_keepalive_clone_path`, and `_write_bg_wait_marker` bodies and import them from `larch.implement.bg_wait` (keep only the local `_bg_wait_marker` / `_write_terminal_sentinel` context wrapper).
  - From Cursor-Requirements: Mirror the dispatch_commit_route.py instructions: remove the three duplicate helpers from step_7a.py and import _write_bg_wait_marker from larch.implement.bg_wait inside the local _bg_wait_marker context manager


### FINDING_4: `time` is still live in the Step 5 resume path
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: The plan treats `time` as removable, but `step5_resume_main` still uses `int(time.time())`, so removing the import would raise `NameError` on the Step 5 resume path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Revise the plan to keep import time unless the final diff proves all non-marker uses are gone


### FINDING_6: Step 7a test still references a symbol the extraction removes
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The test update asks `test_step_7a.py` to call `step_7a._write_bg_wait_marker` even though the extraction plan removes that symbol, so the test contract conflicts with the refactor.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Update test_step7a_bg_wait_marker_copies_keepalive_clone_path to exercise larch.implement.bg_wait._write_bg_wait_marker directly or to enter step_7a._bg_wait_marker and assert the marker fields; do not require step_7a._write_bg_wait_marker to remain


