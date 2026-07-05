### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-bare-grep-probe.sh:435-437
- **Concern**: Multi-candidate loop must keep scanning after segments with no grep-family command. Scenario: The plan only says to restart after a candidate is evaluated. Today `if (!candidate) next` skips the whole line. Lines like `false || rg PATTERN ../root` or `true; rg PATTERN ../root` have no grep-family at the first segment start, so a naive port can still miss every RHS probe and leave gap 1 unfixed.
- **Proposed resolution**: Specify loop control explicitly: when `advance_to_command_start` finds no grep-family token, still search forward for the next segment boundary (`||`, `&&`, `;`, `|`, `|&`) and continue; never `next` the line solely because the current segment has no candidate.

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-bare-grep-probe.sh:417-455
- **Concern**: Pipe-fed stdin detection must treat `|&` like `|`. Scenario: The plan says pipe-fed means preceded by unquoted `|` only, but the harness keeps `cat file |& rg PATTERN` allowed. Multi-segment scanning will finally evaluate post-pipe `rg` candidates; without `|&` in the pipe-fed predicate they get the no-path rule and false-positive.
- **Proposed resolution**: Add `|&` to the pipe-fed predecessor check (and document it beside `|` in the contract and harness bullets).

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-bare-grep-probe.sh:226-244
- **Concern**: Rewrite is_bare_wrapper_grep for segment-start peeling, not line-start only. Scenario: The planned test false || grep PATTERN file.txt must flag bare-wrapper on the RHS, but is_bare_wrapper_grep() only matches grep at line start (assignments, if, {). A multi-candidate loop alone still returns 0 for RHS bare grep.
- **Proposed resolution**: Make is_bare_wrapper_grep take the segment boundary index from advance_to_command_start and treat grep as bare when it is the first command word after that peel (still exempt command grep and allowed pipe-fed forms).

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-bare-grep-probe.sh:273-279
- **Concern**: Pipe-fed stdin detection must include |& as well as |. Scenario: The plan allows cat file |& rg PATTERN but pipe-fed tracking only names unquoted |. Treating only | as pipe-fed can false-flag no-path on allowed |& producers or miss the pipe-fed bare-grep exemption.
- **Proposed resolution**: When deciding a candidate is pipe-fed, treat the immediately preceding unquoted token as | or |&; document the same rule in scripts/lint-bare-grep-probe.md.

### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-bare-grep-probe.sh
- **Concern**: The multi-candidate loop must advance at every segment boundary, not only after a grep-family candidate is evaluated. Scenario: The plan says to scan for the next separator after each candidate is evaluated. On lines like `echo ok; rg PATTERN ../root` or `false || echo ok && rg PATTERN ../root`, the leading segment has no grep-family command. If the loop waits for a evaluated candidate before advancing, it never reaches the later unsafe probe and gap 3 stays open
- **Proposed resolution**: Define the loop as: from cursor `pos`, call `advance_to_command_start(pos)`; if grep-family, run the per-candidate checks; then always find the next unquoted segment separator and set `pos` to the token after it, whether or not the current segment produced a candidate. Add a regression such as `echo ok; rg PATTERN ../root`

### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/test-lint-bare-grep-probe.sh
- **Concern**: Background `&` segment boundaries lack an explicit regression case. Scenario: The approach adds `&` as a same-line segment start, but the planned test list covers `||`, `&&`, `;`, pipelines, and `|&` only. A bad `&` restart can leave `foo & rg PATTERN ../root` unscanned with no harness signal
- **Proposed resolution**: Add one allowed/flagged pair, e.g. flag `sleep 1 & rg PATTERN ../root` and keep a safe no-path `sleep 1 & true` or similar non-grep control if needed ### 1. [correctness] Segment cursor must advance without a grep-family candidate (`scripts/lint-bare-grep-probe.sh`) The plan’s loop text ties separator scanning to “after each candidate is evaluated.” Gap 3 also needs later segments when earlier tokens are ordinary commands (`echo ok; rg …`, `false || echo ok && rg …`). If advancement waits for a evaluated grep-family candidate, those lines stay clean. **Suggested revision:** Advance at every segment boundary regardless of whether the current segment matched grep-family; add a regression such as `echo ok; rg PATTERN ../root`. ### 2. [risk-integration] Add a `&` boundary regression (`scripts/test-lint-bare-grep-probe.sh`) The approach treats `&` as a segment boundary (covering the previously rejected background-gap). The planned fixtures list `||`, `&&`, `;`, pipelines, and `|&`, but not a standalone `&` separator. **Suggested revision:** Add one case like `sleep 1 & rg PATTERN ../root` so the new boundary is exercised in CI.

### FINDING_9:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:12,28,44
- **Concern**: Prior accepted pattern-file fix remains incomplete for attached short `-fVALUE` operands. Scenario: The plan checks split `-f VALUE` and long `--file=VALUE`, but `command grep -f../patterns target.txt` and `rg -f../patterns target/` are valid pattern-file forms with hidden parent ascent and would still bypass the required `-f` parent-ascent guard.
- **Proposed resolution**: Treat attached short `-fVALUE` as a consumed pattern-file value in the shared walker, run `has_parent_ascent_segment()` on `VALUE`, and add one regression with a follow-on safe search path.

### FINDING_11:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-bare-grep-probe.sh:226-244
- **Concern**: Multi-candidate loop must skip non-grep-family segment starts without ending the line scan. Scenario: The plan only says to advance after a candidate is evaluated. It does not say what to do when advance_to_command_start lands on a non-grep token (for example echo in echo done ; rg PATTERN ../root). An implementer can still exit the line after candidate_index-style failure and miss later semicolon or logical-and grep-family probes that the new regression list requires.
- **Proposed resolution**: Add an outer loop rule: from each boundary restart, if advance_to_command_start does not yield a grep-family command, scan forward to the next listed separator and repeat until a grep-family candidate is found or the line is exhausted; only a safe evaluated candidate may continue scanning.

### FINDING_12:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-bare-grep-probe.sh:226-244
- **Concern**: is_bare_wrapper_grep must anchor to the segment start, not line start. Scenario: The plan mandates flagging false || grep PATTERN file.txt and calls bare-wrapper reporting segment-relative, but the only described helper change is advance_to_command_start. Today is_bare_wrapper_grep compares idx only against skip_assignments(1) and line-leading if or brace positions, so a grep token after || or ; on the RHS will not be treated as bare even when the multi-candidate loop finds it.
- **Proposed resolution**: Rebase is_bare_wrapper_grep (or pass segment_start) so bare-wrapper detection uses the same segment-local prefix peeling as advance_to_command_start, with the existing pipe-fed grep carve-out.
