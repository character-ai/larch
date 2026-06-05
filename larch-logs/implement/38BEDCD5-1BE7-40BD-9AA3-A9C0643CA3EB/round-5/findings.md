### FINDING_1: MainAgent scope-anchor renderer is missing/unregistered and untested
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-scope-anchor-flow-output.txt, dyn-prompt-boundaries-output.txt
- **Severity**: important
- **Concern**: `skills/design/SKILL.md` invokes `skills/design/scripts/render-main-agent-scope-anchor.sh` for the MainAgent 0-judge fallback path, but reviewers report the helper is absent from HEAD and/or not wired into harnesses/lint. A clean checkout can fail before ballot adjudication, and the degraded path can lose the same redacted/escaped scope-anchor guarantees as reviewers/voters.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-scope-anchor-flow-output.txt, dyn-prompt-boundaries-output.txt: Address the concern above.

### FINDING_2: Tagged dedup merge can drop reviewer attribution
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: In `skills/design/scripts/plan-review-loop.sh`, when both overlapping blocks are `[SCOPE-REDUCTION]` tagged and the first block is kept, `merge_reviewers(kb, kb)` can lose the second block’s `Reviewer(s)` attribution before tally/aggregation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: Scope-anchor PR bundles unrelated line-count work
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `scripts/compute-pr-line-counts.sh` and related final-report metrics work appear unrelated to the scope-anchor change, increasing review surface and merge risk for the plan-review anchoring fix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_4: collect-findings to scope-marker regression is missing
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The planned regression proving `[SCOPE-REDUCTION]` survives TSV/Concern formatting and remains detectable by `check-scope-reduction-marker.sh` is absent, so collect-format drift could silently break downstream marker handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_5: Scope-marker detection logic is duplicated inside plan-review-loop
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Multiple inline Python blocks in `plan-review-loop.sh` duplicate tagged-detection subprocess logic already centralized in `check-scope-reduction-marker.sh`, creating drift risk across dedup, aggregation, and ballot renumber paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: check-scope-reduction-marker duplicates stdin/file implementations
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `scripts/check-scope-reduction-marker.sh` has near-identical Python heredocs for `--file` and stdin paths, so marker-rule edits must be applied twice.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

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

### FINDING_9: Scope-anchor materialization failure can proceed implicitly
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-env-handoff-output.txt
- **Severity**: important
- **Concern**: `_materialize_scope_anchor` is called without an explicit failure gate. If strip/path/empty-body handling fails or future refactors bypass `errexit`, plan review can continue with a missing or stale `plan-review-scope-anchor.txt`, defeating the fail-loud scope-anchor contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-env-handoff-output.txt: Address the concern above.

### FINDING_10: Global context escaping may alter non-plan-review code samples
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `scripts/launch-claude-subprocess.sh` now escapes all context-file contents, which may alter `<`/`>` in non-plan-review code samples and cause unrelated review paths to inspect changed text.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

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

### FINDING_15: Marker detector strips only a narrow severity vocabulary
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `check-scope-reduction-marker.sh` strips only `important`, `nit`, and `latent` before matching `[SCOPE-REDUCTION]`; other severity prefixes such as `[blocking]` would false-negative unless reviewer vocabulary is constrained.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_16: redact-secrets failure aborts context prompt construction without fallback
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `launch-claude-subprocess.sh` pipes context embedding through `redact-secrets.sh` under `pipefail`; redact failure aborts dispatch prompt construction rather than warning and degrading or surfacing a targeted retry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_17: Panel dispatch tests only check argv, not rendered scope-anchor prompts
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `test-dispatch-plan-review-panel.sh` lacks prompt-content assertions proving static, fallback, and dynamic reviewer prompts actually contain the untrusted scope-anchor block.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_18: Tagged tally neutral-threshold regression is missing
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `test-tally-plan-review.sh` lacks the planned tagged `YES=1 NO=1` neutral threshold case, so tagged scope-reduction findings could be promoted or demoted incorrectly versus normal quorum behavior.
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

### FINDING_23: Voter prompt still leads with finding-anchored proportionality
- **Reviewer(s)**: dyn-scope-anchor-flow-output.txt
- **Severity**: important
- **Concern**: With `--scope-anchor-file`, `render-voter-prompt.sh` still gives generic finding-anchored EXONERATE guidance before the later issue-scope override, risking the same voter bias the branch aims to fix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-scope-anchor-flow-output.txt: Address the concern above.

### FINDING_24: Tagged dedup may retain a body the detector no longer classifies as tagged
- **Reviewer(s)**: dyn-marker-pipeline-output.txt
- **Severity**: important
- **Concern**: `choose_tagged_body` prefers token count, not detector-confirmed leading marker preservation. It can keep a merged body whose `[SCOPE-REDUCTION]` appears only in a detector-ignored field, risking ballot output without a recognized tagged scope-cut.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-marker-pipeline-output.txt: Address the concern above.

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

### FINDING_29: Function-scoped RETURN trap is not cleared
- **Reviewer(s)**: dyn-bash-portability-output.txt
- **Severity**: latent
- **Concern**: `_materialize_scope_anchor()` installs a `RETURN` trap but never clears it, so later function returns in the long-lived Bash driver can re-run cleanup unexpectedly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-portability-output.txt: Address the concern above.

### FINDING_30: Marker helper lacks python3 preflight
- **Reviewer(s)**: dyn-bash-portability-output.txt
- **Severity**: latent
- **Concern**: `check-scope-reduction-marker.sh` depends on `python3` but has no `command -v python3` guard, producing generic nested failures instead of actionable interpreter diagnostics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-portability-output.txt: Address the concern above.

### FINDING_31: aggregate-findings collapses distinct marker-split failures
- **Reviewer(s)**: dyn-bash-portability-output.txt
- **Severity**: latent
- **Concern**: `aggregate-findings.sh` treats any non-zero from the plan-mode Python split the same, obscuring missing interpreter, syntax, unreadable helper, and helper rc 2 failures behind one generic warning.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-portability-output.txt: Address the concern above.

### FINDING_32: compute-pr-line-counts cleanup trap pattern is fragile
- **Reviewer(s)**: dyn-bash-portability-output.txt
- **Severity**: nit
- **Concern**: `compute-pr-line-counts.sh` registers an `EXIT` trap, disables it, manually removes the temp file, and exits, creating an avoidable future cleanup hazard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-portability-output.txt: Address the concern above.

### FINDING_33: Final-report line-count cache can become stale before merge summary
- **Reviewer(s)**: dyn-run-summary-metrics-output.txt
- **Severity**: important
- **Concern**: `write-final-report.sh` reuses the first cached `LINES_STATUS=ok` block for a PR, so the post-merge final report can under-report or misstate diff size after later pushes, CI fixes, or log flushes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-run-summary-metrics-output.txt: Address the concern above.

### FINDING_34: gh API failures for PR line counts lose diagnostics
- **Reviewer(s)**: dyn-run-summary-metrics-output.txt
- **Severity**: latent
- **Concern**: `compute-pr-line-counts.sh` redirects `gh api` stderr to `/dev/null` and collapses all failures to `gh-failed`, leaving operators with `N/A` line counts but no actionable auth/rate-limit/repo/network breadcrumb.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-run-summary-metrics-output.txt: Address the concern above.

### FINDING_35: Missing/empty line-count helper output is silently treated as N/A
- **Reviewer(s)**: dyn-run-summary-metrics-output.txt
- **Severity**: latent
- **Concern**: `write-final-report.sh` does not warn when the line-count helper is missing, non-executable, or emits no `LINES_STATUS`, masking packaging or permission regressions as ordinary unavailable line data.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-run-summary-metrics-output.txt: Address the concern above.

### OOS_1: [OUT_OF_SCOPE] assess-plan-round still falls back to IMPLEMENT_TMPDIR feature file
- **Reviewer(s)**: dyn-scope-anchor-flow-output.txt
- **Severity**: latent
- **Concern**: `assess-plan-round.sh` can fall back to `$IMPLEMENT_TMPDIR/feature-description.txt`, conflicting with the design-session source precedence rule applied elsewhere.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-scope-anchor-flow-output.txt: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] decompose-panel-dispatch remains unanchored
- **Reviewer(s)**: dyn-scope-anchor-flow-output.txt
- **Severity**: important
- **Concern**: `decompose-panel-dispatch.sh` still binds `--feature-file` to raw `feature-description.txt` without stripping plan blocks or using staged scope anchoring.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-scope-anchor-flow-output.txt: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] brainstorm feature-context file is written but unused
- **Reviewer(s)**: dyn-scope-anchor-flow-output.txt
- **Severity**: latent
- **Concern**: `plan-review-feature-context.txt` is created for brainstorm runs, but no downstream production script reads it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-scope-anchor-flow-output.txt: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] lib-vote-tally helper path/block mismatch
- **Reviewer(s)**: dyn-marker-pipeline-output.txt
- **Severity**: nit
- **Concern**: `is_scope_reduction_block` is documented as taking a block but actually passes its argument as a file path; production does not call it today.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-marker-pipeline-output.txt: Address the concern above.

### OOS_5: [OUT_OF_SCOPE] aggregate-findings fallback marker-loss test missing
- **Reviewer(s)**: dyn-marker-pipeline-output.txt
- **Severity**: latent
- **Concern**: Existing plan-mode happy-path coverage does not test validation-failure fallback preserving tagged `[SCOPE-REDUCTION]` blocks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-marker-pipeline-output.txt: Address the concern above.

### OOS_6: [OUT_OF_SCOPE] collect-findings TSV marker regression missing
- **Reviewer(s)**: dyn-marker-pipeline-output.txt
- **Severity**: latent
- **Concern**: `test-collect-findings.sh` lacks a lower-risk regression for TSV `what: [SCOPE-REDUCTION]` folding into severity-prefixed Concern bodies.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-marker-pipeline-output.txt: Address the concern above.

### OOS_7: [OUT_OF_SCOPE] Positive prompt-boundary hardening noted
- **Reviewer(s)**: dyn-prompt-boundaries-output.txt
- **Severity**: nit
- **Concern**: Reviewer noted positive branch behavior: several prompt renderers share redaction/HTML-escape patterns with delimiter-breakout harness coverage, and non-Read-tools context files are redacted/escaped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-boundaries-output.txt: Address the concern above.

### OOS_8: [OUT_OF_SCOPE] Voter ballot file remains raw path-loaded
- **Reviewer(s)**: dyn-prompt-boundaries-output.txt
- **Severity**: latent
- **Concern**: Voters still load `ballot.txt` by filesystem path without inline escaping; this predates the branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-boundaries-output.txt: Address the concern above.

### OOS_9: [OUT_OF_SCOPE] READ_TOOLS branch still reads staged files raw
- **Reviewer(s)**: dyn-prompt-boundaries-output.txt
- **Severity**: latent
- **Concern**: `launch-claude-subprocess.sh`’s `READ_TOOLS=true` branch continues to rely on models reading staged files without inline escaping.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-boundaries-output.txt: Address the concern above.

### OOS_10: [OUT_OF_SCOPE] Round summary SCOPE_ANCHOR_FILE write bypasses env writer
- **Reviewer(s)**: dyn-env-handoff-output.txt
- **Severity**: nit
- **Concern**: `_write_round_summary` writes `SCOPE_ANCHOR_FILE` via raw `printf` instead of the CR/LF-rejecting phase env writer; reviewer judged practical risk low because the path is currently constant under `$DESIGN_TMPDIR`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-env-handoff-output.txt: Address the concern above.

### OOS_11: [OUT_OF_SCOPE] MainAgent renderer lacks dead-script/lint registration and harness
- **Reviewer(s)**: dyn-env-handoff-output.txt
- **Severity**: latent
- **Concern**: The MainAgent renderer is not registered in `agent-lint.toml` dead-script exclusions and has no dedicated harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-env-handoff-output.txt: Address the concern above.

### OOS_12: [OUT_OF_SCOPE] Dedup Python identity-based merge is a maintainability smell
- **Reviewer(s)**: dyn-bash-portability-output.txt
- **Severity**: latent
- **Concern**: The embedded dedup Python calls `choose_tagged_body(kb, blk)` twice and uses `is blk` identity to choose operands; reviewer marked this outside Bash portability scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-portability-output.txt: Address the concern above.

### OOS_13: [OUT_OF_SCOPE] Positive Bash portability assessment
- **Reviewer(s)**: dyn-bash-portability-output.txt
- **Severity**: nit
- **Concern**: Reviewer noted most touched shell follows existing repo conventions and avoids Bash 4-only constructs in runtime paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-portability-output.txt: Address the concern above.

### OOS_14: [OUT_OF_SCOPE] compute-pr-line-counts coerces nonnumeric API fields to zero
- **Reviewer(s)**: dyn-run-summary-metrics-output.txt
- **Severity**: nit
- **Concern**: Awk summation treats nonnumeric `additions`/`deletions` as zero while still emitting `LINES_STATUS=ok`; reviewer judged this unlikely with GitHub’s schema.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-run-summary-metrics-output.txt: Address the concern above.

### OOS_15: [OUT_OF_SCOPE] PR-files test fixtures are duplicated
- **Reviewer(s)**: dyn-run-summary-metrics-output.txt
- **Severity**: nit
- **Concern**: The `gh` PR-files shim/fixture is duplicated across line-count and final-report harnesses, creating fixture drift risk but no runtime defect.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-run-summary-metrics-output.txt: Address the concern above.
