### FINDING_1: Later boundary scans must restart per segment instead of stopping at the first safe candidate
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Awk Parser Guard
- **Severity**: important
- **Concern**: The multi-segment awk scan still needs segment-local restart and the same wrapper/prefix peeling at each boundary; otherwise later `||`/`;`/pipe-fed candidates can be skipped, safe first segments can terminate the line early, and bare-wrapper or no-path regressions can hide on the RHS.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add explicit violation cases such as `false || rg PATTERN` and `true; rg PATTERN` (no `../`) to the harness contract and `scripts/test-lint-bare-grep-probe.sh`
  - From Cursor-Arch: Add `false || grep PATTERN file.txt` (expect bare-wrapper violation) alongside the planned `|| command grep ... ../root` cases
  - From Cursor-Arch: In pipe-fed lookback, treat unquoted `|&` the same as `|`; add allowed `cat file |& rg PATTERN` and keep violation `rg PATTERN |& cat`
  - From Cursor-Arch: Document and implement per-candidate order: bare wrapper (segment-relative) → parent-ascent (always) → if pipe-fed skip no-path/devnull path checks → else existing devnull then explicit-path logic
  - From Cursor-Innovation: Add candidate_index_at(start_i) (or equivalent) invoked at each segment boundary after || && ; | |& and group openers; reuse command/if/!/{/( skipping relative to that start index only
  - From Cursor-Pragmatic: Reuse today's `candidate_index()` prefix peeling at every boundary-delimited start, not only for the first token on the line. Add harness cases such as `true || if rg -q PATTERN ../python; then echo x; fi`, `true; command rg -n PATTERN ../python`, and `false || ( rg -n PATTERN ../python )`.
  - From Cursor-Requirements: State in the approach and `scripts/lint-bare-grep-probe.sh` section that only bare-wrapper, parent-ascent, and no-path violations short-circuit the line; pipe-fed no-path allowance, `< /dev/null`, and explicit-path passes must fall through to the next grep-family candidate on the same line
  - From Cursor-dyn-Awk Parser Guard: Pass each candidate its segment-start index into `is_bare_wrapper_grep()` (or equivalent) and compare `idx` only against skips from that boundary: assignments, optional leading `if`/`!`, `(`, `{`, then `command`.
  - From Cursor-dyn-Awk Parser Guard: Define one `advance_to_command_start(i)` used for the first candidate and every post-boundary restart; reuse it in the multi-candidate iterator before testing `is_grep_family`.


### FINDING_2: Split include/exclude fixtures must exercise grep, not ripgrep
- **Reviewer(s)**: Cursor-Arch, Cursor-dyn-Awk Parser Guard
- **Severity**: important
- **Concern**: Gap 4 is a grep option-parsing bug, so the tests need real `grep` split-value cases instead of dead `rg --include` / `rg --exclude` shapes that can pass without exercising the parser.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: State in the harness contract that split `--include` / `--exclude` fixtures use `grep`; add violation/allow cases with `grep --include VALUE` and `grep --exclude VALUE`
  - From Cursor-dyn-Awk Parser Guard: Keep `--include`/`--exclude`/`--exclude-dir` value consumption in the grep branch only; add an explicit regression `grep --include ../dir PATTERN` (no path) to the test list


### FINDING_4: Pattern-file operands need ascent checks on the consumed value
- **Reviewer(s)**: Cursor-Innovation, Cursor-dyn-Awk Parser Guard
- **Severity**: important
- **Concern**: The `-f` / `--file` path guard still needs to inspect the option value itself, including split and equals forms, and the test list needs a no-follow-on-path regression so a pure pattern-file probe cannot evade the parent-ascent check.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In the shared argv walker, when base is -f or --file (split or equals), run has_parent_ascent_segment() on the option value before continue; leave -e / --regexp values unchecked
  - From Cursor-Innovation: Add assert_fence_line_violation cases for rg -f ../patterns, rg --file=../patterns, and grep -f ../list with no later path operand
  - From Cursor-dyn-Awk Parser Guard: Shared argv walker must parent-ascent-check -f/--file operand values, including equals forms. Scenario: Gap 2 is -f/--file evasion. Today pattern options consume a split value or keep an equals value without calling has_parent_ascent_segment on that operand. Plan lists rg -f ../patterns and equals-form tests but the refactor bullet only says "share argv walking," not that ascent runs on pattern-file option values during option scan. An implementer could still only scan post-pattern path operands and leave rg -f=../patterns or rg --file=../patterns allowed.
  - From Cursor-dyn-Awk Parser Guard: In the shared walker option branch, when option_base is -f or --file, test the split next token or the substring after = with has_parent_ascent_segment before continuing; keep -e/--regexp values pattern-only.


### FINDING_1: Segment cursor must advance past non-grep segments
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The multi-candidate loop can still stop scanning after ordinary commands that are not grep-family, which would leave later `||`, `;`, or pipeline-separated probes unchecked.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Specify loop control explicitly: when `advance_to_command_start` finds no grep-family token, still search forward for the next segment boundary (`||`, `&&`, `;`, `|`, `|&`) and continue; never `next` the line solely because the current segment has no candidate.
  - From Cursor-Pragmatic: Define the loop as: from cursor `pos`, call `advance_to_command_start(pos)`; if grep-family, run the per-candidate checks; then always find the next unquoted segment separator and set `pos` to the token after it, whether or not the current segment produced a candidate. Add a regression such as `echo ok; rg PATTERN ../root`
  - From Cursor-Requirements: Add an outer loop rule: from each boundary restart, if advance_to_command_start does not yield a grep-family command, scan forward to the next listed separator and repeat until a grep-family candidate is found or the line is exhausted; only a safe evaluated candidate may continue scanning.


### FINDING_2: Pipe-fed stdin detection must treat `|&` like `|`
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: important
- **Concern**: The pipe-fed predicate appears to recognize only `|`, so `|&` producers could be misclassified and either false-positive on allowed inputs or miss the intended pipe-fed exemption.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `|&` to the pipe-fed predecessor check (and document it beside `|` in the contract and harness bullets).
  - From Cursor-Innovation: When deciding a candidate is pipe-fed, treat the immediately preceding unquoted token as `|` or `|&`; document the same rule in `scripts/lint-bare-grep-probe.md`.


### FINDING_3: `is_bare_wrapper_grep` must anchor to the segment start
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: Bare-wrapper detection is still described as line-start oriented, so a `grep` after `||` or `;` on the right-hand side can evade the bare-wrapper check even if the multi-candidate loop reaches it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Make `is_bare_wrapper_grep` take the segment boundary index from `advance_to_command_start` and treat `grep` as bare when it is the first command word after that peel (still exempt command `grep` and allowed pipe-fed forms).
  - From Cursor-Requirements: Rebase `is_bare_wrapper_grep` (or pass `segment_start`) so bare-wrapper detection uses the same segment-local prefix peeling as `advance_to_command_start`, with the existing pipe-fed grep carve-out.


### FINDING_5: Attached short `-fVALUE` operands still need parent-ascent checks
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: The parent-ascent guard covers split and long-form pattern-file operands, but attached short `-fVALUE` forms can still hide a `../` path in the value and bypass the check.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Treat attached short `-fVALUE` as a consumed pattern-file value in the shared walker, run `has_parent_ascent_segment()` on `VALUE`, and add one regression with a follow-on safe search path.


