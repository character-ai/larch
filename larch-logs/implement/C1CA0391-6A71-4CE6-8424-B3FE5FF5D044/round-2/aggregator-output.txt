### FINDING_1: [OUT_OF_SCOPE] Redundant inner ledger status guard
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Inner status check around `append_group_ledger_ok` duplicates the surrounding `OK|cap_hit` terminal-success gate, adding maintenance noise without changing behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: Missing section marker for Bug A regression
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The Bug A two-run regression is embedded without a clear section marker, making the test harder to maintain.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: Bug A regression may fail for the wrong reason
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The two-run regression cleanup may leave or remove artifacts in a way that lets unfixed code fail through `cp`/stale artifact behavior instead of clearly proving ledger truncation and fresh launch behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_4: Bug A/B red-green verification not documented
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The plan requires red-green verification that the new regressions fail without the production fixes, but no CI step or commit note documents that bisect.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_5: cap_hit regression does not model sentinel-only output
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The `cap_hit` grouped test uses stub output containing `## Recommendation`, while launcher `cap_hit` can produce sentinel-only files; the test may miss regressions for that production shape.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] Dispatch docs are stale for cap_hit ledger semantics
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `scripts/dispatch-with-waterfall.md` still describes only `STATUS=OK` ledger rows and omits the new `cap_hit` ledger behavior and per-invocation ledger truncation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] Ledger truncate follows symlinks
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `GROUP_LEDGER` and `REUSED_INDICES_FILE` truncation follow symlinks in the slots directory, so an attacker who can plant fixed-name symlinks there could truncate an arbitrary writable target.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] Shared ledger path can race across concurrent use
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: A shared ledger path per slots-file directory can race under concurrent or multi-manifest use of the same directory.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] Background Codex stdin closure can skip finalization
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Codex background stdin closure can skip final commit or manifest generation, leaving review fixes uncommitted despite being present in the working tree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] Plan documentation drift for Test 3 tool expectation
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The implementation plan specifies `ALL_OUTPUT_TOOLS=codex cursor` for phase1-OK dedup parity, while the branch asserts `codex codex`; reviewer judged this documentation drift only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
