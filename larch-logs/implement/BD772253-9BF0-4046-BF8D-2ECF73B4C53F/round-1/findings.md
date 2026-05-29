### FINDING_1: `1e40f8015` — Extract plan-line dedup helper from plan-review-loop.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: - `1e40f8015` — Extract plan-line dedup helper from plan-review-loop.sh
- **Suggested revision**: Address the concern above.

### FINDING_2: `bd17afd36` — chore(larch-logs): flush implement run BD772253-…
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: - `bd17afd36` — chore(larch-logs): flush implement run BD772253-… ## Review summary This branch implements issue #3166 as a behavior-preserving refactor: the post-apply plan-line dedup moves from an inline heredoc in `_run_post_apply_pipeline` to `dedup-plan-lines.py`, wired through `$DEDUP_PLAN_LINES_PY` beside the existing `DESIGN_DRIVER_SH` / `CHECK_PLAN_SIZE_SH` / `INVOKE_PLAN_VALIDATOR_SH` siblings. **Plan fidelity (structure lens)** — All planned structural obligations appear met:
- **Suggested revision**: Address the concern above.

### FINDING_3: Verbatim Python extraction with shebang + docstring only
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: - Verbatim Python extraction with shebang + docstring only
- **Suggested revision**: Address the concern above.

### FINDING_4: Single-line caller in `plan-review-loop.sh`; failure handling unchanged
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: - Single-line caller in `plan-review-loop.sh`; failure handling unchanged
- **Suggested revision**: Address the concern above.

### FINDING_5: Sibling contract `dedup-plan-lines.md` with fence-model divergence
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: - Sibling contract `dedup-plan-lines.md` with fence-model divergence
- **Suggested revision**: Address the concern above.

### FINDING_6: Four eval-isolation sites export `DEDUP_PLAN_LINES_PY` (outer + inner `bash -c`)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: - Four eval-isolation sites export `DEDUP_PLAN_LINES_PY` (outer + inner `bash -c`)
- **Suggested revision**: Address the concern above.

### FINDING_7: New `run_loop` integration test (`DDPL`) with basename-scoped PYWRAP and `REAL_PYTHON` capture
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: - New `run_loop` integration test (`DDPL`) with basename-scoped PYWRAP and `REAL_PYTHON` capture
- **Suggested revision**: Address the concern above.

### FINDING_8: `relevant-checks.sh`, `plan-review.md`, `parse-plan-commands.md`, and focused `agent-lint.toml` exclusions
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: - `relevant-checks.sh`, `plan-review.md`, `parse-plan-commands.md`, and focused `agent-lint.toml` exclusions The extraction removes ~80 lines of embedded Python from the awk-extracted function range, which was the main maintainability hazard (column-zero `}` truncating `awk "/^_run_post_apply_pipeline\(\)/,/^}$/"` tests). Documentation correctly distinguishes fence-aware heading/Constraints state from duplicate-line collapse and does not claim fenced duplicates are protected.
- **Suggested revision**: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] code-quality
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 1. **code-quality** `skills/design/scripts/plan-review-loop.sh:207-993` — The loop still embeds several other Python heredocs (findings split, parse-collect-inline, `.plan-review-loop-dedup.py`, etc.). Only `_run_post_apply_pipeline` is awk-extracted in tests today; similar extraction could reduce future bash/Python coupling elsewhere. **Why out of scope:** pre-existing surface, not introduced or worsened by this diff (this PR reduces one heredoc).
- **Suggested revision**: Address the concern above.

### FINDING_10: `1e40f8015` — Extract plan-line dedup helper from `plan-review-loop.sh`
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - `1e40f8015` — Extract plan-line dedup helper from `plan-review-loop.sh`
- **Suggested revision**: Address the concern above.

### FINDING_11: `bd17afd36` — `chore(larch-logs):` implement run flush (out of scope for correctness review)
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - `bd17afd36` — `chore(larch-logs):` implement run flush (out of scope for correctness review) **Plan vs diff:** The refactor matches the plan: verbatim Python extraction, `$DEDUP_PLAN_LINES_PY` wiring (plain `$PLUGIN_ROOT` form), unchanged failure handling (`emit-plan-failed` / `dedup-python-failed`), docs and `relevant-checks.sh` routing, `agent-lint.toml` exclusions, four eval-isolation exports, non-numeric stub fix, and a `run_loop` integration test distinct from `out_ddd`. **Correctness checks:**
- **Suggested revision**: Address the concern above.

### FINDING_12: Extracted dedup body is byte-identical to the former heredoc (only shebang/docstring/imports differ).
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - Extracted dedup body is byte-identical to the former heredoc (only shebang/docstring/imports differ).
- **Suggested revision**: Address the concern above.

### FINDING_13: On dedup failure, `_run_post_apply_pipeline` still sets `LOOP_STATUS=emit-plan-failed` and `LOOP_REASON=dedup-python-failed`; `_snapshot_terminal_exit_preserving_status` preserves those and `emit_loop_kvs` maps `LOOP_REASON` → `REASON=` (lines 134–146, 368–375, 1298–1299 in `plan-review-loop.sh`).
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - On dedup failure, `_run_post_apply_pipeline` still sets `LOOP_STATUS=emit-plan-failed` and `LOOP_REASON=dedup-python-failed`; `_snapshot_terminal_exit_preserving_status` preserves those and `emit_loop_kvs` maps `LOOP_REASON` → `REASON=` (lines 134–146, 368–375, 1298–1299 in `plan-review-loop.sh`).
- **Suggested revision**: Address the concern above.

### FINDING_14: Integration test scaffolding mirrors the existing emit-plan-failure test (`write_collect one`, revise OK); PYWRAP matches only `dedup-plan-lines.py` via basename and uses pre-captured `REAL_PYTHON` to avoid recursion.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - Integration test scaffolding mirrors the existing emit-plan-failure test (`write_collect one`, revise OK); PYWRAP matches only `dedup-plan-lines.py` via basename and uses pre-captured `REAL_PYTHON` to avoid recursion.
- **Suggested revision**: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] **`skills/design/scripts/plan-review-loop.sh`** — Other inline Python heredocs (`plan_slot_human_label`, `plan_review_slot_for_reviewer`, findings dedup, etc.) still pose the same awk `^}$` truncation hazard if column-zero `}` appears in embedded Python; this PR only removes that risk from `_run_post_apply_pipeline`.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - **`skills/design/scripts/plan-review-loop.sh`** — Other inline Python heredocs (`plan_slot_human_label`, `plan_review_slot_for_reviewer`, findings dedup, etc.) still pose the same awk `^}$` truncation hazard if column-zero `}` appears in embedded Python; this PR only removes that risk from `_run_post_apply_pipeline`.
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: skills/design/scripts/test-plan-review-loop.sh:1533-1564
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] New dedup-python-failed run_loop test does not assert plan backup restore because revise stub leaves plan.txt unchanged Post-apply backup is byte-identical to the current plan so cp restore on dedup failure is a no-op in integration; restore regressions only fail in awk-isolated unit tests Mutate plan.txt in the revise stub (as in mr-emit-plan-fail) then cmp plan.txt to the original seed after run_loop exits with dedup-python-failed
- **Suggested revision**: Address the concern above.

### FINDING_17: `1e40f8015` — Extract plan-line dedup helper from plan-review-loop.sh  
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `1e40f8015` — Extract plan-line dedup helper from plan-review-loop.sh
- **Suggested revision**: Address the concern above.

### FINDING_18: `bd17afd36` — chore(larch-logs): flush implement run BD772253-9BF0-4046-BF8D-2ECF73B4C53F  
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `bd17afd36` — chore(larch-logs): flush implement run BD772253-9BF0-4046-BF8D-2ECF73B4C53F   ---
- **Suggested revision**: Address the concern above.

### FINDING_19: **Shell invocation** — `python3 "$DEDUP_PLAN_LINES_PY" "$plan_path" "$dedup_tmp"` keeps all three operands quoted; `DEDUP_PLAN_LINES_PY` is assigned from `$PLUGIN_ROOT/...` at script load (same pattern as `DESIGN_DRIVER_SH` / `INVOKE_PLAN_VALIDATOR_SH`), not from untrusted plan text.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Shell invocation** — `python3 "$DEDUP_PLAN_LINES_PY" "$plan_path" "$dedup_tmp"` keeps all three operands quoted; `DEDUP_PLAN_LINES_PY` is assigned from `$PLUGIN_ROOT/...` at script load (same pattern as `DESIGN_DRIVER_SH` / `INVOKE_PLAN_VALIDATOR_SH`), not from untrusted plan text.
- **Suggested revision**: Address the concern above.

### FINDING_20: **Python helper** — `dedup-plan-lines.py` only opens `sys.argv[1]`/`[2]`, does line-oriented text processing, and prints an integer count. No `subprocess`, `eval`, deserialization, or network I/O. Failure paths still fail closed (`LOOP_REASON=dedup-python-failed`, backup restore).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Python helper** — `dedup-plan-lines.py` only opens `sys.argv[1]`/`[2]`, does line-oriented text processing, and prints an integer count. No `subprocess`, `eval`, deserialization, or network I/O. Failure paths still fail closed (`LOOP_REASON=dedup-python-failed`, backup restore).
- **Suggested revision**: Address the concern above.

### FINDING_21: **stdout handling** — Non-numeric / multi-line stdout still fails the `^[0-9]+$` guard (same as before).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **stdout handling** — Non-numeric / multi-line stdout still fails the `^[0-9]+$` guard (same as before).
- **Suggested revision**: Address the concern above.

### FINDING_22: **Tests** — The new `PATH` `python3` wrapper and `REAL_PYTHON` capture are harness-only; basename gating targets `dedup-plan-lines.py` only and does not widen production attack surface.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Tests** — The new `PATH` `python3` wrapper and `REAL_PYTHON` capture are harness-only; basename gating targets `dedup-plan-lines.py` only and does not widen production attack surface.
- **Suggested revision**: Address the concern above.

### FINDING_23: **Docs / lint** — `agent-lint.toml` exclusions and `relevant-checks.sh` routing are CI/maintainability only, not runtime auth or secrets.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Docs / lint** — `agent-lint.toml` exclusions and `relevant-checks.sh` routing are CI/maintainability only, not runtime auth or secrets. `DESIGN_TMPDIR` validation (`larch_design_tmpdir_validate`, `pwd -P`) and the existing PLUGIN_ROOT trust model are unchanged; moving dedup from an inline heredoc to a sibling script does not introduce a new class of injection or privilege escalation beyond “trust the plugin tree,” which already applied to other `$PLUGIN_ROOT/...` helpers. ---
- **Suggested revision**: Address the concern above.

### FINDING_24: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **security** `skills/design/scripts/test-plan-review-loop.sh:1786-1920` — Eval-isolation tests still `eval "$(awk ... _run_post_apply_pipeline ...)"` to extract the function from `plan-review-loop.sh`. That trusts the repo copy of the shell file at test time; not introduced by this PR, but it remains a high-trust test pattern adjacent to the touched harness.
- **Suggested revision**: Address the concern above.

### FINDING_25: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **security** `skills/design/scripts/dedup-plan-lines.py:445-484` — `open(..., errors="replace")` can silently substitute U+FFFD for invalid UTF-8 before `plan.txt` is re-emitted. Integrity/correctness concern for exotic byte sequences, not new command execution risk; same behavior as the removed heredoc.
- **Suggested revision**: Address the concern above.

### FINDING_26: [OUT_OF_SCOPE] architecture: skills/design/scripts/plan-review-loop.sh:493-517,969-975
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Findings dedup fails open while plan-line dedup fails closed. A .plan-review-loop-dedup.py failure degrades the round and the loop can still reach cap-hit; a dedup-plan-lines.py failure terminates with emit-plan-failed. Operators may expect symmetric recovery. No change in this refactor; keep the intentional divergence documented (already improved in dedup-plan-lines.md and the new integration test).
- **Suggested revision**: Address the concern above.

### FINDING_27: [OUT_OF_SCOPE] risk-integration: skills/design/scripts/plan-review-loop.sh:1298-1299
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Terminal post-apply failures exit 0 from _terminal_exit. Scripts wrapping plan-review-loop.sh that only check $? after dedup-python-failed will treat the run as success despite LOOP_STATUS=emit-plan-failed. Document KV-driven status in plan-review reference, or revisit exit codes in a dedicated behavior change.
- **Suggested revision**: Address the concern above.

### FINDING_28: [OUT_OF_SCOPE] risk-integration: skills/design/scripts/plan-review-loop.sh:518-555
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Backup is not restored after successful dedup if a later post-apply step fails. Validator or emit failure leaves a deduped plan.txt while the pre-revise backup is deleted, so the operator cannot roll back to the pre-dedup revise output. Only if full rollback is desired; would require extending failure paths beyond this refactor.
- **Suggested revision**: Address the concern above.

### FINDING_29: `1e40f8015` — Extract plan-line dedup helper from plan-review-loop.sh  
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `1e40f8015` — Extract plan-line dedup helper from plan-review-loop.sh
- **Suggested revision**: Address the concern above.

### FINDING_30: `bd17afd36` — chore(larch-logs): flush implement run (excluded from scope per reviewer rules)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `bd17afd36` — chore(larch-logs): flush implement run (excluded from scope per reviewer rules) Walked all planned deliverables against the diff. The refactor matches the implementation plan for issue #3166. | Plan requirement | Status | |------------------|--------| | `dedup-plan-lines.py` — verbatim logic, shebang, docstring, CLI `<src> <dest>` → stdout count | Done | | `dedup-plan-lines.md` — sibling contract, CLI, caller, invariants, fence divergence, harness | Done | | `plan-review-loop.sh` — `$DEDUP_PLAN_LINES_PY` (plain `$PLUGIN_ROOT`), single-line call, unchanged failure handling | Done | | `test-plan-review-loop.sh` — 4 eval-isolation exports (outer + inner), non-numeric stub without stdin, new `run_loop` integration test | Done | | `relevant-checks.sh` — pipe-alternate `.py` and `.md` | Done | | `plan-review.md` — helper pointer, Gate B + normalization preserved | Done | | `agent-lint.toml` — dead-script + sibling-doc exclusions with caller comment | Done | | `parse-plan-commands.md` — fenced-section cross-reference | Done | Sub-tasks from the original feature description are addressed: (1) embedded Python removed from awk-extractable shell, (2) fence-model divergence documented in `dedup-plan-lines.md` with cross-ref, (3) `dedup-python-failed` integration coverage added (distinct from `out_ddd` findings-dedup).
- **Suggested revision**: Address the concern above.

