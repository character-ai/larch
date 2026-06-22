### OOS_1: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 1. **correctness** `python/oos_filer.py:559-561` — `_body_file_for_item` reads `ITEM_{N}_BODY_FILE` with no tmpdir containment check, so a symlink path outside `$IMPLEMENT_TMPDIR` could be read during issue filing. This predates the branch; the rollup only added stable-ID mapper coverage tests, not hardening here. **Suggested fix:** Resolve and verify `raw_path` stays under `tmpdir` (same pattern as `cleanup_implement_logs._within_run_dir`) before `read_text`.
- **Suggested revision**: Address the concern above.


### OOS_2: correctness: python/lint_consecutive_bash.py:82-100
- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: [important] Closer regex requires exact opener indentation, contradicting CommonMark-style 0 to 3 space closer handling. A valid Markdown pair with an unindented opener, a three-space-indented closer, then another bash fence is parsed as one unclosed fence, so no adjacent-pair violation is emitted. Accept any 0 to 3 leading spaces on closing fences while requiring backticks and sufficient marker length, and add a regression for mixed opener/closer indentation.
- **Suggested revision**: Address the concern above.


### OOS_3: correctness: python/lint_consecutive_bash.py:128-133
- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: [important] Nearby prose containing example drops a Bash fence from candidate detection even when it is not an explicit example label. “For example, prepare env:” before two adjacent Bash fences causes the first fence to be skipped and the violation to disappear. Only treat example in the info string as an example marker; for surrounding prose or first body comments require explicit WRONG or CORRECT labels.
- **Suggested revision**: Address the concern above.


### OOS_4: correctness: python/lint_consecutive_bash.py:186-198
- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: [important] WRONG/CORRECT carve-out scans arbitrary fence bodies, so normal shell text can suppress violations. A command like if command; then echo correct; else echo wrong; fi followed by another Bash fence is incorrectly treated as an example pair. Restrict WRONG/CORRECT detection to explicit labels in nearby prose or first body comments, not arbitrary shell bodies.
- **Suggested revision**: Address the concern above.


### OOS_5: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 2. **correctness** `python/oos_filer.py:149-169` — `_stable_ids_by_combined_item` assumes count-reducing combine maps the first `combined_count - 1` outputs 1:1 and rolls the rest into the tail; when `combined_count > len(blocks)` (Codex emits more blocks than sources), tail mapping can be empty and stable IDs may be dropped on retry. **Suggested fix:** Add an explicit branch that assigns all `source_ids` to the last output block when `combined_count > len(blocks)`, or fail closed. (Production code unchanged on this branch; new test only pins the count-reducing path.)
- **Suggested revision**: Address the concern above.


### OOS_6: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 1. **risk-integration** `python/oos_filer.py:184-188` — The rollup cited “oos_filer … symlink-escape gaps,” but this branch adds symlink regression coverage only for `cleanup_implement_logs.delete_identical_aggregator`, not for `oos_filer._working_batch`, which still reads accepted OOS inputs with `path.is_file()` and no symlink rejection. **Suggested fix:** If that gap is still considered real, add `_within_run_dir` or `is_symlink()` guards on accepted-input reads in `oos_filer.py` plus targeted tests; out of scope here because `oos_filer.py` is unchanged.
- **Suggested revision**: Address the concern above.


