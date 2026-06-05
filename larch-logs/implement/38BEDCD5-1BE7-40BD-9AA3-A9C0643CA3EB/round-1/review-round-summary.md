# Review Round 1

- Mode: `diff`
- 19 accepted, 4 rejected (3 exonerated)

## Accepted Findings

### FINDING_1: Makefile declares new harnesses as .PHONY only
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-scope-marker-output.txt
- **Severity**: important
- **Concern**: New harness targets are listed in `.PHONY` but lack Makefile recipes and shard membership, so `make lint` does not run the new marker / strip / scope-anchor regressions and some documented `make test-*` targets fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-scope-marker-output.txt: Add recipe targets (same pattern as `test-plan-block:`) and register them in a harness shard, or invoke `test-check-scope-reduction-marker.sh` from an already-sharded harness such as `test-plan-review-loop`.


### FINDING_10: Reviewer prompt inlines raw scope-anchor text without redaction or delimiter hardening
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-prompt-boundary-output.txt
- **Severity**: important
- **Concern**: `render-plan-review-prompt.sh` wraps collaborator-controlled scope-anchor text in plain `<scope-anchor>` tags without `redact-secrets.sh`, angle-bracket escaping, collision-resistant tags, or explicit tag-like-content instructions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From dyn-prompt-boundary-output.txt: Reuse the specialist-renderer pattern: pipe staged anchor text through `redact-secrets.sh` and markup escaping, wrap it with the canonical “tag-like content” preamble, prefer namespaced tags such as `<reviewer_feature_description>`, and add harness cases that assert a payload containing `</scope-anchor>` plus instruction text cannot break the envelope.


### FINDING_11: Voter prompt newly inlines raw full scope anchor
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-prompt-boundary-output.txt
- **Severity**: important
- **Concern**: `render-voter-prompt.sh` now sends full issue-scope text inline to voter prompts without redaction, escaping, or delimiter-breakout hardening, expanding third-party exposure and injection risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From dyn-prompt-boundary-output.txt: Either keep voters on path-only ballot access and supply scope only through hardened, redacted, escaped blocks—or, if inline scope is required, apply the same `redact_untrusted_stream` / `emit_untrusted_file_block` helper used by `scripts/render-specialist-prompt.sh:226-237`, include the canonical tag-like-content instruction, and add regression tests for delimiter-breakout payloads.


### FINDING_12: Scope-anchor staging omits secret redaction
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-prompt-boundary-output.txt
- **Severity**: important
- **Concern**: `plan-review-loop.sh` materializes `plan-review-scope-anchor.txt` from issue text with only plan-block stripping, so secrets in issue bodies can be forwarded verbatim to reviewers, voters, revise, and fallback paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From dyn-prompt-boundary-output.txt: Redact (and optionally escape) anchor contents at materialization time, or immediately before each prompt render, and add a harness fixture proving tokens in the issue body are scrubbed before voter/reviewer prompts are emitted.


### FINDING_13: Revise prompt raw-inlines untrusted feature / scope text
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-prompt-boundary-output.txt
- **Severity**: important
- **Concern**: `revise-plan-with-waterfall.sh` adds framing but still embeds untrusted feature/scope text in `<feature>` without redaction, escaping, or delimiter-hardening; this can steer write-capable revise lanes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From dyn-prompt-boundary-output.txt: Apply the same untrusted-payload pipeline as `render-specialist-prompt.sh` to the feature block (minimum: redact + escape + tag-like-content preamble), consider path-based indirection instead of inline for large anchors, and extend `scripts/test-revise-plan-with-waterfall.sh` with an assertion for untrusted framing plus a delimiter-breakout fixture (the plan promised this coverage, but the harness currently has no `untrusted` assertions).


### FINDING_14: PR line-count script lacks strict REPO / PR_NUMBER validation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `compute-pr-line-counts.sh` interpolates `REPO` and `PR_NUMBER` into `gh api` endpoints without strict format validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_17: Ballot renumber failure aborts instead of falling back
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-plan-aggregation-output.txt
- **Severity**: important
- **Concern**: Final ballot renumbering can raise under `set -e`, aborting the whole round on duplicate / malformed headings instead of warning and falling back to pre-dedup or pre-aggregation findings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-plan-aggregation-output.txt: Wrap the ballot renumber step in explicit error handling: on duplicate-heading failure, log a warning, copy the parity fallback artifact (`findings-in-scope.pre-dedup.md`) or pre-aggregation backup into `findings-in-scope.md`, re-run renumber once, and only fail closed if the fallback stream is also invalid.


### FINDING_18: Step 3 / design-outline docs still describe pre-anchor scope flow
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-scope-anchor-flow-output.txt
- **Severity**: important
- **Concern**: Documentation still says reviewers receive brainstorm-merged feature context, contradicting the staged `plan-review-scope-anchor.txt` contract and risking orchestrator/operator misuse.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-scope-anchor-flow-output.txt: Replace line 1038 with the staged-anchor contract (strip `larch:plan`, append approved outline when present, brainstorm only in non-binding `plan-review-feature-context.txt`) so Step 3 launch prose matches `plan-review-loop.sh` and `references/plan-review.md`.
  - From dyn-scope-anchor-flow-output.txt: Update line 121 to state the approved outline is appended to `plan-review-scope-anchor.txt` when `.outline-approved` exists, not merged into binding reviewer feature context.


### FINDING_2: Dedup uses hardcoded marker helper path
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `plan-review-loop.sh` dedup hardcodes the plugin-root marker helper instead of using the already-resolved `SCOPE_MARKER_HELPER`, so fallback or override resolution can desync dedup from parity / aggregation marker checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_22: Step 3 handoff harness omits `SCOPE_ANCHOR_FILE`
- **Reviewer(s)**: dyn-scope-anchor-flow-output.txt, dyn-env-handoff-output.txt
- **Severity**: important
- **Concern**: `test-step3-orchestrator-fence.sh` mirrors the old durable-key contract and does not preserve / assert `SCOPE_ANCHOR_FILE`, so MainAgent fallback handoff regressions can pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-scope-anchor-flow-output.txt: Add `SCOPE_ANCHOR_FILE` to the display-pass allowlist and both file-first/later-wins parse arms in `test-step3-orchestrator-fence.sh`, with a fixture asserting the path survives handoff when the loop stub emits it.
  - From dyn-env-handoff-output.txt: Add `SCOPE_ANCHOR_FILE` to every allowlist/`unset` site in `test-step3-orchestrator-fence.sh` to match `SKILL.md`, add file-first vs stdout-fallback cases (including `main-agent-vote-required`), and extend `test-design-structure.sh` or the fence doc to pin key parity.


### FINDING_26: Marker-helper failures are silently treated as untagged
- **Reviewer(s)**: dyn-scope-marker-output.txt
- **Severity**: important
- **Concern**: Dedup / aggregation only check `returncode == 0`; helper failures are indistinguishable from “not tagged,” so real scope-reduction findings can lose marker-aware treatment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-scope-marker-output.txt: Fail closed or log loudly when the helper exits unexpectedly (e.g. distinguish exit 1 vs 2+, surface a WARN and skip dedup merge for that block, or fall back to the pre-dedup snapshot).


### FINDING_28: Tagged-block preservation validation is count-only
- **Reviewer(s)**: dyn-plan-aggregation-output.txt
- **Severity**: important
- **Concern**: `aggregate-findings.sh` validates tagged preservation by count rather than ensuring each original tagged block survives as a distinct tagged block in the combined stream.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-plan-aggregation-output.txt: After building the combined stream, require a one-to-one match from each block in `aggregate-scope-reduction-tagged.md` to a distinct combined block that `check-scope-reduction-marker.sh` still detects (reuse the parity-style normalized token overlap used in `plan-review-loop.sh`, or compare block bodies directly), and fail closed with full input restore when any tagged input is unmatched.


### FINDING_29: Post-dedup parity gate is weaker than the plan contract
- **Reviewer(s)**: dyn-plan-aggregation-output.txt
- **Severity**: important
- **Concern**: The parity gate matches tagged pre/post blocks using Concern-token Jaccard only, not reviewer overlap plus normalized problem-token overlap, and can mask intended-block marker loss.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-plan-aggregation-output.txt: Require both reviewer-set overlap and normalized problem-token Jaccard when pairing pre/post tagged blocks, and treat “matched block lost leading marker” as parity failure so the pre-dedup snapshot is restored before aggregation.


### FINDING_3: Plan-required harness coverage is incomplete across scope-anchor and marker flows
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-scope-anchor-flow-output.txt, dyn-scope-marker-output.txt, dyn-plan-aggregation-output.txt, dyn-env-handoff-output.txt, dyn-prompt-boundary-output.txt
- **Severity**: important
- **Concern**: Multiple acceptance-plan harness cases are missing, including voter dispatch forwarding, revise framing, scout/voter argv assertions, collect-to-detector severity-prefix coverage, dedup/parity/ballot regressions, tally threshold cases, env-handoff validation, and delimiter-breakout prompt tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From dyn-scope-anchor-flow-output.txt: Add cases that invoke `dispatch-plan-voters.sh` with a readable scope-anchor file, assert generated voter prompt files contain inlined anchor text, and assert omission leaves prompts byte-identical to the no-flag baseline.
  - From dyn-scope-anchor-flow-output.txt: Add a case that runs `compose_prompt` (or captures `plan-review/round-1/revise/prompt.txt`) with `--feature-file` set to a staged scope anchor and asserts the untrusted-evidence line appears immediately before `<feature>`.
  - From dyn-scope-anchor-flow-output.txt: Extend the brainstorm fixture to grep `PLAN_REVIEW_SCOUT_ARGV_LOG` for `--description-file` pointing at `plan-review-scope-anchor.txt`, and add a voter stub argv log assertion for `--scope-anchor-file` with the same path.
  - From dyn-scope-marker-output.txt: Add stubbed-loop cases with TSV `what: [SCOPE-REDUCTION] …`, assert `findings-in-scope.pre-dedup.md` / post-dedup marker survival, parity fallback, and ballot renumbering.
  - From dyn-scope-marker-output.txt: Add a collect fixture plus a call to `check-scope-reduction-marker.sh` on the emitted block.
  - From dyn-scope-marker-output.txt: Add tally harness cases using blocks that pass `is_scope_reduction_block` and assert `classify_result` / acceptance behavior is unchanged.
  - From dyn-env-handoff-output.txt: Add integration cases with a real or stub loop that writes inner env including `SCOPE_ANCHOR_FILE`, assert file-first precedence and MainAgent-relevant non-empty values, and negative path/CR-LF cases.


### FINDING_30: Inner Step 3 result-env writer skips phase-driver safety guards
- **Reviewer(s)**: dyn-env-handoff-output.txt
- **Severity**: important
- **Concern**: `write_step3_result_env` uses raw `printf` + `mv` instead of `phase_driver_write_result_env`, so the inner env handoff skips symlink refusal and CR/LF validation while now carrying `SCOPE_ANCHOR_FILE`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-env-handoff-output.txt: Route inner env writes through `phase_driver_write_result_env` (or share its validation), or sanitize `SCOPE_ANCHOR_FILE` immediately before every inner/outer emit/write.


### FINDING_31: `run-step3-review.sh` forwards unconfined `SCOPE_ANCHOR_FILE`
- **Reviewer(s)**: dyn-env-handoff-output.txt
- **Severity**: important
- **Concern**: After parsing inner env/stdout, the driver emits and persists `SCOPE_ANCHOR_FILE` without canonicalizing and requiring it to remain under `$DESIGN_TMPDIR`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-env-handoff-output.txt: Before emit/write, canonicalize and require `SCOPE_ANCHOR_FILE` under `$DESIGN_TMPDIR` (and reject CR/LF); clear or fail closed when validation fails, with harness cases for out-of-tmpdir and malformed paths.


### FINDING_32: `phase_driver_read_result_env` silently drops CR/LF values
- **Reviewer(s)**: dyn-env-handoff-output.txt
- **Severity**: important
- **Concern**: CR/LF-containing allowlisted values are skipped without a warning, so `SCOPE_ANCHOR_FILE` can vanish silently at the inner-to-driver boundary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-env-handoff-output.txt: Emit an explicit WARN when a requested key is skipped for CR/LF, or fail closed for durable handoff keys like `SCOPE_ANCHOR_FILE`.


### FINDING_8: Scope-anchor materialization hides malformed plan-strip detail
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `plan-review-loop.sh` does not propagate `MALFORMED=` output from `plan-block-strip-body.sh`, leaving operators with a generic strip failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_9: Plan-mode aggregation can overwrite inputs before tagged-block validation succeeds
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-plan-aggregation-output.txt
- **Severity**: important
- **Concern**: `aggregate-findings.sh` writes the LLM merge to `findings-in-scope.md` before tagged `[SCOPE-REDUCTION]` blocks are appended and validated; marker / renumber failure can leave an untagged-only file and drop tagged findings from ballots.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From dyn-plan-aggregation-output.txt: Snapshot `FINDINGS_FILE` before the plan-mode `mv` (or defer the `mv` until after tagged append + marker validation succeed). On marker/renumber failure, restore the snapshot, emit `AGGREGATED=false`, and leave the caller with the pre-aggregation in-scope file unchanged.


