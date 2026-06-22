### OOS_2: correctness: python/lint_consecutive_bash.py:25-133
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] _is_example_fence uses broad EXAMPLE_RE on preceding context, excluding fences when prose contains whole words wrong/correct/example, wider than the plan's WRONG/CORRECT carve-out. Adjacent bash fences after prose like Use the correct launcher: within three lines are never paired because the first fence is dropped from candidates. Narrow example detection to explicit WRONG/CORRECT labels and info-string example markers; add regression test.
- **Suggested revision**: Address the concern above.


### OOS_3: correctness: python/lint_consecutive_bash.py:105-111
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Unclosed fence openers extend to EOF instead of failing closed, absorbing later bash fences into one block. A missing closing fence before a second bash block prevents the linter from seeing two candidates and reports no violation. Treat unclosed openers as parse errors or skip with diagnostic; add pytest for unclosed opener plus following bash fence.
- **Suggested revision**: Address the concern above.


### OOS_4: **correctness** `python/lint_consecutive_bash.py:128-133` — **Important**: `_is_example_fence` skips any Bash fence when the preceding three lines or first body comment contain `example`, `wrong`, or `correct`. A real orchestrator step introduced with “Example:” can therefore hide an adjacent Bash pair entirely, so the new lint returns clean for the exact smell it is meant to catch. **Suggested fix:** Limit context/body-comment example suppression to explicit `WRONG` / `CORRECT` labels, or require a stricter illustrative-example marker. Add a negative test where “For example:” precedes two adjacent real Bash fences and must fail.
- **Reviewer**: codex-generic-output.txt
- **Concern**: - **correctness** `python/lint_consecutive_bash.py:128-133` — **Important**: `_is_example_fence` skips any Bash fence when the preceding three lines or first body comment contain `example`, `wrong`, or `correct`. A real orchestrator step introduced with “Example:” can therefore hide an adjacent Bash pair entirely, so the new lint returns clean for the exact smell it is meant to catch. **Suggested fix:** Limit context/body-comment example suppression to explicit `WRONG` / `CORRECT` labels, or require a stricter illustrative-example marker. Add a negative test where “For example:” precedes two adjacent real Bash fences and must fail.
- **Suggested revision**: Address the concern above.


### OOS_5: **correctness** `python/lint_consecutive_bash.py:99-111` — When a fence opener has no matching closer, `_parse_fences` treats EOF as the close line and advances past the rest of the file without emitting a diagnostic. Any later ` ```bash ` openers inside that swallowed span are never parsed as separate fences, so real consecutive-Bash violations after a typo’d or truncated fence are silently missed. **Suggested fix:** On the `while cursor < len(lines)` `else` branch, emit a parse warning or `LintError` for the unclosed opener (include `start_line`), and do not treat the remainder of the file as a single closed fence; add a pytest case with a missing closer followed by a second valid bash fence.
- **Reviewer**: dyn-dyn-fence-parser-output.txt
- **Concern**: - **correctness** `python/lint_consecutive_bash.py:99-111` — When a fence opener has no matching closer, `_parse_fences` treats EOF as the close line and advances past the rest of the file without emitting a diagnostic. Any later ` ```bash ` openers inside that swallowed span are never parsed as separate fences, so real consecutive-Bash violations after a typo’d or truncated fence are silently missed. **Suggested fix:** On the `while cursor < len(lines)` `else` branch, emit a parse warning or `LintError` for the unclosed opener (include `start_line`), and do not treat the remainder of the file as a single closed fence; add a pytest case with a missing closer followed by a second valid bash fence.
- **Suggested revision**: Address the concern above.


### OOS_6: **correctness** `python/lint_consecutive_bash.py:25,128-133` — `_is_example_fence` excludes a fence from all adjacency checks when `\bexample\b`, `\bcorrect\b`, or `\bwrong\b` appears in the info string, the three preceding lines, or the first body comment. That is broader than the documented WRONG/CORRECT teaching-block carve-out and can drop real adjacent `bash` pairs when ordinary prose uses those words nearby (for example “correct behavior” or “for example”). **Suggested fix:** Limit example detection to explicit WRONG/CORRECT labeling (including labels in the gap, as round 1 already fixed) instead of any occurrence of `example`/`correct`/`wrong` in preceding context.
- **Reviewer**: dyn-dyn-lint-wiring-output.txt
- **Concern**: - **correctness** `python/lint_consecutive_bash.py:25,128-133` — `_is_example_fence` excludes a fence from all adjacency checks when `\bexample\b`, `\bcorrect\b`, or `\bwrong\b` appears in the info string, the three preceding lines, or the first body comment. That is broader than the documented WRONG/CORRECT teaching-block carve-out and can drop real adjacent `bash` pairs when ordinary prose uses those words nearby (for example “correct behavior” or “for example”). **Suggested fix:** Limit example detection to explicit WRONG/CORRECT labeling (including labels in the gap, as round 1 already fixed) instead of any occurrence of `example`/`correct`/`wrong` in preceding context.
- **Suggested revision**: Address the concern above.


### OOS_7: **correctness** `python/lint_consecutive_bash.py:105-107` — When a fence opener has no matching closer, the parser absorbs through EOF and advances the cursor to the file end without reporting a parse error. Any later ` ```bash ` openers inside that swallowed region are never parsed as separate fences, so consecutive violations later in the same file can be missed silently. **Suggested fix:** Fail closed on unclosed fences (or at minimum skip adjacency checks for the malformed fence and emit a parse diagnostic), and add a pytest with an unclosed opener followed by a second valid `bash` fence.
- **Reviewer**: dyn-dyn-lint-wiring-output.txt
- **Concern**: - **correctness** `python/lint_consecutive_bash.py:105-107` — When a fence opener has no matching closer, the parser absorbs through EOF and advances the cursor to the file end without reporting a parse error. Any later ` ```bash ` openers inside that swallowed region are never parsed as separate fences, so consecutive violations later in the same file can be missed silently. **Suggested fix:** Fail closed on unclosed fences (or at minimum skip adjacency checks for the malformed fence and emit a parse diagnostic), and add a pytest with an unclosed opener followed by a second valid `bash` fence.
- **Suggested revision**: Address the concern above.


