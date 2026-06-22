# Review Round 1

- Mode: `diff`
- 3 accepted, 2 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Terminal stall paths skip Step 16/16a rejected-findings and notify side effects
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-stall-routing-output.txt
- **Severity**: important
- **Concern**: Recover-then-report routes terminal (unrecoverable) stalls to Step 18b `final-report step18b` only, bypassing `python/cli.py implement step-16-17` (`python/closeout.py`), which owns rejected-findings replay (`step_16`) and Slack notify (`step_16a`). A Step 5 lint-fix-failed or similar terminal stall after multi-round review with `rejected-findings.md` can tear down without flushing rejected findings to the run log or tracking issue. Before the reorder, stall paths still ran Step 16 side effects; only the final report was premature.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Run slim Step 16/16a (or fold write-rejected into Step 18b) after terminal Step 18a before finalize.
  - From codex-specialist-correctness-output.txt: Route terminal-stall recovery completion through implement step-16-17 before Step 18b teardown, or add an equivalent terminal-stall closeout path that runs Step 16 and Step 16a side effects before final-report step18b emits.
  - From cursor-specialist-edge-cases-output.txt: After terminal Step 18a completes, run Step 16/16a/17 (or invoke write-rejected plus final-report write) before Step 18b finalize; update line 864 to match recover-then-report.
  - From codex-specialist-edge-cases-output.txt: After Step 18a decides the stall is terminal, run python/cli.py implement step-16-17 before teardown, or extend Step 18b to run Step 16/16a side effects before final-report step18b while preserving summary marker dedupe.
  - From codex-specialist-testing-output.txt: Add a terminal-stall closeout path that runs rejected findings and notify after Step 18a terminal classification and before teardown, while keeping final-report chat emission single-shot.
  - From dyn-stall-routing-output.txt: Either (a) run a slim Step 16/16a-only pass after terminal Step 18a and before Step 18b finalize, or (b) fold rejected-findings replay into the Step 18b terminal path (e.g., invoke `step_16` inside `step18b_final_report` when `.step17-emitted` is absent and `STALL_TRACKING` remains active) so terminal and green paths stay symmetric.


### FINDING_3: MAV/coder Step 5 lint-stall path lacks explicit recover-then-report routing
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: After step5-mav lint-fix exhausts repair, the orchestrator records timing via `--record-only` but has no explicit skip to Step 18; it may continue toward Step 6/16 and render a report before Step 18a recovery. Peer stall paths set `STALL_TRACKING=true` and skip to Step 18.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add explicit STALL_TRACKING=true and skip to Step 18 after record-only, matching stall/self-review/resume-handoff paths


### FINDING_6: `_iter_tsv_logical_rows` prematurely splits multiline rows on digit-tab continuations
- **Reviewer(s)**: dyn-tsv-normalization-output.txt
- **Severity**: important
- **Concern**: `_iter_tsv_logical_rows` treats any physical line matching `^\d+\t` as a new data row, even when a prior row is still buffered from an incomplete multiline record. Continuation text that happens to start with digits plus a tab (for example a numbered step like `2\tintroduces a regression\t…` wrapped onto its own line) prematurely yields the buffered row (which then fails `_split_structured_tsv_row` and is dropped) and parses the continuation as a separate row. The pre-refactor parser processed each physical line independently and did not have this cross-line coupling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-tsv-normalization-output.txt: Before starting a new row on `^\d+\t`, require the buffered line to already contain at least seven tab delimiters (a complete prefix through `scenario_or_breakage`), or only treat a line as a row start when the buffer is empty; alternatively, join tab-bearing continuations when the buffer has fewer than seven tabs instead of always using a space separator.


