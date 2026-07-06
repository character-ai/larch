# Review Round 1

- Mode: `diff`
- 5 accepted, 4 rejected (0 neutral)

## Accepted Findings

### FINDING_1: issue_create gh reads still bypass bounded helpers
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, codex-specialist-testing
- **Severity**: major
- **Concern**: `python/larch/issue/issue_create.py` still routes several `/issue` read paths through direct `gh` subprocess calls with `timeout=None`, so a hung GitHub read can still stall the command even though the A5 lint/baseline now recognizes the path. Those reads should be moved onto `larch.git.gh` helpers or otherwise forced through bounded timeouts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_2: wire-artifact Python writer detection misses real writers
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-wire-ratchets
- **Severity**: major
- **Concern**: The Python side of `python/larch/lint/lint_wire_artifact_pairing.py` only recognizes a writer when the artifact literal appears in the same write-call snippet, so split-line path bindings, `_write_text_atomic`, and similar atomic-write helpers are invisible. That leaves real writers such as `design-report-gate-sidecars.md` and `.ship-route-exit-handoff.env` baselined as one-sided findings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-wire-ratchets: Address the concern above.


### FINDING_3: Bash 3.2 empty-array guard tracking is too coarse
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-correctness, codex-specialist-edge-cases, codex-specialist-testing
- **Severity**: major
- **Concern**: The Bash 3.2 array lint uses file-global guard state and never clears the empty-array flag after repopulation, so a prior `${#arr[@]}` can hide later unsafe expansions and same-line assignment/expansion order can miss real aborts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_4: shell writer detection overcounts redirected lines
- **Reviewer(s)**: codex-specialist-edge-cases, cursor-specialist-testing
- **Severity**: major
- **Concern**: The shell writer scan in `lint_wire_artifact_pairing.py` treats any redirected line that mentions the artifact as proof of writing, so a reader/printf mismatch can pass as a writer. The `skills/*/scripts/` manifest-artifact case also lacks a passing regression fixture.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.


### FINDING_7: basename reader matching is too broad
- **Reviewer(s)**: dyn-dyn-wire-ratchets
- **Severity**: major
- **Concern**: In `lint_wire_artifact_pairing.py`, basename matching uses bare substring search, so sibling filenames like `scout-coder-manifest.json` can inflate reader counts for `manifest.json` even when the underlying run-log file is never read.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-wire-ratchets: Address the concern above.


