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

### FINDING_4: Add an explicit regression for `&` segment restarts
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: latent
- **Concern**: The planned regression coverage mentions `||`, `&&`, `;`, pipelines, and `|&`, but not a standalone `&` boundary, so a bad background-separator restart could still go untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add one allowed/flagged pair, e.g. flag `sleep 1 & rg PATTERN ../root` and keep a safe no-path `sleep 1 & true` or similar non-grep control if needed

### FINDING_5: Attached short `-fVALUE` operands still need parent-ascent checks
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: The parent-ascent guard covers split and long-form pattern-file operands, but attached short `-fVALUE` forms can still hide a `../` path in the value and bypass the check.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Treat attached short `-fVALUE` as a consumed pattern-file value in the shared walker, run `has_parent_ascent_segment()` on `VALUE`, and add one regression with a follow-on safe search path.

### FINDING_6:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/lint-bare-grep-probe.sh:252-256
- **Concern**: [SCOPE-REDUCTION] Drop bare `&` as a multi-candidate segment boundary. Scenario: Gap 3 covers later pipeline and semicolon commands only; background `&` was rejected in round 1 (FINDING_3). Wiring `&` as a restart boundary expands scope beyond gaps 1-5 with no mandated regression and little orchestrator-fence value.
- **Proposed resolution**: Limit segment restarts to `||`, `&&`, `;`, `|`, and `|&`; leave post-background commands as the documented limitation unless a gap-mandated test is added later.

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: architecture
- **Location**: scripts/lint-bare-grep-probe.sh:252-256
- **Concern**: [SCOPE-REDUCTION] Drop background & from multi-candidate segment boundaries. Scenario: Gaps 1-5 cover ||, &&, ;, and pipelines; round 1 rejected & as a required boundary and the test plan lists no & fixture. Scanning bare & adds tokenizer and restart complexity for rare orchestrator-fence shapes.
- **Proposed resolution**: Limit segment restarts to ||, &&, ;, |, and |& unless a concrete in-repo fence needs background &; drop & from boundary lists and docs if not required. ### 1. correctness — `scripts/lint-bare-grep-probe.sh:226-244` The plan requires `false || grep PATTERN file.txt` to flag bare-wrapper on the RHS, but `is_bare_wrapper_grep()` only recognizes grep at **line** start (after assignments, `if`, or `{`). A multi-candidate loop without rewriting this helper still returns 0 for RHS bare `grep`. **Suggested revision:** Pass each segment’s `advance_to_command_start` index into `is_bare_wrapper_grep` and treat `grep` as bare when it is the first command word after that peel (still exempt `command grep` and allowed pipe-fed forms). ### 2. correctness — `scripts/lint-bare-grep-probe.sh:273-279` The plan allows `cat file |& rg PATTERN`, but pipe-fed tracking text only names unquoted `|`. `|&` is a separate tokenizer token; checking only `|` can false-flag allowed `|&` producers or mishandle the pipe-fed bare-grep carve-out. **Suggested revision:** Treat the immediately preceding unquoted token as `|` **or** `|&` for pipe-fed stdin; mirror that in `scripts/lint-bare-grep-probe.md`. ### 3. architecture — `scripts/lint-bare-grep-probe.sh:252-256` **[SCOPE-REDUCTION]** Gaps 1–5 target `||`, `&&`, `;`, and pipelines. Round 1 rejected `&` as a required boundary, and the test plan has no `&` fixture. Scanning bare `&` adds boundary and restart logic for uncommon fence shapes. **Suggested revision:** Limit segment restarts to `||`, `&&`, `;`, `|`, and `|&` unless a concrete in-repo fence needs background `&`; drop `&` from boundary lists and docs if not required.

### FINDING_8:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:9,24,55
- **Concern**: [SCOPE-REDUCTION] Background `&` scanning over-serves gaps 1-5. Scenario: The feature needs fallback, logical-chain, semicolon, and pipeline segment coverage; starting a new candidate after background `&` was already rejected in the prior round and adds parser surface unrelated to the required fixes.
- **Proposed resolution**: Remove `&` from the new multi-candidate segment boundaries, docs, and any new tests; keep it only as an argv terminator for existing suffix-truncation behavior.

### FINDING_9:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/lint-bare-grep-probe.sh:435-455
- **Concern**: [SCOPE-REDUCTION] Drop background & as a multi-candidate segment boundary. Scenario: Issue gaps 1-5 cover RHS ||, -f/--file, later pipeline or semicolon commands, split grep --include/--exclude, and walker deduplication. None require scanning a later grep-family probe after a same-line background & separator, and round-1 FINDING_3 on that point was rejected. Keeping & in the segment-boundary set adds discovery and contract surface beyond the stated minimum.
- **Proposed resolution**: Limit new segment boundaries to ||, &&, ;, |, and |& only; leave & as an argv terminator inside a segment, matching gap 3 wording and the rejected prior finding. ## Findings ### 1. **correctness** `scripts/lint-bare-grep-probe.sh:226-244` — Multi-candidate loop must skip non-grep-family segment starts The plan describes advancing after each evaluated candidate, but not how to handle segment starts that are not grep-family commands. Lines like `echo done ; rg PATTERN ../root` need the outer loop to keep scanning after `echo` without treating the line as clean. **Suggested revision:** Add an explicit outer-loop rule: when `advance_to_command_start` does not land on grep/rg/ripgrep, jump to the next listed separator and repeat until a candidate is found or the line ends. ### 2. **correctness** `scripts/lint-bare-grep-probe.sh:226-244` — `is_bare_wrapper_grep` must use segment start, not line start The plan requires flagging `false || grep PATTERN file.txt`, but `is_bare_wrapper_grep` today only treats grep as bare when it matches line-leading positions via `skip_assignments(1)`. RHS `grep` tokens would be missed even if the multi-candidate loop finds them. **Suggested revision:** Rebase bare-wrapper detection on the segment-local start index from `advance_to_command_start`, preserving the pipe-fed grep exception. ### 3. **architecture** `scripts/lint-bare-grep-probe.sh` — [SCOPE-REDUCTION] Drop `&` as a segment boundary Gaps 1–5 do not require background-`&` command separation; round-1 FINDING_3 on that point was rejected. Keeping `&` in the boundary set adds complexity beyond the stated scope. **Suggested revision:** Limit segment boundaries to `||`, `&&`, `;`, `|`, and `|&`; keep `&` as an in-segment argv terminator only.
