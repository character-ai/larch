### OOS_1: [OUT_OF_SCOPE] close-priors KV failure paths lack focused tests
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Pytest coverage is thin for close-priors failure contracts such as `ISSUE_LIST_FAILED`, `CLOSE_FAILED`, and `BODY_FILE_FAILED`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### OOS_2: [OUT_OF_SCOPE] refresh-execution issue test uses invalid CLI stub
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `test-refresh-execution-issues.sh` has the same invalid `cli.py` bash stub pattern and may give false confidence on the happy path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### OOS_3: [OUT_OF_SCOPE] release docs still mention deleted shell scripts
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Release skill prose still references deleted shell scripts, creating operator confusion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### OOS_4: [OUT_OF_SCOPE] analyze skill docs point at deleted contract markdown
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Analyze skill docs reference deleted analyze contract markdown files instead of current Python module contracts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### OOS_5: [OUT_OF_SCOPE] callsite docs have broken CLI quoting
- **Reviewer(s)**: dyn-cli-registry-output.txt
- **Severity**: nit
- **Concern**: The reviewer flagged broken audit and release skill callsite quoting as out of scope for the CLI registry audit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cli-registry-output.txt: Address the concern above.


