### [rejected] FINDING_1

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_1: `1e40f8015` — Extract plan-line dedup helper from plan-review-loop.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: - `1e40f8015` — Extract plan-line dedup helper from plan-review-loop.sh
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_10

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_10: `1e40f8015` — Extract plan-line dedup helper from `plan-review-loop.sh`
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - `1e40f8015` — Extract plan-line dedup helper from `plan-review-loop.sh`
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_11: `bd17afd36` — `chore(larch-logs):` implement run flush (out of scope for correctness review)
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - `bd17afd36` — `chore(larch-logs):` implement run flush (out of scope for correctness review) **Plan vs diff:** The refactor matches the plan: verbatim Python extraction, `$DEDUP_PLAN_LINES_PY` wiring (plain `$PLUGIN_ROOT` form), unchanged failure handling (`emit-plan-failed` / `dedup-python-failed`), docs and `relevant-checks.sh` routing, `agent-lint.toml` exclusions, four eval-isolation exports, non-numeric stub fix, and a `run_loop` integration test distinct from `out_ddd`. **Correctness checks:**
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_12: Extracted dedup body is byte-identical to the former heredoc (only shebang/docstring/imports differ).
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - Extracted dedup body is byte-identical to the former heredoc (only shebang/docstring/imports differ).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_13: On dedup failure, `_run_post_apply_pipeline` still sets `LOOP_STATUS=emit-plan-failed` and `LOOP_REASON=dedup-python-failed`; `_snapshot_terminal_exit_preserving_status` preserves those and `emit_loop_kvs` maps `LOOP_REASON` → `REASON=` (lines 134–146, 368–375, 1298–1299 in `plan-review-loop.sh`).
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - On dedup failure, `_run_post_apply_pipeline` still sets `LOOP_STATUS=emit-plan-failed` and `LOOP_REASON=dedup-python-failed`; `_snapshot_terminal_exit_preserving_status` preserves those and `emit_loop_kvs` maps `LOOP_REASON` → `REASON=` (lines 134–146, 368–375, 1298–1299 in `plan-review-loop.sh`).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_14: Integration test scaffolding mirrors the existing emit-plan-failure test (`write_collect one`, revise OK); PYWRAP matches only `dedup-plan-lines.py` via basename and uses pre-captured `REAL_PYTHON` to avoid recursion.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - Integration test scaffolding mirrors the existing emit-plan-failure test (`write_collect one`, revise OK); PYWRAP matches only `dedup-plan-lines.py` via basename and uses pre-captured `REAL_PYTHON` to avoid recursion.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_17: `1e40f8015` — Extract plan-line dedup helper from plan-review-loop.sh  
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `1e40f8015` — Extract plan-line dedup helper from plan-review-loop.sh
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_18: `bd17afd36` — chore(larch-logs): flush implement run BD772253-9BF0-4046-BF8D-2ECF73B4C53F  
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `bd17afd36` — chore(larch-logs): flush implement run BD772253-9BF0-4046-BF8D-2ECF73B4C53F   ---
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_19: **Shell invocation** — `python3 "$DEDUP_PLAN_LINES_PY" "$plan_path" "$dedup_tmp"` keeps all three operands quoted; `DEDUP_PLAN_LINES_PY` is assigned from `$PLUGIN_ROOT/...` at script load (same pattern as `DESIGN_DRIVER_SH` / `INVOKE_PLAN_VALIDATOR_SH`), not from untrusted plan text.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Shell invocation** — `python3 "$DEDUP_PLAN_LINES_PY" "$plan_path" "$dedup_tmp"` keeps all three operands quoted; `DEDUP_PLAN_LINES_PY` is assigned from `$PLUGIN_ROOT/...` at script load (same pattern as `DESIGN_DRIVER_SH` / `INVOKE_PLAN_VALIDATOR_SH`), not from untrusted plan text.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_2: `bd17afd36` — chore(larch-logs): flush implement run BD772253-…
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: - `bd17afd36` — chore(larch-logs): flush implement run BD772253-… ## Review summary This branch implements issue #3166 as a behavior-preserving refactor: the post-apply plan-line dedup moves from an inline heredoc in `_run_post_apply_pipeline` to `dedup-plan-lines.py`, wired through `$DEDUP_PLAN_LINES_PY` beside the existing `DESIGN_DRIVER_SH` / `CHECK_PLAN_SIZE_SH` / `INVOKE_PLAN_VALIDATOR_SH` siblings. **Plan fidelity (structure lens)** — All planned structural obligations appear met:
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_20: **Python helper** — `dedup-plan-lines.py` only opens `sys.argv[1]`/`[2]`, does line-oriented text processing, and prints an integer count. No `subprocess`, `eval`, deserialization, or network I/O. Failure paths still fail closed (`LOOP_REASON=dedup-python-failed`, backup restore).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Python helper** — `dedup-plan-lines.py` only opens `sys.argv[1]`/`[2]`, does line-oriented text processing, and prints an integer count. No `subprocess`, `eval`, deserialization, or network I/O. Failure paths still fail closed (`LOOP_REASON=dedup-python-failed`, backup restore).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_21: **stdout handling** — Non-numeric / multi-line stdout still fails the `^[0-9]+$` guard (same as before).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **stdout handling** — Non-numeric / multi-line stdout still fails the `^[0-9]+$` guard (same as before).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_22: **Tests** — The new `PATH` `python3` wrapper and `REAL_PYTHON` capture are harness-only; basename gating targets `dedup-plan-lines.py` only and does not widen production attack surface.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Tests** — The new `PATH` `python3` wrapper and `REAL_PYTHON` capture are harness-only; basename gating targets `dedup-plan-lines.py` only and does not widen production attack surface.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_23: **Docs / lint** — `agent-lint.toml` exclusions and `relevant-checks.sh` routing are CI/maintainability only, not runtime auth or secrets.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Docs / lint** — `agent-lint.toml` exclusions and `relevant-checks.sh` routing are CI/maintainability only, not runtime auth or secrets. `DESIGN_TMPDIR` validation (`larch_design_tmpdir_validate`, `pwd -P`) and the existing PLUGIN_ROOT trust model are unchanged; moving dedup from an inline heredoc to a sibling script does not introduce a new class of injection or privilege escalation beyond “trust the plugin tree,” which already applied to other `$PLUGIN_ROOT/...` helpers. ---
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_29

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_29: `1e40f8015` — Extract plan-line dedup helper from plan-review-loop.sh  
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `1e40f8015` — Extract plan-line dedup helper from plan-review-loop.sh
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_3: Verbatim Python extraction with shebang + docstring only
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: - Verbatim Python extraction with shebang + docstring only
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_30

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_30: `bd17afd36` — chore(larch-logs): flush implement run (excluded from scope per reviewer rules)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `bd17afd36` — chore(larch-logs): flush implement run (excluded from scope per reviewer rules) Walked all planned deliverables against the diff. The refactor matches the implementation plan for issue #3166. | Plan requirement | Status | |------------------|--------| | `dedup-plan-lines.py` — verbatim logic, shebang, docstring, CLI `<src> <dest>` → stdout count | Done | | `dedup-plan-lines.md` — sibling contract, CLI, caller, invariants, fence divergence, harness | Done | | `plan-review-loop.sh` — `$DEDUP_PLAN_LINES_PY` (plain `$PLUGIN_ROOT`), single-line call, unchanged failure handling | Done | | `test-plan-review-loop.sh` — 4 eval-isolation exports (outer + inner), non-numeric stub without stdin, new `run_loop` integration test | Done | | `relevant-checks.sh` — pipe-alternate `.py` and `.md` | Done | | `plan-review.md` — helper pointer, Gate B + normalization preserved | Done | | `agent-lint.toml` — dead-script + sibling-doc exclusions with caller comment | Done | | `parse-plan-commands.md` — fenced-section cross-reference | Done | Sub-tasks from the original feature description are addressed: (1) embedded Python removed from awk-extractable shell, (2) fence-model divergence documented in `dedup-plan-lines.md` with cross-ref, (3) `dedup-python-failed` integration coverage added (distinct from `out_ddd` findings-dedup).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_4: Single-line caller in `plan-review-loop.sh`; failure handling unchanged
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: - Single-line caller in `plan-review-loop.sh`; failure handling unchanged
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_5: Sibling contract `dedup-plan-lines.md` with fence-model divergence
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: - Sibling contract `dedup-plan-lines.md` with fence-model divergence
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_6: Four eval-isolation sites export `DEDUP_PLAN_LINES_PY` (outer + inner `bash -c`)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: - Four eval-isolation sites export `DEDUP_PLAN_LINES_PY` (outer + inner `bash -c`)
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_7: New `run_loop` integration test (`DDPL`) with basename-scoped PYWRAP and `REAL_PYTHON` capture
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: - New `run_loop` integration test (`DDPL`) with basename-scoped PYWRAP and `REAL_PYTHON` capture
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_8: `relevant-checks.sh`, `plan-review.md`, `parse-plan-commands.md`, and focused `agent-lint.toml` exclusions
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: - `relevant-checks.sh`, `plan-review.md`, `parse-plan-commands.md`, and focused `agent-lint.toml` exclusions The extraction removes ~80 lines of embedded Python from the awk-extracted function range, which was the main maintainability hazard (column-zero `}` truncating `awk "/^_run_post_apply_pipeline\(\)/,/^}$/"` tests). Documentation correctly distinguishes fence-aware heading/Constraints state from duplicate-line collapse and does not claim fenced duplicates are protected.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

