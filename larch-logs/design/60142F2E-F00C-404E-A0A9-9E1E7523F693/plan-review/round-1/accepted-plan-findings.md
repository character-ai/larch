### FINDING_1: Non-numeric dedup stub may block on stdin
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Cursor-dyn-anchor-verifier, Codex-dyn-anchor-verifier, Codex-Innovation, Codex-Pragmatic, Cursor-dyn-test-contract, Codex-dyn-test-contract
- **Severity**: important
- **Concern**: The refactor removes the inline Python heredoc and calls the helper by path, but the non-numeric `python3` test stub still reads stdin. That can hang or consume ambient stdin during the non-numeric dedup-output scenario instead of reliably asserting bogus output handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch, Codex-Edge, Cursor-dyn-anchor-verifier, Codex-dyn-anchor-verifier: Change the stub for the refactored path to print bogus without reading stdin, or gate on basename dedup-plan-lines.py and exit after printing bogus
  - From Codex-Innovation, Codex-Pragmatic, Cursor-dyn-test-contract, Codex-dyn-test-contract: Change this stub to just print bogus output, or redirect the cat from /dev/null, when updating the eval-isolation exports


### FINDING_2: PYWRAP integration test can recurse
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The integration-test `PYWRAP` does not capture and pass through the real `python3` before prepending the wrapper directory to `PATH`. A wrapper that runs `exec python3 "$@"` can resolve back to itself and recurse instead of reaching the real interpreter for non-dedup calls.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Mirror out_ddd: capture REAL_PYTHON before mkdir PYWRAP; wrapper ends with exec "${REAL_PYTHON:?}" "$@"; invoke with REAL_PYTHON="$REAL_PYTHON" PATH="$PYWRAP:$PATH" run_loop ...


### FINDING_3: New helper may fail dead-script lint
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: The plan adds a skill-local Python helper and sibling documentation file without updating the adjacent `agent-lint` dead-script exclusions. Because the linter may not follow the shell caller edge, `relevant-checks` can fail on the new helper files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add skills/design/scripts/dedup-plan-lines.py and skills/design/scripts/dedup-plan-lines.md to the adjacent exclude block with a short comment naming plan-review-loop.sh as the caller

