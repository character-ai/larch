### FINDING_12: Ensure Step 3 result env/KVs emit on all loop failure paths
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-scope-flow-output.txt
- **Severity**: important
- **Concern**: Certain `plan-review-loop.sh` failure paths can exit before writing `.step3-plan-review-result.env` or emitting `LOOP_STATUS`/`SCOPE_ANCHOR_FILE` KVs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Guard the write (log + continue) and always emit loop KVs before exit; or use write_step3_result_env || true only after explicit error logging
  - From dyn-scope-flow-output.txt: Replace the bare `exit 1` with `return 1` plus an explicit terminal status (`LOOP_STATUS=panel-failed` or a dedicated ballot-renumber token), or call `_terminal_exit` / `_snapshot_terminal_exit_preserving_status` before exiting so `SCOPE_ANCHOR_FILE` is always emitted on every loop termination path.


### FINDING_13: Add reviewer prompt scope-anchor assertions
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `test-plan-review-prompt.sh` does not assert the rendered prompt includes binding issue scope, untrusted framing, or `[SCOPE-REDUCTION]` instruction text.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Assert Binding issue scope anchor, untrusted framing, and [SCOPE-REDUCTION] what-prefix instruction when --feature-file is set.
  - From cursor-specialist-plan-fidelity-output.txt: Add assertions for Binding issue scope anchor, untrusted evidence framing, and [SCOPE-REDUCTION] what-field instruction per plan


### FINDING_16: Add aggregate-findings plan-mode validation tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-mode aggregation lacks tests for marker-loss fallback, code-mode negative behavior, and inline emitter cases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add AGGREGATED=false validation-failed fixture, code-mode control, and inline Severity/Concern fixture.


### FINDING_17: Fail closed when marker helper fails in plan-review dedup
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-marker-flow-output.txt
- **Severity**: latent
- **Concern**: `plan-review-loop.sh` treats unexpected marker-helper failures as “untagged,” allowing real `[SCOPE-REDUCTION]` findings to lose their marker during dedup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Fail closed or force pre-dedup fallback on helper rc not in {0,1}; add harness for helper failure.
  - From dyn-marker-flow-output.txt: Fail closed on helper `rc ∉ {0,1}` (abort dedup or force pre-dedup fallback), or treat helper failure as tagged for merge purposes so the tagged body is never discarded.


### FINDING_18: Harden MainAgent 0-judge scope-anchor inlining
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-prompt-sandbox-output.txt
- **Severity**: latent
- **Concern**: The MainAgent 0-judge path inlines `SCOPE_ANCHOR_FILE` raw, unlike external reviewer/voter paths that use redacted and escaped untrusted-data blocks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Require MainAgent scope anchoring to use the same redact+entity-escape wrapper as render-voter-prompt.sh and add a delimiter-breakout regression test for the SKILL path
  - From dyn-prompt-sandbox-output.txt: Add a small shared helper (or reuse `emit_untrusted_file_block`) to render a hardened scope-anchor block for MainAgent consumption, and change Step 3 prose to require emitting that wrapped block instead of raw file contents; add a harness asserting closing-tag breakout is escaped on the MainAgent path.


### FINDING_2: Add voter dispatch scope-anchor forwarding regressions
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `dispatch-plan-voters.sh` forwarding of `--scope-anchor-file` is untested, so voters could silently lose issue-scope anchoring.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add harness cases asserting --scope-anchor-file is forwarded and omission preserves byte-identical prompts.
  - From cursor-specialist-testing-output.txt: Add harness cases that assert --scope-anchor-file appears in all voter prompt render argv (including retry) and that omission preserves byte-identical prompts.
  - From cursor-specialist-plan-fidelity-output.txt: Add harness cases asserting --scope-anchor-file is forwarded on all render paths and omitted when unset


### FINDING_20: Make anchored voter proportionality override legacy EXONERATE guidance
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-compat-mode-output.txt
- **Severity**: important
- **Concern**: With `--scope-anchor-file`, voter prompts still include finding-relative EXONERATE guidance before the issue-scope anchor, preserving the addition-biased failure mode.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: When --scope-anchor-file is set, rewrite or reorder proportionality guidance so issue-scope rules override the legacy finding-anchored EXONERATE line
  - From dyn-compat-mode-output.txt: When a readable scope anchor is inlined, replace or qualify the global EXONERATE lines so proportionality is explicitly measured against the originating issue scope (mirror the `[SCOPE-REDUCTION]` problem-first rubric), and add a harness assertion that the finding-relative wording does not appear unchanged on the anchored path.


### FINDING_22: Fail closed when run-step3 scope-anchor handoff validation rejects a non-empty path
- **Reviewer(s)**: dyn-scope-flow-output.txt
- **Severity**: important
- **Concern**: `validate_scope_anchor_handoff` clears invalid `SCOPE_ANCHOR_FILE` with only a warning, creating asymmetry where external judges saw anchored scope but MainAgent fallback may not.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-scope-flow-output.txt: Fail closed with a dedicated `LOOP_STATUS` / `TALLY_PLAN_REVIEW_STATUS` when a non-empty handoff path cannot be validated, or fall back to the canonical staged file `$DESIGN_TMPDIR/plan-review-scope-anchor.txt` when it exists and is a regular file under the design tmpdir, instead of clearing the key.


### FINDING_25: Fix tagged dedup parity so distinct scope-reduction findings cannot collapse silently
- **Reviewer(s)**: dyn-marker-flow-output.txt
- **Severity**: important
- **Concern**: The post-dedup parity gate permits multiple pre-dedup tagged findings to match one surviving post-dedup block, and tagged-to-tagged merges discard later Concern text.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-marker-flow-output.txt: Mirror the aggregation guard in `skills/review/scripts/aggregate-findings.sh:767-779`: fail parity when `len(post_tag) < len(pre_tagged)`, and match each post tagged block to at most one pre tagged block (track `used` indices or require distinct `dst` per `src`).
  - From dyn-marker-flow-output.txt: In the both-tagged merge branch, prefer the block whose canonical detector still sees a leading marker (or refuse to merge two tagged blocks), and add a harness case with two distinct `[SCOPE-REDUCTION]` findings that Jaccard-merge to one block.


### FINDING_26: Restrict scope-reduction marker semantics to in-scope FINDING blocks
- **Reviewer(s)**: dyn-marker-flow-output.txt, dyn-compat-mode-output.txt
- **Severity**: important
- **Concern**: The marker detector and dedup tagging include `OOS_*` headings even though the plan contract limits marker preservation to in-scope `FINDING_*` blocks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-marker-flow-output.txt: Restrict `candidates()` to `FINDING` headings only (or explicitly document and test OOS behavior if intentional).
  - From dyn-compat-mode-output.txt: Restrict dedup tagging to `FINDING_*` blocks (parity gate already does), and narrow `check-scope-reduction-marker.sh` to `FINDING_*` candidates—or add an explicit `FINDING-only` mode used by dedup/aggregation while keeping any broader detector out of the ballot path.


### FINDING_27: Avoid raw Claude waterfall context attachment for revise scope anchor
- **Reviewer(s)**: dyn-prompt-sandbox-output.txt
- **Severity**: important
- **Concern**: Claude revise tier receives the scope anchor both escaped in the prompt and raw through `--context-files`, allowing delimiter breakout or instruction text to bypass hardening.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-sandbox-output.txt: For revise launches that already embed the feature in `PROMPT_PATH`, omit `--feature-file` from `launch-claude-review.sh` (and any context append), or teach `launch-claude-subprocess.sh` to apply the same `redact-secrets` + HTML-escape pipeline when inlining context files that are also prompt-delimited payloads.


### FINDING_28: Harden scout description-file handling for scope anchors
- **Reviewer(s)**: dyn-prompt-sandbox-output.txt
- **Severity**: important
- **Concern**: Plan-review scout receives the staged scope anchor as a copied/read context file without delimiter escaping at rest or read time.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-sandbox-output.txt: Either inline scout description through the same `emit_untrusted_file_block` pattern used by reviewers/voters, or stage a redacted+HTML-escaped copy for scout consumption and add delimiter-breakout coverage in the scout harness.


### FINDING_3: Assert panel prompts actually contain scope-anchor framing
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Panel tests only check argv forwarding, not that rendered reviewer prompts include the binding issue anchor, untrusted evidence framing, or scope-reduction instructions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extend harness to inspect rendered prompt files for untrusted scope evidence and [SCOPE-REDUCTION] instructions.
  - From cursor-specialist-testing-output.txt: Capture rendered prompt; assert binding scope anchor / untrusted evidence sections.


### FINDING_33: Fail closed on aggregate-findings marker helper infrastructure failure
- **Reviewer(s)**: dyn-bash-portability-output.txt
- **Severity**: important
- **Concern**: Plan-mode aggregation treats marker helper failures like “not tagged,” routing tagged scope-reduction blocks into normal LLM aggregation instead of the preserved tagged sidecar.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-portability-output.txt: Mirror the deduper’s `is_tagged()` handling in `plan-review-loop.sh`: distinguish exit `1` (false) from infrastructure failure (non-0/1), log a WARN, and on helper failure fall back to the untagged+tagged split using the original input (or abort aggregation with `AGGREGATED=false`) rather than misclassifying tagged blocks.


### FINDING_37: Make compute-pr-line-count cleanup non-fatal after KV emission
- **Reviewer(s)**: dyn-bash-portability-output.txt
- **Severity**: latent
- **Concern**: `compute-pr-line-counts.sh` can emit partial KVs and then fail on manual temp cleanup, confusing downstream KV parsing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-portability-output.txt: Keep the EXIT trap until process exit, or wrap the manual `rm` with `rm -f … || true` after successful emission so the helper always exits 0 once KVs are printed.


### FINDING_38: Gate scope-anchor voter prompt behavior to plan verification context
- **Reviewer(s)**: dyn-compat-mode-output.txt
- **Severity**: latent
- **Concern**: `render-voter-prompt.sh` emits plan-review scope-anchor instructions whenever the file is readable, without checking `--verification-context`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-compat-mode-output.txt: Gate scope-anchor emission on `VERIFICATION_CONTEXT=plan` (fail closed or ignore the flag with a warning otherwise), document that invariant in `render-voter-prompt.md`, and add a negative harness case for `--verification-context code --scope-anchor-file …`.


### FINDING_39: Document SCOPE_ANCHOR_FILE in plan-review-loop machine-output contract
- **Reviewer(s)**: dyn-compat-mode-output.txt
- **Severity**: latent
- **Concern**: `plan-review-loop.md` says `SCOPE_ANCHOR_FILE` is emitted, but the normative Machine output KV table omits it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-compat-mode-output.txt: Add `SCOPE_ANCHOR_FILE` to the machine-output table and the durable-handoff key list beside the existing scope-anchor section.


### FINDING_5: Add tagged scope-reduction tally threshold regressions
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Tally tests do not prove tagged `[SCOPE-REDUCTION]` findings follow unchanged acceptance/rejection thresholds, including the original “scope reduction can win” failure mode.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add cases: tagged YES=1 NO=1 neutral; tagged YES less than NO rejected; tagged OOS no special handling.
  - From cursor-specialist-testing-output.txt: Add ballot fixtures with tagged Concern lines; assert neutral tie, rejection, exoneration, and OOS non-special-case match untagged baselines.
  - From cursor-specialist-plan-fidelity-output.txt: Add tally or loop stub test where tagged scope-reduction finding is accepted under normal thresholds


### FINDING_6: Expand plan-review loop/scope-anchor integration coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-marker-flow-output.txt
- **Severity**: important
- **Concern**: Core planned loop regressions—malformed plan strip aborts, outline append, tagged dedup/parity, aggregation fallback, ballot renumbering, inline emitter chain, and artifact copying—are not covered by the main loop or scope-anchor harnesses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Implement planned cases in test-plan-review-scope-anchor.sh or test-plan-review-loop.sh stubs.
  - From cursor-specialist-testing-output.txt: Add stub-loop fixtures for each plan bullet; assert exit codes, artifact copies, and ballot heading sequences.
  - From cursor-specialist-plan-fidelity-output.txt: Add the plan-listed fixtures to test-plan-review-loop.sh
  - From dyn-marker-flow-output.txt: Add the planned fixtures to `test-plan-review-loop.sh` (or extend `test-plan-review-scope-anchor.sh`) covering many-to-one parity failure and both-tagged dedup collapse.


