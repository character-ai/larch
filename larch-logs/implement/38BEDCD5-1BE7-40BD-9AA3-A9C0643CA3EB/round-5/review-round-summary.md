# Review Round 5

- Mode: `diff`
- 18 accepted, 17 rejected (14 exonerated)

## Accepted Findings

### FINDING_11: Scout/read-tools staged context lacks delimiter hardening
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-prompt-boundaries-output.txt
- **Severity**: latent
- **Concern**: The scout path stages and reads issue/scope context as raw files via Read tools, unlike reviewer/voter/revise prompts that inline redacted and HTML-escaped untrusted blocks. Malicious issue prose could influence dynamic archetype selection despite the new anchoring.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, dyn-prompt-boundaries-output.txt: Address the concern above.


### FINDING_12: Post-dedup parity helper failure hard-aborts instead of degrading
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: In `plan-review-loop.sh`, an exit 2 from `check-scope-reduction-marker.sh` during post-dedup parity aborts the whole round instead of falling back to the pre-dedup snapshot like other marker-degradation paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_13: Step 3 result-env write failure is non-fatal
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `_terminal_exit` can emit healthy stdout KVs including `SCOPE_ANCHOR_FILE` even when `write_step3_result_env` fails, leaving durable `.step3-plan-review-result.env` stale or missing for MainAgent handoff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_14: run-step3-review handoff/preference harness cases are missing
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-env-handoff-output.txt
- **Severity**: important
- **Concern**: `test-run-step3-review.sh` lacks planned coverage for `DESIGN_TMPDIR` winning over stale `IMPLEMENT_TMPDIR`, CR/LF rejection, outside-path clearing, canonical scope-anchor recovery, and explicit `SCOPE_ANCHOR_FILE` parse/emit behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-env-handoff-output.txt: Address the concern above.


### FINDING_17: Panel dispatch tests only check argv, not rendered scope-anchor prompts
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `test-dispatch-plan-review-panel.sh` lacks prompt-content assertions proving static, fallback, and dynamic reviewer prompts actually contain the untrusted scope-anchor block.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_19: aggregate-findings plan-mode marker tests are incomplete
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `test-aggregate-findings.sh` lacks planned partial marker-loss fallback, inline-emitter, and code-mode negative cases, leaving plan-mode marker preservation and code-mode isolation under-tested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_20: Revise prompt harness omits untrusted scope-evidence framing assertion
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-revise-plan-with-waterfall.sh` verifies delimiter behavior but not the expected framing text that labels scope evidence as untrusted and non-instructional.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_21: Brainstorm reference contradicts staged-anchor contract
- **Reviewer(s)**: dyn-scope-anchor-flow-output.txt
- **Severity**: important
- **Concern**: `skills/design/references/brainstorm.md` still says Step 3 merges brainstorm into the feature file passed to panel dispatch, contradicting the new contract where `plan-review-scope-anchor.txt` is binding and brainstorm context is optional/non-binding.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-scope-anchor-flow-output.txt: Address the concern above.


### FINDING_22: Round artifact allowlist omits scope-anchor forensic files
- **Reviewer(s)**: dyn-scope-anchor-flow-output.txt
- **Severity**: latent
- **Concern**: `scripts/lib-design-round-artifacts.sh` does not snapshot `plan-review-scope-anchor.txt` or `findings-in-scope.pre-dedup.md`, making multi-round debugging unable to reconstruct what scope reviewers/voters actually saw.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-scope-anchor-flow-output.txt: Address the concern above.


### FINDING_25: Marker detector ignores plain `- Concern:` lines
- **Reviewer(s)**: dyn-marker-pipeline-output.txt
- **Severity**: important
- **Concern**: `check-scope-reduction-marker.sh` only inspects markdown-bold `- **Concern**:` lines, so blocks using plain `- Concern:` can false-negative in dedup, aggregation splitting, and parity paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-marker-pipeline-output.txt: Address the concern above.


### FINDING_26: Dynamic reviewer prompt bodies are concatenated raw
- **Reviewer(s)**: dyn-prompt-boundaries-output.txt
- **Severity**: important
- **Concern**: `dispatch-plan-review-panel.sh` concatenates scout JSON `prompt_body` with raw `cat` before the escaped scope-anchor tail. Soft instruction injection from dynamic archetype output can reach reviewer prompts unredacted/unescaped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-boundaries-output.txt: Address the concern above.


### FINDING_27: run-step3 recovery can abort before durable normalized handoff
- **Reviewer(s)**: dyn-env-handoff-output.txt
- **Severity**: important
- **Concern**: `recover_main_agent_scope_anchor` returns 1 under `set -e`, so missing/unrecoverable anchors can abort `run-step3-review.sh` before terminal KVs and `.step3-review-result.env` are written, rather than downgrading durably to `panel-failed`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-env-handoff-output.txt: Address the concern above.


### FINDING_28: MainAgent renderer lacks path containment and symlink validation
- **Reviewer(s)**: dyn-env-handoff-output.txt
- **Severity**: important
- **Concern**: `render-main-agent-scope-anchor.sh` accepts any readable `--scope-anchor-file` without mirroring `DESIGN_TMPDIR` containment, symlink rejection, or CR/LF validation, so poisoned handoff state could cause MainAgent voting to read arbitrary host files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-env-handoff-output.txt: Address the concern above.


### FINDING_3: Scope-anchor PR bundles unrelated line-count work
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `scripts/compute-pr-line-counts.sh` and related final-report metrics work appear unrelated to the scope-anchor change, increasing review surface and merge risk for the plan-review anchoring fix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_33: Final-report line-count cache can become stale before merge summary
- **Reviewer(s)**: dyn-run-summary-metrics-output.txt
- **Severity**: important
- **Concern**: `write-final-report.sh` reuses the first cached `LINES_STATUS=ok` block for a PR, so the post-merge final report can under-report or misstate diff size after later pushes, CI fixes, or log flushes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-run-summary-metrics-output.txt: Address the concern above.


### FINDING_4: collect-findings to scope-marker regression is missing
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The planned regression proving `[SCOPE-REDUCTION]` survives TSV/Concern formatting and remains detectable by `check-scope-reduction-marker.sh` is absent, so collect-format drift could silently break downstream marker handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_7: Plan-review loop and scope-anchor regression coverage is incomplete
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-marker-pipeline-output.txt
- **Severity**: important
- **Concern**: Multiple planned loop/scope-anchor fixtures are missing, including malformed `larch:plan` handling, dedup marker preservation, parity fallback, tagged+untagged overlap, aggregation fallback, ballot renumber, outline append, and inline-emitter cases. Marker-loss or stale-anchor regressions could reach production without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-marker-pipeline-output.txt: Address the concern above.


### FINDING_8: lib-vote-tally scope helper API is misleading
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `is_scope_reduction_block` documents block content but actually requires a file path, which could mislead future callers into passing inline markdown and getting false negatives.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


