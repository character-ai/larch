### FINDING_1: Extract duplicated plan-review-loop dedup/parity/renumber Python
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `plan-review-loop.sh` embeds multiple inline Python heredocs and duplicate ballot-renumber logic, making marker/dedup/parity behavior difficult to test and maintain.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract a committed findings dedup/parity/renumber module; invoke once from plan-review-loop.sh; delete duplicate ballot-renumber heredoc.

### FINDING_2: Add voter dispatch scope-anchor forwarding regressions
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `dispatch-plan-voters.sh` forwarding of `--scope-anchor-file` is untested, so voters could silently lose issue-scope anchoring.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add harness cases asserting --scope-anchor-file is forwarded and omission preserves byte-identical prompts.
  - From cursor-specialist-testing-output.txt: Add harness cases that assert --scope-anchor-file appears in all voter prompt render argv (including retry) and that omission preserves byte-identical prompts.
  - From cursor-specialist-plan-fidelity-output.txt: Add harness cases asserting --scope-anchor-file is forwarded on all render paths and omitted when unset

### FINDING_3: Assert panel prompts actually contain scope-anchor framing
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Panel tests only check argv forwarding, not that rendered reviewer prompts include the binding issue anchor, untrusted evidence framing, or scope-reduction instructions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extend harness to inspect rendered prompt files for untrusted scope evidence and [SCOPE-REDUCTION] instructions.
  - From cursor-specialist-testing-output.txt: Capture rendered prompt; assert binding scope anchor / untrusted evidence sections.

### FINDING_4: [OUT_OF_SCOPE] Add collect-to-marker regression for severity-prefixed scope-reduction concerns
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, dyn-marker-flow-output.txt
- **Severity**: important
- **Concern**: The collect path lacks a regression proving TSV `what:[SCOPE-REDUCTION]` or severity-prefixed `[SCOPE-REDUCTION]` Concern lines remain detectable downstream.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add fixture asserting collect output is detected by check-scope-reduction-marker.sh.
  - From cursor-specialist-testing-output.txt: Add test: collect output -> check-scope-reduction-marker.sh exit 0 for [important] [SCOPE-REDUCTION] Concern.
  - From dyn-marker-flow-output.txt: Address the concern above.

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

### FINDING_7: [OUT_OF_SCOPE] Unify duplicated scope-reduction marker detector entrypoints
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-bash-portability-output.txt
- **Severity**: important
- **Concern**: `check-scope-reduction-marker.sh` duplicates the same Python detector for stdin and `--file`, creating drift risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Unify to one Python entrypoint reading argv path or stdin.
  - From dyn-bash-portability-output.txt: Address the concern above.

### FINDING_8: Extract aggregate-findings tagged-block helper logic
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Plan-mode aggregation scatters marker preservation logic across multiple inline Python blocks using subprocess/tempfile detector calls.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract shared Python helper for split/append/renumber/validate tagged blocks.

### FINDING_9: [OUT_OF_SCOPE] Clean up unused/misleading `is_scope_reduction_block` API
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-marker-flow-output.txt, dyn-bash-portability-output.txt, dyn-compat-mode-output.txt
- **Severity**: latent
- **Concern**: `is_scope_reduction_block` is documented as shared tally surface but has no production callers and its parameter name suggests inline markdown even though it expects a file path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Remove wrapper or wire all marker checks through it; rename to block_file if kept.
  - From dyn-marker-flow-output.txt: Address the concern above.
  - From dyn-bash-portability-output.txt: Rename the parameter/doc to `block_file`, or write the block body to a `mktemp` under `$TMPDIR` and pass that path (with trap cleanup), matching how the Python deduper already invokes the helper.
  - From dyn-compat-mode-output.txt: Either wire the helper only where needed (dedup/aggregation) and trim the lib-vote-tally export/docs, or document it explicitly as test-only until tally consumes it.

### FINDING_10: Factor duplicated larch:plan marker-count validation
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `plan-block-strip-body.sh` duplicates malformed marker-counting logic from `plan-block-read.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Optionally factor shared marker-count helper used by read and strip.

### FINDING_11: [OUT_OF_SCOPE] Split unrelated PR line-count feature from scope-anchor work
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-scope-flow-output.txt, dyn-compat-mode-output.txt
- **Severity**: important
- **Concern**: The branch includes unrelated PR line-count/reporting changes alongside scope-anchor work, increasing review noise and isolation risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Split features in PR description or separate commits/branches going forward.
  - From cursor-specialist-plan-fidelity-output.txt: Split #3506 into a separate PR or revert compute-pr-line-counts/render-run-summary/write-final-report changes from this branch
  - From dyn-scope-flow-output.txt: Address the concern above.
  - From dyn-compat-mode-output.txt: Address the concern above.

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

### FINDING_14: Add revise prompt untrusted scope-evidence regression
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The revise harness does not assert the new untrusted scope-evidence preamble before the feature block.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: grep revise prompt for untrusted scope evidence only line added in compose_prompt.

### FINDING_15: [OUT_OF_SCOPE] Add run-step3 IMPLEMENT_TMPDIR precedence test
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-scope-flow-output.txt
- **Severity**: important
- **Concern**: `test-run-step3-review.sh` does not prove `DESIGN_TMPDIR/feature-description.txt` wins over stale `IMPLEMENT_TMPDIR` state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Stub loop with decoy IMPLEMENT_TMPDIR; assert --feature-file uses DESIGN_TMPDIR/feature-description.txt.
  - From dyn-scope-flow-output.txt: Address the concern above.

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

### FINDING_19: Harden raw plan/findings bodies in revise prompt
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `revise-plan-with-waterfall.sh` hardens feature scope text but still leaves plan and findings bodies raw in the same prompt.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Apply redact_untrusted_stream to plan/findings sections or wrap them in escaped literal-redacted blocks

### FINDING_20: Make anchored voter proportionality override legacy EXONERATE guidance
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-compat-mode-output.txt
- **Severity**: important
- **Concern**: With `--scope-anchor-file`, voter prompts still include finding-relative EXONERATE guidance before the issue-scope anchor, preserving the addition-biased failure mode.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: When --scope-anchor-file is set, rewrite or reorder proportionality guidance so issue-scope rules override the legacy finding-anchored EXONERATE line
  - From dyn-compat-mode-output.txt: When a readable scope anchor is inlined, replace or qualify the global EXONERATE lines so proportionality is explicitly measured against the originating issue scope (mirror the `[SCOPE-REDUCTION]` problem-first rubric), and add a harness assertion that the finding-relative wording does not appear unchanged on the anchored path.

### FINDING_21: Add revise staged-anchor argv assertion
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The planned loop test does not assert revise receives the staged `plan-review-scope-anchor.txt` path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Log revise argv in loop stub and assert plan-review-scope-anchor.txt is passed

### FINDING_22: Fail closed when run-step3 scope-anchor handoff validation rejects a non-empty path
- **Reviewer(s)**: dyn-scope-flow-output.txt
- **Severity**: important
- **Concern**: `validate_scope_anchor_handoff` clears invalid `SCOPE_ANCHOR_FILE` with only a warning, creating asymmetry where external judges saw anchored scope but MainAgent fallback may not.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-scope-flow-output.txt: Fail closed with a dedicated `LOOP_STATUS` / `TALLY_PLAN_REVIEW_STATUS` when a non-empty handoff path cannot be validated, or fall back to the canonical staged file `$DESIGN_TMPDIR/plan-review-scope-anchor.txt` when it exists and is a regular file under the design tmpdir, instead of clearing the key.

### FINDING_23: Remove or sanitize stale brainstorm feature-context sidecar
- **Reviewer(s)**: dyn-scope-flow-output.txt
- **Severity**: latent
- **Concern**: Brainstorm handling writes a sidecar feature-context file from unstripped original feature content, creating a latent alternate scope surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-scope-flow-output.txt: Either stop writing the sidecar until something actually consumes it, or build it from the same stripped anchor body (and keep brainstorm clearly non-binding) so no parallel feature narrative can become the accidental binding input.

### FINDING_24: [OUT_OF_SCOPE] Happy-path scope-anchor wiring appears sound
- **Reviewer(s)**: dyn-scope-flow-output.txt
- **Severity**: nit
- **Concern**: Happy-path wiring uses the design feature file, materializes a staged scope anchor, forwards it to scout/panel/voters/revise, and preserves voter retry prompts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-scope-flow-output.txt: Address the concern above.

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

### FINDING_29: [OUT_OF_SCOPE] Positive hardened prompt renderers
- **Reviewer(s)**: dyn-prompt-sandbox-output.txt
- **Severity**: nit
- **Concern**: Reviewer, voter, and revise prompt renderers add untrusted-data framing plus redaction and HTML escaping for scope-anchor embedding, with breakout regressions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-sandbox-output.txt: Address the concern above.

### FINDING_30: [OUT_OF_SCOPE] Positive anchor materialization and handoff guards
- **Reviewer(s)**: dyn-prompt-sandbox-output.txt
- **Severity**: nit
- **Concern**: Scope anchor materialization strips embedded plan blocks fail-closed, redacts secrets, rejects CR/LF paths, and constrains handoff under `DESIGN_TMPDIR`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-sandbox-output.txt: Address the concern above.

### FINDING_31: [OUT_OF_SCOPE] Residual disclosure risk from wider issue-body inlining
- **Reviewer(s)**: dyn-prompt-sandbox-output.txt
- **Severity**: latent
- **Concern**: `redact-secrets.sh` does not cover PII, internal URLs, or opaque bearer tokens, so wider issue-body inlining increases accidental disclosure risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-sandbox-output.txt: Address the concern above.

### FINDING_32: [OUT_OF_SCOPE] Document scope-anchor trust boundary in SECURITY.md
- **Reviewer(s)**: dyn-prompt-sandbox-output.txt
- **Severity**: nit
- **Concern**: `SECURITY.md` does not describe the new plan-review scope-anchor pipeline.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-sandbox-output.txt: Address the concern above.

### FINDING_33: Fail closed on aggregate-findings marker helper infrastructure failure
- **Reviewer(s)**: dyn-bash-portability-output.txt
- **Severity**: important
- **Concern**: Plan-mode aggregation treats marker helper failures like “not tagged,” routing tagged scope-reduction blocks into normal LLM aggregation instead of the preserved tagged sidecar.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-portability-output.txt: Mirror the deduper’s `is_tagged()` handling in `plan-review-loop.sh`: distinguish exit `1` (false) from infrastructure failure (non-0/1), log a WARN, and on helper failure fall back to the untagged+tagged split using the original input (or abort aggregation with `AGGREGATED=false`) rather than misclassifying tagged blocks.

### FINDING_34: Preserve strip-helper stderr for debuggability
- **Reviewer(s)**: dyn-bash-portability-output.txt
- **Severity**: nit
- **Concern**: Scope-anchor materialization suppresses `plan-block-strip-body.sh` stderr, hiding useful diagnostics behind a generic failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-portability-output.txt: Drop the stderr redirect (or tee stderr into `$DESIGN_TMPDIR/plan-strip.stderr` and append it to the `larch_err` message) while keeping stdout KV parsing unchanged.

### FINDING_35: Route strip-helper line-number failures through structured MALFORMED output
- **Reviewer(s)**: dyn-bash-portability-output.txt
- **Severity**: latent
- **Concern**: `plan-block-strip-body.sh` can abort under `pipefail` while resolving malformed marker line numbers instead of emitting a structured `MALFORMED=` token.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-portability-output.txt: Guard the pipeline with `set +e`, verify `start_line`/`end_line` are non-empty integers, and route empty/invalid results through `emit_malformed` (e.g. a dedicated token) instead of dying in the pipeline.

### FINDING_36: Avoid orphaned marker-detector temp files
- **Reviewer(s)**: dyn-bash-portability-output.txt
- **Severity**: nit
- **Concern**: Marker detector temp files are created under the default temp directory with `delete=False`, so crashes can leave orphan files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-portability-output.txt: Create temp files under `$DESIGN_TMPDIR` (or pass `dir=os.environ["DESIGN_TMPDIR"]` when set), and/or register an `atexit` cleanup list so marker-detector temp files cannot accumulate across long multi-round runs.

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

### FINDING_40: [OUT_OF_SCOPE] Add `--scope-anchor-file` to render-voter prompt flag docs
- **Reviewer(s)**: dyn-compat-mode-output.txt
- **Severity**: nit
- **Concern**: `render-voter-prompt.md` documents `--scope-anchor-file` in prose but omits it from the Flags table.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-compat-mode-output.txt: Address the concern above.

### FINDING_41: [OUT_OF_SCOPE] Positive compatibility isolation
- **Reviewer(s)**: dyn-compat-mode-output.txt
- **Severity**: nit
- **Concern**: Optional scope-anchor wiring appears isolated from code-review and no-flag voter defaults.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-compat-mode-output.txt: Address the concern above.
