### [Plan Review] FINDING_11

### FINDING_11: Bash 3.2 smoke is not the portability gate
- **Reviewer(s)**: Cursor-dyn-portability-audit, Codex-dyn-portability-audit
- **Severity**: latent
- **Concern**: `BASH_COMPAT=3.2` on newer Bash versions does not make Bash-4-only syntax unavailable, so it cannot replace the existing Bash 3.2 static portability checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-portability-audit: Keep the BASH_COMPAT smoke if required, but make lint-bash32 or the existing forbidden-token assertions the stated portability gate for this harness
  - From Codex-dyn-portability-audit: Keep the BASH_COMPAT smoke if required, but make lint-bash32 or the existing forbidden-token assertions the stated portability gate for this harness


### [Plan Review] FINDING_12

### FINDING_12: B6 does not prove the test harness consumes TSV rows
- **Reviewer(s)**: Cursor-dyn-consumer-contract, Codex-dyn-consumer-contract
- **Severity**: important
- **Concern**: The B6 source-of-truth case only proves lint iterates a synthetic TSV row, not that the test harness parser uses every manifest row to generate fixtures and expectations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-consumer-contract: Extend B6 to assert the harness enumeration matches lint row count (or that populate_fixture writes every parsed path); add an assertion that a deliberately omitted parser row leaves a manifest-only path without a fixture and fails
  - From Codex-dyn-consumer-contract: Revise B6 so the extra TSV row must be consumed by the test harness parser itself, for example by requiring the manifest-derived fixture writer to create the extra file and asserting the compliant synthetic fixture passes only because that parsed row was handled.


