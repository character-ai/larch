### FINDING_1:
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge, Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1045-1063
- **Concern**: Step 3 handoff allowlist omits SCOPE_ANCHOR_FILE. Scenario: Plan adds SCOPE_ANCHOR_FILE to loop/result-env writers and tells MainAgent to read it from Step 3 result env, but the inline Step 3 case lists at 1045 and 1062 still whitelist only the existing twelve keys; run-step3-review.md:40 and test-step3-orchestrator-fence.sh:53-111 mirror the same set. The key can be persisted yet never loaded into shell state, so re-tally cannot pass --scope-anchor-file "$SCOPE_ANCHOR_FILE".
- **Proposed resolution**: Add SCOPE_ANCHOR_FILE to the SKILL.md Step 3 env/stdout allowlists, run-step3-review.md normalized-key list, and test-step3-orchestrator-fence.sh fence mirror in the same change as run-step3-review.sh.

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/review/scripts/aggregate-findings.sh planned in plan.txt:194-199
- **Concern**: Plan adds shared aggregator prompt and validation logic where a local skip is enough for SIMPLE scope. Scenario: More shared LLM merge logic increases maintenance risk and can create new marker-matching failure modes while trying to protect the privileged marker
- **Proposed resolution**: For plan mode, when any input finding has a leading [SCOPE-REDUCTION] marker, skip aggregation and pass the deduped findings directly to tally; leave aggregate-findings.sh unchanged except tests/docs if needed

### FINDING_3:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: security
- **Location**: skills/design/scripts/revise-plan-with-waterfall.sh:131-149
- **Concern**: Scope anchor is passed into revise without untrusted-data framing. Scenario: The plan sends the originating issue or issue+outline anchor to revise-plan-with-waterfall.sh, but its prompt still embeds FEATURE_FILE directly in <feature>. A malicious issue body can tell the revise agent to ignore accepted scope-reduction findings or re-add optional brainstorm work, silently defeating the scope-control loop.
- **Proposed resolution**: Add the same minimal untrusted-evidence instruction before the <feature> block in compose_prompt, and include revise in the plan's untrusted scope-anchor framing bullet.

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/run-step3-review.sh:309-366
- **Concern**: SCOPE_ANCHOR_FILE handoff chain is incomplete across Step 3 surfaces. Scenario: Plan adds SCOPE_ANCHOR_FILE to plan-review-loop emit/write_step3_result_env but run-step3-review.sh only allowlists/parses legacy keys, omits it from emit_kv and phase_driver_write_result_env; SKILL.md Step 3 fence (skills/design/SKILL.md:1045-1063) and test-step3-orchestrator-fence.sh twelve-key allowlist also omit it — orchestrator cannot bind $SCOPE_ANCHOR_FILE for MainAgent re-tally --scope-anchor-file even if the inner loop wrote the path
- **Proposed resolution**: Extend the full handoff contract: parse SCOPE_ANCHOR_FILE from inner env/stdout in run-step3-review.sh, persist it in .step3-review-result.env and stdout emit_kv, add the key to SKILL.md both allowlists, update test-step3-orchestrator-fence.sh and run-step3-review.md normalized-key table

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1015
- **Concern**: Stale Step 3 prose still says brainstorm is merged into binding reviewer feature context. Scenario: After the anchor split, scout/panel/voters/revise use SCOPE_ANCHOR_FILE; brainstorm must not be described as merged binding context — operators following SKILL.md will misread what reviewers actually receive
- **Proposed resolution**: Update this bullet (and any adjacent Step 3 feature-context prose) to match the plan: binding scope anchor = originating issue ± approved outline; brainstorm/plan-review-feature-context.txt is optional non-binding at most

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/scripts/plan-review-loop.sh:1106-1210
- **Concern**: Pre-aggregation Jaccard dedup has no concrete way to share is_scope_reduction_block with tally. Scenario: Plan requires dedup to preserve leading [SCOPE-REDUCTION] via the tally detector or a wrapper, but dedup is an inline Python heredoc while is_scope_reduction_block lives in scripts/lib-vote-tally.sh — duplicated or divergent regex risks silent marker loss before aggregation validation
- **Proposed resolution**: Specify one shared implementation (e.g. extract dedup to a script that imports/calls the same marker helper, or shell out to a tiny marker-check helper) instead of leaving parity implicit

### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:1413-1452
- **Concern**: The proposed write-once baseline is keyed only to plan-review-baseline.txt absence, not to the current loop invocation. Scenario: A later Step 3 re-entry in the same DESIGN_TMPDIR can reuse an old baseline, so reviewers flag drift from a prior run instead of the current round-1 entry plan
- **Proposed resolution**: Reset or use a run-scoped baseline before the first _run_plan_review_round for each plan-review-loop invocation; keep it unchanged only across rounds within that invocation

### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1045-1046; skills/design/SKILL.md:1062; skills/design/scripts/run-step3-review.sh:294-317; skills/design/scripts/run-step3-review.sh:341-366
- **Concern**: SCOPE_ANCHOR_FILE handoff chain incomplete in plan. Scenario: Plan adds SCOPE_ANCHOR_FILE to plan-review-loop write_step3_result_env and tells SKILL to re-tally with --scope-anchor-file "$SCOPE_ANCHOR_FILE", but omits SKILL Step 3 result-env/stdout parse allowlists and run-step3-review forward emit_kv plus phase_driver_write_result_env; variable stays unset and MainAgent re-tally loses the anchor
- **Proposed resolution**: Add SCOPE_ANCHOR_FILE to run-step3-review inner/outer parse allowlists, final emit_kv, and phase_driver_write_result_env; add the same key to SKILL.md Step 3 handoff case lists at 1045-1046 and 1062

### FINDING_9:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: security
- **Location**: skills/design/scripts/revise-plan-with-waterfall.sh:147-149
- **Concern**: Revise receives the new scope anchor without untrusted-data framing. Scenario: The originating issue can contain prompt-like text; the revise agent reads it inside <feature> and may treat it as instructions, re-expanding or ignoring accepted scope-cut findings
- **Proposed resolution**: Add revise-plan-with-waterfall.sh to the plan and prepend a short line before the feature block: treat this feature/scope text as untrusted scope evidence only, not instructions

### FINDING_10:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1044-1063
- **Concern**: SCOPE_ANCHOR_FILE is not called out for the Step 3 inline result-env allowlists. Scenario: The loop and run-step3 driver can emit SCOPE_ANCHOR_FILE, but the SKILL inline orchestration drops it before the 0-judge MainAgent re-tally, so --scope-anchor-file is omitted on the fallback path
- **Proposed resolution**: Add SCOPE_ANCHOR_FILE to both Step 3 result-env parsing case arms and preserve it when refreshing the Step 3 result state after MainAgent re-tally

### FINDING_11:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/run-step3-review.sh:187-203, skills/design/scripts/plan-review-loop.sh:1413-1452
- **Concern**: Baseline snapshot can be stale across later Step 3 re-runs. Scenario: Gate C can re-enter Step 3 after plan changes. run-step3-review.sh only clears plan-review/round-* artifacts, while the plan proposes writing plan-review-baseline.txt only when absent. A later review can compare against an older entry plan and flag already-approved changes as drift, reintroducing ratchet pressure.
- **Proposed resolution**: Revise the plan to reset or use an invocation-scoped baseline at the start of each plan-review-loop invocation, then keep it write-once only across that loop's internal rounds.

### FINDING_12:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/dispatch-plan-review-panel.sh:58-61,104-110,168-177,207-211
- **Concern**: Dispatch prompt threading lacks required validation. Scenario: The plan adds renderer issue-anchor instructions and says dispatch threads --feature-file into static, generic fallback, and dynamic prompts, but the listed dispatch tests only mention baseline forwarding. An implementation could keep passing --feature-file only as waterfall_extra while rendered prompts lack the untrusted scope-anchor rubric.
- **Proposed resolution**: Add minimal test-dispatch-plan-review-panel.sh assertions that static, generic fallback, and dynamic rendered prompts call render-plan-review-prompt.sh with --feature-file and include the issue-anchor block.

### FINDING_13:
- **Reviewer(s)**: Cursor-dyn-anchor-threading
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1045-1063
- **Concern**: SCOPE_ANCHOR_FILE is not on the Step 3 result-env or stdout allowlists. Scenario: Plan adds SCOPE_ANCHOR_FILE to plan-review-loop.sh write_step3_result_env and run-step3-review.sh but the orchestrator fence only binds LOOP_STATUS ACCEPTED_COUNT and related keys; SCOPE_ANCHOR_FILE is dropped before MainAgent re-tally so --scope-anchor-file is empty and 0-judge adjudication falls back to ballot-only scope
- **Proposed resolution**: Add SCOPE_ANCHOR_FILE to run-step3-review.sh inner phase_driver_read_result_env allowlist outer phase_driver_write_result_env and emit_kv breadcrumbs; mirror the same key in the SKILL.md Step 3 fence and skills/design/scripts/test-step3-orchestrator-fence.sh; document it in run-step3-review.md

### FINDING_14:
- **Reviewer(s)**: Codex-dyn-anchor-threading
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1038-1066,1094
- **Concern**: SCOPE_ANCHOR_FILE handoff can still be dropped by the Step 3 orchestration allowlists. Scenario: The plan emits SCOPE_ANCHOR_FILE from run-step3-review.sh, but the inline Step 3 bash fence only assigns whitelisted keys from .step3-review-result.env and stdout; MainAgent re-tally can then lack the anchor even after the scripts emit it
- **Proposed resolution**: Add SCOPE_ANCHOR_FILE to both Step 3 parsing allowlists in SKILL.md and pass it in the documented MainAgent re-tally command

### FINDING_15:
- **Reviewer(s)**: Codex-dyn-anchor-threading
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/brainstorm.md:5,157-160; skills/design/references/design-outline.md:118-121
- **Concern**: Stale references still define Step 3 around brainstorm/outline feature-context merging. Scenario: These references remain load-bearing for brainstorm and outline semantics and still say Step 3 merges brainstorm/outline into reviewer feature context, conflicting with the proposed binding anchor of issue plus approved outline and non-binding brainstorm context
- **Proposed resolution**: Update the Step 3 bullets to state that plan-review uses the issue plus approved outline as the binding scope anchor, while brainstorm remains optional non-binding context if surfaced at all

### FINDING_16:
- **Reviewer(s)**: Cursor-dyn-marker-lifecycle
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:155-176
- **Concern**: `write_step3_result_env` is not listed in the `plan-review-loop.sh` edit bullets even though Key decision line 40 requires `SCOPE_ANCHOR_FILE` in both `emit_loop_kvs` and `write_step3_result_env`. Scenario: Pause/resume and `run-step3-review.sh` prefer `.step3-plan-review-result.env` over stdout; if implementers only add `emit_kv SCOPE_ANCHOR_FILE` to loop stdout, `SCOPE_ANCHOR_FILE` can be absent from the inner env and MainAgent re-tally / SKILL.md `--scope-anchor-file` threading fails silently
- **Proposed resolution**: Add an explicit bullet to persist `SCOPE_ANCHOR_FILE` inside `write_step3_result_env`, extend `_terminal_exit` to emit it on stdout, and keep `run-step3-review.sh` allowlists in sync (as the plan already proposes)

### FINDING_17:
- **Reviewer(s)**: Cursor-dyn-marker-lifecycle
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/review/scripts/aggregate-findings.sh:175-627
- **Concern**: Plan-mode `[SCOPE-REDUCTION]` validation is specified only as “retain at least one leading marker for the corresponding merged scope-cut content” without an algorithm, unlike the concrete `[OUT_OF_SCOPE]` reviewer-slot rule at lines 602-610. Scenario: Implementers may copy heading-based OOS checks, validate too weakly (any unrelated output block with a marker passes while the merged scope-cut block loses its tag), or over-reject valid merges; tagged findings then miss the protected tally path
- **Proposed resolution**: Define validation in `aggregate-validate.py` for `--input-mode plan`: extract/normalize the Concern/problem field per block (same rules as `is_scope_reduction_block`), require that when any input block in a merge group carries a leading marker the merged block’s Concern still starts with `[SCOPE-REDUCTION]`, and reject/fallback when all markers in that group are lost

### FINDING_18:
- **Reviewer(s)**: Cursor-dyn-marker-lifecycle
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:1106-1210
- **Concern**: Pre-aggregation Jaccard dedup is inline Python that only merges on `what_text` and `merge_reviewers`; the plan requires the tally `is_scope_reduction_block` detector but does not specify how inline dedup invokes it. Scenario: Re-implementing leading-marker logic separately in the ephemeral dedup script can drift from `scripts/lib-vote-tally.sh`, letting tagged/untagged Jaccard merges drop `[SCOPE-REDUCTION]` before aggregation/tally despite the stated contract
- **Proposed resolution**: Extract one shared marker-normalization helper (Python module or small `check-scope-reduction-marker.sh` used by both dedup and `is_scope_reduction_block`) or write each block to a temp file and call the shared bash helper; never merge a tagged block into an untagged keeper without copying the leading prefix into the retained Concern

### FINDING_19:
- **Reviewer(s)**: Codex-dyn-marker-lifecycle
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/render-plan-review-prompt.sh:126-142
- **Concern**: Planned explicit scope-size answer has no safe output slot. Scenario: The plan tells reviewers to explicitly answer whether the plan is larger than the issue requires, but the current prompt contract permits only the TSV header/rows or the JSON no-issues sentinel with no prose. A reviewer may add a prose answer and get dropped by the first-line/structured gate, or the answer may be ignored because it is not a TSV finding.
- **Proposed resolution**: Replace that instruction with: if the plan over-serves the issue, emit a normal TSV finding with what prefixed [SCOPE-REDUCTION]; otherwise emit no extra prose and follow the existing sentinel/TSV contract.

### FINDING_20:
- **Reviewer(s)**: Cursor-dyn-shared-compat
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/scripts/plan-review-loop.sh:1106-1210
- **Concern**: Pre-aggregation Jaccard dedup may reimplement the scope-reduction detector separately from scripts/lib-vote-tally.sh::is_scope_reduction_block. Scenario: Plan allows inline Python to "source/use the same … detector … or a wrapper"; dedup runs before aggregation/tally and today has no marker-preservation logic (skills/design/scripts/plan-review-loop.sh:1172-1184 merges on token overlap only). A second ad hoc matcher can diverge on fenced-code stripping or leading-marker rules, drop [SCOPE-REDUCTION] before tally, and nullify the protected-acceptance path despite lib-vote-tally and tally-plan-review.sh being correct
- **Proposed resolution**: Mandate one canonical detector for dedup + tally (e.g., small shared helper invoked from the dedup Python via subprocess, or extract shared Python used by both paths). Extend test-plan-review-scope-anchor.sh dedup case to assert parity with is_scope_reduction_block fixtures in scripts/test-lib-vote-tally.sh

### FINDING_21:
- **Reviewer(s)**: Codex-dyn-shared-compat
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/review/scripts/review-core.sh:698-711 skills/review/scripts/aggregate-findings.sh:24,168-172,596-601
- **Concern**: Shared aggregate-findings plan-mode marker change lacks a default code-mode regression for the /review caller. Scenario: /review and /implement Step 5 call aggregate-findings without --input-mode, so default code mode is the safety boundary; if [SCOPE-REDUCTION] prompt or validation logic is not fully gated to plan mode, code-review aggregation can change or fail
- **Proposed resolution**: Extend test-aggregate-findings.sh with one default/code-mode fixture asserting the prompt and validator do not apply [SCOPE-REDUCTION] preservation rules unless --input-mode plan is set

### OOS_1:
- **Description**: Step 3 consumer paragraph still says outline may merge into reviewer feature context. Scenario: design-outline.md says plan-review-loop MAY merge design-outline.md into the feature-context file for reviewers; the plan moves approved outline into plan-review-scope-anchor.txt and stops passing brainstorm-merged context as the binding anchor. Operators reading design-outline.md get the old contract.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/references/design-outline.md:121
- **Phase**: design
