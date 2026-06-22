### FINDING_1: Unwrap Claude JSON envelope before assessment schema validation
- **Reviewer(s)**: Cursor-Arch, Codex-Generic
- **Severity**: blocking
- **Concern**: `claude --print --output-format json` returns a wrapper object whose `result` field is a string, not a top-level `assessments` array. Parsing stdout directly as `{"assessments":[...]}` fails schema validation on every successful call, so final summaries omit materiality lines despite a working `claude` binary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Match existing subprocess handling: `json.loads(stdout)`, reject when `is_error`, read string `result`, `json.loads` that inner text, then validate `assessments`. Add a mocked test with envelope-shaped stdout, not bare assessments JSON.
  - From Codex-Generic: Parse the Claude JSON envelope first, validate result is a string, JSON-decode that string as the assessments payload, and add a test using the envelope shape from the existing Claude subprocess contract. Alternatively drop --output-format json and parse direct text output.


### FINDING_2: Pin default Haiku model when `LARCH_EXEC_ISSUE_ASSESSMENT_MODEL` is unset
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan only binds `--model` from env when set. Without a documented default, implementations either fail closed (subprocess error → empty assessments) or inherit operator-specific Claude defaults, yielding non-deterministic behavior across environments.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Pin a documented default Haiku slug (same style as other larch model defaults) and allow env override. Test both env-set and env-unset paths.
  - From Cursor-Pragmatic: Pin a default Haiku slug when the env var is unset (same pattern as `agents.py` / `design_lifecycle.py` model defaults) and test one mocked-success assessment path with no env override.


