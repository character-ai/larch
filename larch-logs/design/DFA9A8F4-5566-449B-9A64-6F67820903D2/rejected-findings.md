### [Plan Review] FINDING_13

### FINDING_13: Free-form --panel-role is a prompt-injection surface

- **Concern**: `--panel-role STRING` is free-form. A future caller could pass role text with newlines or contradictory instructions and still get a syntactically valid voter prompt, bypassing intended prompt shapes. While the panel-role is currently hardcoded in the two dispatchers (not user-controllable), the helper's API exposes a free-form sink that could be exploited if a future caller wires it to untrusted input.
- **Proposed resolution**: Replace `--panel-role STRING` with a fixed enum `--prompt-kind design-plan|code-review` (the helper internalizes both panel-role strings). Alternatively, validate the input: reject control characters and newlines; reject non-ASCII; cap length.
- **Reviewers**: 1 (Cursor-Innovation)
- **Severity**: latent

