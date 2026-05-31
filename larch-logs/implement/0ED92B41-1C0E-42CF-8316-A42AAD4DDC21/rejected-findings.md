### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: run_lint_fix monolithic function
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `run_lint_fix` combines validation, dispatch, git guards, forbidden-path reversion, and auto-commit in one ~315-line function. Parity fixes to `lint-fix-loop.sh` require editing a single giant function and brittle multi-call stub sequences in `test_checks.py`. Extract phase-aligned private helpers (`_prepare_baseline`, `_dispatch_agent`, `_finalize_delta`) while keeping the public API unchanged.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: duplicate incompatible StubRunner implementations
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Duplicate incompatible `StubRunner` implementations in `test_checks.py` and `test_git.py` with different matching semantics. `proc.Runner` signature changes (fd redirect) must be updated in multiple places, risking test drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: _run_cursor direct Path filesystem checks
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `_run_cursor` uses direct `Path` filesystem checks alongside injected `Runner`. Stub tests cannot fully cover stderr-tail selection branches without real files on disk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: lint-fix-loop mkdtemp run dirs never cleaned up
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `mkdtemp` run directories under lint-fix-loop are never cleaned up. Long implement runs with repeated fix attempts accumulate orphaned run dirs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_15: redaction write failure overwrites exit code
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Redaction write failure forces `exit_code=1` instead of preserving `relevant-checks.sh` return code. Callers use exit code 126 vs 1 to distinguish non-executable script from redaction I/O failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: repo_root used without git toplevel verification
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `repo_root` is used as cwd and agent workspace without git toplevel verification unlike `lint-fix-loop.sh`. Phase 7 wiring with a tampered session `REPO` path could run relevant-checks and codex/cursor `--full-auto` against an unintended directory.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: TOCTOU on dispatch_first redacted log path
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `dispatch_first` uses `is_file()` on redacted log path without immediate `_resolve_checks_log_path` re-check. TOCTOU symlink swap in a shared session directory could steer the fixer at sensitive file contents.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_19: structural fix failures mapped to dispatch-failed TRANSIENT
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Structural fix failures map to `dispatch-failed` `TRANSIENT` like bash. Forbidden-path or missing launcher failures may hit transient recovery instead of stall when wiring ship-pr.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: checks.py god-module size and layout
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: ~1.6k-line module with 38 functions spans capture, dispatch, git loop, and escalation. Phase 5+ CI fixer work will add more surface to an already hard-to-navigate module; flat layout prevents directory split. Add internal section boundaries and document seams; consider `checks_dispatch.py` sibling if flat constraint relaxes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_23: _read_log_tail trivial wrapper
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `_read_log_tail` is a trivial wrapper around `_read_log_text_bounded` with extra indirection and no behavioral value.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_24

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_24: _submodule_paths redundant collection
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `_submodule_paths` triple-collects submodule paths with redundant `.gitmodules` regex parse—extra I/O and dedup logic on every fix dispatch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_25

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_25: LoopResult mutable vs frozen dataclasses
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `LoopResult` is mutable while other result dataclasses are frozen—inconsistent immutability convention from Phase 4 plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_26

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_26: per-job target command string API vs args file
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Per-job target command is a string API; bash reads `--target-cmd-args-file`. Phase 7 integrator must parse args file externally or per-job prompt text diverges.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_28

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_28: run_lint_fix allowed_root fallback when allowed_tmpdir is None
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `run_lint_fix` `allowed_root` falls back to parent of `run_parent` when `allowed_tmpdir` is None. Direct API misuse could feed a checks_log outside `IMPLEMENT_TMPDIR` while `run_parent` stays under session.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_29

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_29: unchecked stat in _compose_prompt
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Unchecked `checks_log.stat` in `_compose_prompt`. Log removed between resolve and compose can raise uncaught `OSError`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

