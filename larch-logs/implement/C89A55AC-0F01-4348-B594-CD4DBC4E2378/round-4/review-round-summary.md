# Review Round 4

- Mode: `diff`
- 5 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: plan-review feature-file scope validation regression
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-review `--feature-file` validation no longer enforces the prior scope-anchor common-shape checks, so empty or oversized DESIGN_TMPDIR feature files can be accepted and embedded into external reviewer prompts, risking token blowups and invalid prompt inputs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_2: stale renderer/generator references remain in shipped docs/prompts
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Shipped documentation and reviewer template guidance still reference deleted renderer/generator files or commands, so maintainers following the instructions may open removed files or run deleted Bash generator scripts instead of the current Python generator entry points.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_3: diagrams upsert cache allowlist is too broad
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Diagrams upsert accepts the entire `XDG_CACHE_HOME` as an input root without `--allow-external-paths`, allowing unrelated cache files such as `~/.cache/other/secret.md` to pass and be published, instead of restricting inputs to larch session cache files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_4: diagrams comment marker lookup mishandles paginated GitHub JSON
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Diagrams upsert uses a marker lookup helper that cannot parse multi-page `gh api --paginate` JSON output, so preserving or updating the stable diagrams comment can fail on issues with more than one comments page.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_5: diagrams-upsert production test stub still uses obsolete comment-list format
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The production diagrams-upsert test stub returns old tab-delimited comment-list output while the real Python helper expects JSON from `gh.find_issue_comment_id_by_marker`, so the preserve-architecture helper path fails before patching the stable diagrams comment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Address the concern above.

