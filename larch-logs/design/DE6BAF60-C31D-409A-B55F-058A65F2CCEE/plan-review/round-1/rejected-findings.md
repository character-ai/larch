### [Plan Review] FINDING_6

### FINDING_6: Multiline fixture expansion may exceed the proven regression pin
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: latent
- **Concern**: The plan adds several multiline fixtures even though the audit only identified one proven false-green pin, risking extra coverage of awk edge cases already partially covered elsewhere.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Land the line-162/login-home pin first; add multiline fixtures only if issue #3476 gap 1 explicitly requires them


### [Plan Review] FINDING_10

### FINDING_10: Source-only `chmod a-w` may not force auth-prep failure
- **Reviewer(s)**: Cursor-dyn-auth-contract-drift
- **Severity**: important
- **Concern**: The plan assumes making fixture `HOME/.codex/config.toml` read-only will make copied temp config read-only, but plain `cp` into writable `mktemp` dirs normally creates writable destinations, so the intended login auth-prep failure may not occur.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-auth-contract-drift: For the new review-and-fix login auth-prep case (and any t7a hardening), copy one of those proven shims instead of relying on `cp` to preserve `a-w`; drop the inaccurate `cp preserves read-only` sentence from Approach


### [Plan Review] FINDING_11

### FINDING_11: Trusted-project argv greps do not prove `-c` pairing
- **Reviewer(s)**: Codex-dyn-auth-contract-drift
- **Severity**: latent
- **Concern**: Separate greps for the project key and trusted value can pass even if the `-c` flag is dropped and the config string is passed as a bare argv element.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-auth-contract-drift: Assert an adjacent argv pair: a -c line immediately followed by the exact projects."<escaped repo>".trust_level="trusted" config string


