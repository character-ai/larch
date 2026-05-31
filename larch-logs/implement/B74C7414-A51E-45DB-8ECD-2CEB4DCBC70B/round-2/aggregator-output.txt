### FINDING_1: Step5 harness lacks shared production `pre_coder_snapshot_dir`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-bash32-output.txt, dyn-step5-flow-output.txt
- **Severity**: important
- **Concern**: `step5-starting-round` sources `review-implement-step5-loop.sh` without also defining the production `pre_coder_snapshot_dir` helper now used by fix-applied Step 5 paths. Some new cases avoid this by duplicating inline stubs, but any unstubbed path reaching the structural/MAV relocation logic can fail with `command not found`, and duplicated stubs can drift from production.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-bash32-output.txt, dyn-step5-flow-output.txt: Address the concern above.

### FINDING_2: MAV test hardcodes relocated snapshot path
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The MAV assertion hardcodes `.pre-coder-snapshots/round-1` instead of deriving the path through `pre_coder_snapshot_dir`, so a legitimate helper layout change could break the test while production remains valid.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: Repeated pre-coder head path construction
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Several functions manually reconstruct the relocated `pre-coder-head.txt` path, increasing the chance that future edits update only some call sites.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: Snapshot placement tests do not cover full trust boundary
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-snapshot-tamper-output.txt
- **Severity**: latent
- **Concern**: The new location/invariant tests mainly assert snapshots are outside `round_dir`, but they do not fully assert canonical placement outside `PWD` / Codex grants or that orchestrator integration writes snapshots only under `.pre-coder-snapshots`. A regression could pass tests while snapshots remain coder-writable or are written back into `round_dir`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-snapshot-tamper-output.txt: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] Duplicated carryover head-load logic
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Two residue functions duplicate carryover head-loading logic, creating maintenance noise for future carryover behavior changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: New Step 5 acceptance tests are not wired into CI
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The relocated structural LOC and MAV relocation tests live in `step5-starting-round`, but that section lacks a Makefile recipe / harness shard, so CI may never run the new acceptance coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_7: Structural LOC relocation test relies on indirect cap-hit behavior
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The relocated structural LOC test checks an indirect cap-hit envelope rather than directly asserting the structural LOC input/path behavior, so a stale `round_dir` read or unrelated envelope change could obscure the intended regression signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] Pre-existing `step5-starting-round` CI blind spot
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The whole `step5-starting-round` section was already absent from CI before this branch, so the new relocation tests amplify a pre-existing harness coverage gap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] Relocation still assumes Codex sandbox confinement
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-snapshot-tamper-output.txt, dyn-bash32-output.txt
- **Severity**: latent
- **Concern**: The relocation relies on Codex `--full-auto` being confined to declared workspace/add-dir roots. If Codex can write outside those roots or traverse into sibling snapshot directories, relocation alone is insufficient; follow-up sandbox hardening or read-only snapshot defenses may be needed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-snapshot-tamper-output.txt, dyn-bash32-output.txt: Address the concern above.

### FINDING_10: Snapshot integrity is not enforced outside `PWD` / all Codex grants
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-snapshot-tamper-output.txt
- **Severity**: important
- **Concern**: The new invariant protects against snapshots under `round_dir`, but Codex dispatch also grants `--add-dir "$PWD"`. If `IMPLEMENT_TMPDIR` is placed inside the repo, relocated snapshots under `$IMPLEMENT_TMPDIR/.pre-coder-snapshots` are still inside the `PWD` grant and remain tamperable, weakening the carryover guard despite relocation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-snapshot-tamper-output.txt: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] Harness trust-boundary fixture does not mirror production cache layout
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-step5-flow-output.txt
- **Severity**: latent
- **Concern**: Some harness layouts keep `IMPLEMENT_TMPDIR` under the work tree, so they do not exercise the production expectation that snapshots live outside the repo / all Codex workspace grants.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, dyn-step5-flow-output.txt: Address the concern above.

### FINDING_12: `post_pre_head_file` leaks as a global
- **Reviewer(s)**: dyn-bash32-output.txt
- **Severity**: nit
- **Concern**: `run_implement_loop` assigns `post_pre_head_file` without declaring it `local`, unlike neighboring loop state, so sourcing the loop in harnesses can leak the variable into the parent shell.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash32-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] Step5 loop coupling should be documented
- **Reviewer(s)**: dyn-bash32-output.txt
- **Severity**: nit
- **Concern**: `review-implement-step5-loop.sh` now depends on symbols defined by `review-and-fix.sh`; production ordering is acceptable, but standalone sourcing expectations should stay explicit in the Step 5 loop documentation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash32-output.txt: Address the concern above.
