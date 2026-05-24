### FINDING_11: Step 5d `gh` failure logging omits `append-tool-failure --redact`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Verbose `gh` failures risk copying auth- or token-shaped material into `execution-issues.md` and committed design logs, unlike other network-ish captures that pass `--redact`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_4: run_ok merges stderr into the parsed KV blob
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Test helper `run_ok` combines stderr into output that grep-based assertions treat as structured KV, so stray stderr could break parsing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_5: Step 5d upstream deferral lacks argv/repo-identity guard vs documented expectations
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Step 5d is described as gated on argv-level upstream repo pinning, but the flow effectively keys off issue number, a sentinel, and a hardcoded `gh --repo` target. In clones or forks where issue 2670 exists for unrelated work, the skill can still post the fixed upstream tracking comment on `character-ai/larch#2672`, creating misleading upstream noise and a mismatch with SECURITY / acceptance / flags prose. Related doc-only risk: argv wording can steer security review toward the wrong surface unless it explicitly tracks the `gh` invocation and the real Step 5d conditions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_6: Partition intent can be lost when run-params repair fails (especially without jq)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Partition persistence recovery depends on `jq` and uses silent `|| true`-style fallbacks. If `write-run-params` fails and `jq` is absent, `partition_requested` may never become true, argv `--partition` can be dropped before Step 2b.5, and the forced soft path is skipped without a clear operator-visible failure mode.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_8: `--plan-file` contract is not exercised in the harness
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The helper supports optional `--plan-file`, but tests never pass a non-default plan path, so argv or wiring bugs for that mode could ship while CI stays green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_9: TRIVIAL_DOC_ONLY jq assertion omits `partition_requested == false`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The trivial preset path does not re-check the default `partition_requested` false-only expectation in the `jq -e` filter.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


