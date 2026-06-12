### FINDING_1: Mermaid Gantt time fields and units may render broken or misleading charts
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Codex-dyn-mermaid-format
- **Severity**: important
- **Concern**: The planned Mermaid Gantt task wire does not pin the correct time representation for `dateFormat X`. Reviewers flagged either invalid duration/end-field syntax or seconds-versus-milliseconds unit drift. The chart can fail to parse, render empty, or misrepresent reviewer timing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Document and implement `relative_end = relative_start + clamped_duration` and emit `label :taskId, relative_start, relative_end` with plain integers (no `s` suffix); add a harness assertion that at least one task line matches the `:[^,]+, [0-9]+, [0-9]+$` shape
  - From Cursor-Innovation: Emit relative_end = clamped_end - round_start for each task line (label :id, relative_start, relative_end) and drop the trailing s suffix from the template
  - From Cursor-Pragmatic: Emit `relative_end = relative_start + clamped_duration` as the fourth numeric field; drop the `s` suffix
  - From Codex-dyn-mermaid-format: Change the plan to emit normalized start values in milliseconds for Mermaid, for example relative_start_ms = relative_start_s * 1000, and update the doc/test assertions to include at least one nonzero start value so the unit conversion is pinned.


### FINDING_2: Mermaid task ids and labels are not constrained enough for safe parsing
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-dyn-mermaid-format
- **Severity**: important
- **Concern**: The plan does not require deterministic unique Mermaid task ids, and label sanitization may leave Mermaid metacharacters intact. Duplicate ids, basename-derived ids, or unsafe label text can break a whole per-round chart.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Mint per-round ids from a numeric counter or alphanumerics-only slug; keep human text in the label field only
  - From Cursor-Innovation: Extend sanitization to strip or replace mermaid-metacharacters in labels and require unique ascii-safe task ids derived from basename plus index
  - From Cursor-Innovation: Assign deterministic unique ids per rendered bar (for example roundN_idx) while keeping the human label separate
  - From Cursor-Pragmatic: Assign deterministic unique IDs (e.g. `r<round>-t<seq>`) independent of display labels
  - From Cursor-dyn-mermaid-format: Generate ids as short unique tokens (t1..t25 or sanitized [A-Za-z0-9_-]+ without dots). Keep human labels in the task name field only.


### FINDING_3: No-rounds final-summary caller coverage remains out of sync
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-dyn-caller-audit, Codex-dyn-caller-audit
- **Severity**: important
- **Concern**: The renderer contract changes from empty output to `## Review Phase Detail` plus `No review rounds completed.`, but caller harnesses and wrapper coverage still expect the section to be absent or do not cover the new contract. Required tests can fail or miss wrapper regressions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `skills/implement/scripts/test-write-final-report.sh` to Files to modify/create (or an explicit Edit-in-sync bullet) and flip the assertion to expect the new heading and message for self-review / no-round fixtures
  - From Codex-Arch: Add skills/implement/scripts/test-write-final-report.sh to the plan and update those assertions to expect No review rounds completed while preserving the path-mismatch regression by asserting no live round table is rendered
  - From Cursor-Innovation: Update the assertion to expect ## Review Phase Detail and No review rounds completed. and sync skills/implement/scripts/write-final-report.md empty-output contract per render-review-phase-detail.md edit-in-sync
  - From Codex-Innovation: Update only these existing assertions: expect the no-round message where no rounds exist, and keep the path-mismatch regression focused on not rendering the live-dir round as a table row rather than forbidding the whole section
  - From Cursor-dyn-caller-audit: Add ### UPDATED: skills/implement/scripts/test-write-final-report.sh: flip the run-5 assertion to expect the new heading and message (or assert_contains No review rounds completed.)
  - From Codex-dyn-caller-audit: Add explicit plan entries to update test-write-final-report.sh to expect No review rounds completed. and add a small test-render-final-summary.sh fixture with an existing empty plan-review root that asserts the final summary includes the same message


### FINDING_4: Progress-report terminal output can leak raw Mermaid fences
- **Reviewer(s)**: Cursor-Innovation, Codex-dyn-caller-audit
- **Severity**: important
- **Concern**: The plan adds fenced Mermaid output to the shared renderer but misses the progress-report caller. Plain terminal progress output can show raw chart source instead of a readable summary, conflicting with the final-summary-only Gantt scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Either document terminal degradation in render-review-phase-detail.md or add a minimal progress_report.py pass to omit mermaid fences from terminal output while keeping charts in final-summary notes
  - From Codex-dyn-caller-audit: Update _strip_md_for_terminal to drop fenced mermaid blocks and add a python/test_progress_report.py assertion for that case


### FINDING_5: No-rounds message can falsely appear during in-flight rounds
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: If the new no-rounds branch keys only on an empty completed-round list, live progress reports can print `No review rounds completed.` while a `round-N/` directory exists but `round-meta.json` is not written yet.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Gate the new message on zero `round-*/` directories (any numeric round dir), not only an empty `rounds_list`; keep empty output when dirs exist but no completed meta
  - From Cursor-Requirements: Gate the new message on zero round-* directories under --rounds-root; if any round-* dir exists but none have round-meta.json, keep the current empty best-effort output


### FINDING_6: Planned tests can pass with only the first completed round charted
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The proposed assertions cover round 1 only, while the requirement is one timing chart per completed review round. An implementation could omit later completed rounds and still satisfy the planned checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add at least one matching vendor timing row for round 2 and assert a Round 2 timing heading/chart, or assert the planned round-2 no-task note if no vendor rows are intentional


### FINDING_9:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/render-review-phase-detail.sh:55-57
- **Concern**: [SCOPE-REDUCTION] Plan treats missing --rounds-root as best-effort empty output. Scenario: Missing --rounds-root is currently a usage error and the harness covers exit 2; changing it is unnecessary for the feature and regresses the CLI contract
- **Proposed resolution**: Keep the missing flag path as usage exit 2; apply best-effort empty output only when a valid --rounds-root argument names a missing or unreadable directory


### FINDING_10:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/render-review-phase-detail.sh:55; scripts/test-render-review-phase-detail.sh:112-116
- **Concern**: [SCOPE-REDUCTION] Plan changes missing --rounds-root from a usage error into best-effort empty output. Scenario: The current CLI contract and harness require missing --rounds-root to exit 2. Making it silently render empty output hides a bad caller invocation and breaks existing usage-error coverage.
- **Proposed resolution**: Keep missing --rounds-root as usage exit 2. Change only the valid-root no completed rounds branch to render No review rounds completed.


### FINDING_11:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:20; scripts/render-review-phase-detail.sh:63-66
- **Concern**: [SCOPE-REDUCTION] Plan says missing --rounds-root should stay best-effort empty, which conflicts with the existing required-argument usage contract. Scenario: Omitting --rounds-root could be changed from exit 2 to silent empty output, breaking the CLI contract and existing usage-error coverage
- **Proposed resolution**: Clarify that only a nonexistent or unreadable provided rounds root degrades to empty output; keep omitted --rounds-root as usage error exit 2




### FINDING_1: Plan targets the wrong /design final-summary harness
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Cursor-Requirements, Codex-Requirements, Codex-dyn-data-schema, Cursor-dyn-caller-contract, Codex-dyn-scope-boundary
- **Severity**: important
- **Concern**: The plan points final-summary test work at `scripts/test-render-final-summary.sh`, but the real harness run by `make test-render-final-summary` is `skills/design/scripts/test-render-final-summary.sh`. Implementers may edit or create the wrong file and leave /design no-rounds and Mermaid coverage untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Retarget the plan entry and Testing strategy bullet to skills/design/scripts/test-render-final-summary.sh.
  - From Codex-Arch: Retarget that subsection to skills/design/scripts/test-render-final-summary.sh and keep make test-render-final-summary as the verification command; do not add a new scripts/ harness
  - From Cursor-Innovation: Change the plan path to skills/design/scripts/test-render-final-summary.sh and keep make test-render-final-summary in Testing strategy.
  - From Cursor-Requirements: Retarget the plan entry to `skills/design/scripts/test-render-final-summary.sh` (and keep `make test-render-final-summary` in the testing strategy).
  - From Codex-Requirements: Change the planned updated file to skills/design/scripts/test-render-final-summary.sh and keep the make test-render-final-summary validation.
  - From Codex-dyn-data-schema: Change the plan target to `skills/design/scripts/test-render-final-summary.sh` and keep `make test-render-final-summary` as the command to run
  - From Cursor-dyn-caller-contract: in_scope Replace the Files entry and Testing strategy path with `skills/design/scripts/test-render-final-summary.sh` (and update `skills/design/scripts/test-render-final-summary.md` if you document the new case)
  - From Codex-dyn-scope-boundary: Change the UPDATED heading and test bullets to skills/design/scripts/test-render-final-summary.sh, which is the harness run by make test-render-final-summary


### FINDING_3: /design no-rounds summary is skipped when plan-review is absent
- **Reviewer(s)**: Codex-Innovation, Codex-Pragmatic, Codex-dyn-caller-contract
- **Severity**: important
- **Concern**: The design final-summary caller still gates Review Phase Detail rendering on an existing `plan-review` directory. A /design run with zero review rounds may have no `plan-review` root, so it can omit both the section and `No review rounds completed.` even though the feature must apply to /design and /implement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Update the plan to change skills/design/scripts/render-final-summary.sh so the design final summary invokes the shared no-rounds path, or emits the same message, when plan-review is absent; cover it in skills/design/scripts/test-render-final-summary.sh
  - From Codex-Pragmatic: Handle the missing plan-review root explicitly, for example by passing a valid empty temp/root directory to render-review-phase-detail.sh for that case, and add the fixture in skills/design/scripts/test-render-final-summary.sh rather than a nonexistent scripts/test-render-final-summary.sh.
  - From Codex-dyn-caller-contract: Invoke the shared renderer against a synthesized empty plan-review root or append the no-round Review Phase Detail when plan-review is absent, and add a no-root fixture to test-render-final-summary.sh.


### FINDING_7:
- **Reviewer(s)**: Cursor-dyn-scope-boundary
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:131
- **Concern**: [SCOPE-REDUCTION] Plan names `scripts/test-render-final-summary.sh` but the design final-summary harness lives at `skills/design/scripts/test-render-final-summary.sh` (`make test-render-final-summary` invokes the latter).. Scenario: An implementer may edit or add a nonexistent path, skip the real harness, and leave the /design no-rounds and Gantt contract untested.
- **Proposed resolution**: Retarget the plan heading and testing bullets to `skills/design/scripts/test-render-final-summary.sh` (and its `.md` if doc sync is required).




### FINDING_10:
- **Reviewer(s)**: Codex-dyn-scope-control
- **Severity**: important
- **Focus area**: architecture
- **Location**: <TMPDIR>/plan.txt:150-191
- **Concern**: [SCOPE-REDUCTION] Plan adds six files outside the issue's explicit scope list. Scenario: The binding scope lists only scripts/render-review-phase-detail.sh, scripts/render-review-phase-detail.md, and scripts/test-render-review-phase-detail.sh. The added caller, doc, and terminal-progress changes in skills/design/scripts/test-render-final-summary.sh, skills/implement/scripts/test-write-final-report.sh, skills/implement/scripts/write-final-report.md, python/progress_report.py, and python/test_progress_report.py expand this SIMPLE change unless tied to a concrete failing contract.
- **Proposed resolution**: Constrain implementation to the three scoped files. Keep only a specific outside-file update if the plan names the current failing assertion or caller path that blocks the scoped renderer change.




### FINDING_1: No-rounds message omitted for in-flight-only round directories
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: The renderer can stay silent when numeric round directories exist but no completed `round-meta.json` exists, even though zero completed review rounds should render `No review rounds completed.`
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Render the no-completed message for any valid root with zero completed rounds; remove or adjust the in-flight-empty fixture.
  - From Codex-Pragmatic: Render the Review Phase Detail heading plus No review rounds completed whenever the valid root has zero completed rounds, including numeric round dirs without completed metadata
  - From Codex-Requirements: Change the no-completed-rounds branch to emit the required message whenever no completed rounds are found, including numeric round directories without completed metadata


### FINDING_3: Design final summary may skip renderer for no-round reviews
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: The design final summary caller can skip `render-review-phase-detail.sh` when no `plan-review` directory exists, so `/design` may miss the required no-round message.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add the minimal design caller path needed to invoke the renderer for the no-round case, or otherwise emit the same message there.


### FINDING_4: Vendor row filtering by skill can drop valid design timing data
- **Reviewer(s)**: Cursor-dyn-tsv-column-map
- **Severity**: important
- **Concern**: Vendor rows may record `$4=implement` during design plan-review while round rows use `$4=design`, so filtering vendor rows by `--skill design` can produce empty Gantt charts despite valid overlapping timing data.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-tsv-column-map: Document vendor selection as $2==vendor plus overlap only; never filter vendor rows on $4 to match --skill design


### FINDING_5:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/render-review-phase-detail.sh:72-84
- **Concern**: [SCOPE-REDUCTION] Proposed in-flight round-dir exception suppresses the required no-completed-rounds message. Scenario: When round-1 exists but round-meta.json is not written yet, live design or implement progress still has zero completed rounds, but the plan keeps empty output instead of saying No review rounds completed.
- **Proposed resolution**: Render the no-completed-rounds message whenever rounds_list is empty for a valid readable root; drop the numeric-dir exception and its empty-output test.



### FINDING_1: Implement final-report harness remains on old no-round contract
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: The plan changes the shared renderer to emit a Review Phase Detail section for zero completed rounds, but leaves implement final-report tests and related docs expecting that section to be absent. This can make relevant checks fail and leave the /implement acceptance path unverified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add skills/implement/scripts/test-write-final-report.sh to Files to modify/create (flip run-5 to expect the message; decide #3794 expectation) or keep the plan stop-and-report clause and block merge until harness scope is resolved
  - From Cursor-Innovation: Add a minimal in-scope harness update (flip both assertions to require the new message) or narrow the renderer change so implement callers keep empty output until implement tests are in scope. Do not leave CI red behind an out-of-scope wall
  - From Cursor-Pragmatic: Add minimal in-scope updates to skills/implement/scripts/test-write-final-report.sh and skills/implement/scripts/write-final-report.md flipping the no-round contract to expect the message or narrow the plan stop-and-report clause to a required same-PR harness/doc touch
  - From Cursor-Requirements: Add a minimal harness update to the plan: flip the self-review assertion to require No review rounds completed.; for #3794 either preserve empty output when round-meta exists only outside --rounds-root or document an explicit behavior change and adjust that assertion.
  - From Codex-Requirements: Update this minimal assertion to expect the heading and No review rounds completed.; add the implement final-report harness to the targeted test list without changing the implement caller


### FINDING_3: Gantt axis format wraps after 59 minutes
- **Reviewer(s)**: Cursor-dyn-mermaid-gantt-format
- **Severity**: important
- **Concern**: `axisFormat %M:%S` shows minute-of-hour, not total elapsed minutes. With relative epoch seconds, review rounds longer than 59 minutes can render wrapped or misleading axis labels.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-mermaid-gantt-format: Use axisFormat %H:%M:%S (or pick %H:%M:%S when max relative_end_s > 3599) so axis labels stay monotonic for multi-hour rounds; document the cap in render-review-phase-detail.md


### FINDING_5:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/render-review-phase-detail.sh; python/progress_report.py:365-379
- **Concern**: [SCOPE-REDUCTION] Unconditional Gantt rendering in the shared renderer leaks Mermaid blocks into progress-report callers despite the plan excluding progress-report behavior. Scenario: python/progress_report.py shells out to scripts/render-review-phase-detail.sh without any suppression flag and only strips simple Markdown; after the proposed renderer change, live /design or /implement progress output can include Gantt headings, code fences, and task lines even though charts are supposed to live only in final summary notes and the plan says not to change progress-report behavior
- **Proposed resolution**: Add an explicit suppression path, for example a --no-gantt flag passed by python/progress_report.py, or otherwise filter the new Gantt sections before terminal output; keep final-summary callers rendering charts and add one focused regression for progress output



