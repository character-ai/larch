# Review Round 5

- Mode: `diff`
- 5 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Plan-review classification parsing diverges from session_env
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `python/rendering.py` reimplements classification parsing for plan-review instead of using `session_env`, losing fallback/error handling. `run-params.json` containing `[]` can raise `AttributeError`, and partially written SIMPLE classification can default to HARD instead of preserving the old regex fallback behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_2: Test stubs replace Python cli.py with Bash despite python3 callers
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Multiple test setup paths overwrite or install `python/cli.py` as a Bash stub even though callers invoke it with `python3 python/cli.py`. This breaks the first stubbed voter render in `scripts/test-dispatch-plan-voters.sh` and the green code-flow path in `skills/implement/scripts/test-step-7a.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_4: Quiet-initialized rendering errors are hidden from operators
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Quiet-initialized rendering/generator errors are written to redirected stderr instead of operator-visible stderr. A CI `agent-sync` drift failure can exit nonzero without showing the actionable diagnostic previously surfaced by the bash `larch_err` path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_6: CRLF guards strip carriage returns before validation
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: CRLF guards in `python/rendering.py` use `splitlines()`, stripping carriage returns before checks in both the generators and topology parsers. CRLF rows in `scripts/generators.tsv` or `topology.tsv` can be silently accepted despite the ported row-hygiene contract and prior bash behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_7: Topology runtime_authority no longer requires git-tracked files
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `python/rendering.py` topology `runtime_authority` validation no longer checks that the authority file is tracked by git. An untracked local authority file can generate docs that pass locally but fail or drift in a clean checkout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Address the concern above.


