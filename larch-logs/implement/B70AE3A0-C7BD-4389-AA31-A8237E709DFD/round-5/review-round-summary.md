# Review Round 5

- Mode: `diff`
- 9 accepted, 10 rejected (9 exonerated)

## Accepted Findings

### FINDING_10: Post-create URL recovery can fabricate or bind the wrong PR when verification fails
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-gh-cli-contracts-output.txt
- **Severity**: important
- **Concern**: Post-create recovery can use URL-derived candidates with `allow_unverified=True` after `pr_view` failure, returning a synthetic OPEN PR without confirming existence, state, or branch match.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-gh-cli-contracts-output.txt: Address the concern above.


### FINDING_11: Breadcrumb diagnostics may disappear from operator-visible stderr under lib-quiet
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-stdout-protocol-output.txt
- **Severity**: important
- **Concern**: `BreadcrumbWriter` honors quiet routing, so ship/CI progress and warning breadcrumbs can go to quiet logs instead of captured stderr during `/implement`, reducing operator-visible progress.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-stdout-protocol-output.txt: Address the concern above.


### FINDING_16: Volatile cleanup tests do not prove successful staged reset ordering
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-python311-compat-output.txt
- **Severity**: important
- **Concern**: Volatile cleanup tests cover reset failure but not the successful `git reset HEAD -- rel` before restore path; one fixture may also consume mocked responses out of order and pass without validating the reset sequence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-python311-compat-output.txt: Address the concern above.


### FINDING_17: Python 3.11 ship guard lacks failure-path harness coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The Python 3.11 guard is checked mostly by static grep, so breaking the runtime failure path could allow unsupported interpreters to run `ship.py` without CI catching it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_2: Stale `flush_logs_pre` monkeypatches obscure merge behavior tests
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Many `python/test_merge.py` tests still monkeypatch `flush_logs_pre` even though `merge_pr` no longer invokes it, making tests imply obsolete pre-merge flush behavior and weakening regression coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_20: Unexpected exceptions lose traceback detail
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `main()` converts all unexpected exceptions to generic `INTERNAL_ERROR` JSON without traceback logging, slowing soak/debug cycles.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_21: Duplicate closed-PR noop checks add redundant gh calls
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Two consecutive identical `_merge_noop_if_pr_closed` calls remain where pre-merge flush used to sit, doubling gh traffic and complicating test stubs with no functional gain.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_22: Create-conflict recovery is stricter than bash when list/view both fail
- **Reviewer(s)**: dyn-gh-cli-contracts-output.txt
- **Severity**: important
- **Concern**: On an “already exists” create conflict, Python can raise if both `pr list` and verified `pr view` fail, even when conflict output contains a valid PR URL that bash would recover from.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-gh-cli-contracts-output.txt: Address the concern above.


### FINDING_23: Quiet stdout redirection can break ship.py JSON stdout protocol
- **Reviewer(s)**: dyn-stdout-protocol-output.txt
- **Severity**: important
- **Concern**: The Python invoke fence runs `ship.py` without restoring caller streams, so under inherited lib-quiet stdout redirection the single JSON result could land in the quiet log instead of orchestrator-visible stdout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-stdout-protocol-output.txt: Address the concern above.


