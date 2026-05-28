# Review Round 3

- Mode: `diff`
- 10 accepted, 6 rejected (5 exonerated)

## Accepted Findings

### FINDING_1: Harness Drops Prior Regression Coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The rewritten `scripts/test-revise-plan-with-waterfall.sh` reduces the prior matrix and drops regression coverage for canonical plan path/argv guards, symlink/canonical invariants, heading-loss revert, emit-plan-failed, failed-validation/tier waterfall, codex-absent, and Claude-only paths. One reviewer also notes the new #3146 preamble/corrupt-patch path is not explicitly covered. CI can pass while important revise invariants regress.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_10: Tier-4 Status Documentation Conflicts With Merge Semantics
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The sibling documentation says tier-4 aggregation keeps the worst recorded status, but the code currently keeps the highest rank/best non-ok failure in some mixed-failure cases. Operators may misread `REVISE_TIER_4_STATUS` during failed waterfall debugging.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_11: Candidate Patch Filename Documentation Is Stale
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Documentation still refers to `tier-candidate.patch`, while the code writes `codex-output-candidate.patch`/`*-output-candidate.patch`. Operator-facing docs and fixtures can become confusing even if allowlists still match.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_14: `revise.env` KV Contract Omits `REVISE_WINNING_TIER`
- **Reviewer(s)**: dyn-revise-env-completeness-output.txt
- **Severity**: latent
- **Concern**: The documentation’s numbered KV contract lists nine keys and omits `REVISE_WINNING_TIER`, but `finalize()` always writes/emits it. Consumers following the “full revise KV contract” doc may not expect a key that is present in every artifact.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-revise-env-completeness-output.txt: Address the concern above.


### FINDING_16: Harness Does Not Verify `revise.env` Matches Stdout
- **Reviewer(s)**: dyn-revise-env-completeness-output.txt
- **Severity**: latent
- **Concern**: The harness asserts stdout KVs, including `REVISE_TIER_4_STATUS`, but does not check that `plan-review/round-1/revise/revise.env` exists or matches the emitted contract. Stdout and durable artifacts could diverge without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-revise-env-completeness-output.txt: Address the concern above.


### FINDING_2: Python Rewrite Deviates From Planned Bash/Awk Surface
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The implementation replaces the planned awk unified-diff strip and unchanged file-replacement `cp` path with embedded Python for both formats. This adds a `python3` dependency and changes extraction semantics in a Bash-3.2-oriented script without a shared helper, documentation, or parity tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_3: Unified-Diff Extraction Chooses Corrupt Later Diff
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Unified-diff extraction prefers the last diff candidate in a fence or unfenced response. If a model returns a valid `plan.txt` diff followed by an illustrative or corrupt wrong-path diff, the script can reject or mis-apply the later block and delay recovery until tier 4.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_4: Unfenced Diff Extraction Keeps Trailing Prose
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Unfenced unified-diff extraction retains non-diff prose after the final hunk. A response with a valid patch followed by summary text can fail `git apply --check`, burning tiers 1-3 before tier-4 fallback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_6: File-Replacement Extraction Uses First `diff_lines:` Trailer
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-extract-patch-python-output.txt
- **Severity**: important
- **Concern**: File-replacement extraction stops at the first `diff_lines:` line in a `## Plan` block. If the plan body contains an illustrative or in-fence `diff_lines:` before the real trailer, the candidate can be truncated yet still pass validation and apply the wrong plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-extract-patch-python-output.txt: Address the concern above.


### FINDING_8: Tier-4 Status Merge Keeps Less Severe Failure
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `merge_tier4_status`/`tier4_rank` can keep a later, less severe tier-4 status over an earlier worse one, such as `emit-plan-failed` over `apply-failed` or `invalid-patch`. The final loop status may remain failed, but `REVISE_TIER_4_STATUS` forensics misrepresent the worst tier-4 outcome.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


