### FINDING_1:
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Cursor-dyn-anchor-verifier, Codex-dyn-anchor-verifier
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-plan-review-loop.sh:1862-1865
- **Concern**: Non-numeric python3 stub still reads stdin after heredoc removal. Scenario: The proposed helper call no longer feeds the inline Python heredoc to stdin, so this stub's cat can block on ambient stdin or become environment-dependent when make test-plan-review-loop reaches the non-numeric dedup-output case
- **Proposed resolution**: Change the stub for the refactored path to print bogus without reading stdin, or gate on basename dedup-plan-lines.py and exit after printing bogus

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-plan-review-loop.sh:1507-1528
- **Concern**: Integration-test PYWRAP omits the established REAL_PYTHON capture/passthrough pattern. Scenario: Plan edge cases require exec of real python3 for non-dedup calls but do not require REAL_PYTHON="$(command -v python3)" before PATH prepend or REAL_PYTHON="$REAL_PYTHON" on run_loop; a wrapper that does exec python3 "$@"" with PYWRAP first on PATH recurses or never reaches the real interpreter
- **Proposed resolution**: Mirror out_ddd: capture REAL_PYTHON before mkdir PYWRAP; wrapper ends with exec "${REAL_PYTHON:?}" "$@"; invoke with REAL_PYTHON="$REAL_PYTHON" PATH="$PYWRAP:$PATH" run_loop ...

### FINDING_3:
- **Reviewer(s)**: Codex-Innovation, Codex-Pragmatic, Cursor-dyn-test-contract, Codex-dyn-test-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-plan-review-loop.sh:1862-1865
- **Concern**: Plan leaves the non-numeric python3 stub reading stdin after the heredoc is removed. Scenario: The refactor changes the call from python3 - with a heredoc to python3 "$DEDUP_PLAN_LINES_PY"; this stub's cat >/dev/null can block or consume unrelated stdin, so the existing test may hang instead of asserting non-numeric output
- **Proposed resolution**: Change this stub to just print bogus output, or redirect the cat from /dev/null, when updating the eval-isolation exports

### FINDING_4:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: agent-lint.toml:453-457
- **Concern**: Plan adds a new skill-local Python helper and sibling doc without registering the agent-lint dead-script exception. Scenario: This repo already excludes skill-local Python helpers reached only through shell callers; agent-lint does not follow that runtime shell edge, so relevant-checks can fail on dedup-plan-lines.py and dedup-plan-lines.md
- **Proposed resolution**: Add skills/design/scripts/dedup-plan-lines.py and skills/design/scripts/dedup-plan-lines.md to the adjacent exclude block with a short comment naming plan-review-loop.sh as the caller
