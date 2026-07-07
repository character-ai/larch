# Review Round 1

- Mode: `diff`
- 3 accepted, 2 rejected (0 neutral)

## Accepted Findings

### FINDING_1: bgjob merge-env parsing drops whitespace KV fields
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-bgjob-contract
- **Severity**: major
- **Concern**: Step 3/6 bgjob wrappers tee whitespace-separated checks-failure relay stdout into the merge-result env, but the daemon still merges that file with line-oriented KV parsing. That can collapse a relay line into one bogus entry, drop `DIGEST_FILE` / `REDACTED_LOG_FILE` from the result env, and break the repair loop; the same raw tee path also exists in `step-6-entry.sh`, and there is no regression test that proves the round-trip survives.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-bgjob-contract: Address the concern above.


### FINDING_2: BGJOB_RC=0 gate blocks load-routing conflict resolution
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-bgjob-contract
- **Severity**: major
- **Concern**: The migrated Step 3/6/7a prose gates normal continuation on `BGJOB_RC=0` before it looks at routing KVs, but the rebase checkpoint probes still return a non-zero child rc on conflict while emitting `CHECKPOINT_NEXT=load-routing`. That makes routine rebase conflicts look like hard step failures instead of routing them to conflict resolution.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-bgjob-contract: Address the concern above.


### FINDING_3: shell merge-env writes can follow symlinks
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: major
- **Concern**: The shell merge-env truncation and tee paths can follow symlinks before bgjob validates paths. A compromised or stale session tmpdir could redirect `bgjob/<step>.merge.env` or `bgjob` itself at another same-user file and have the launcher overwrite it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.


