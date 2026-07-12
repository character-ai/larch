### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/design/references/decompose-panel.md:11-16
- **Concern**: Resume-close still jumps straight to close-original and never names migrate-deps. Scenario: After filing succeeds but dependency migration is interrupted, §0 resume-close tells the orchestrator to rerun only close-original. The new flow requires migrate-deps and `.decompose-deps-migrated` before closure. Operators can loop on close failures or assume closure is the only retry step while external blocked-by edges on the original issue stay stale.
- **Proposed resolution**: Rewrite §0 resume-close: when `.decompose-issues-filed` exists and `.decompose-deps-migrated` is absent, run `decompose migrate-deps` (with live-graph verification) before any `close-original` attempt; only then allow resume-close to call `close-original`.

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: skills/design/references/decompose-panel.md
- **Concern**: Split-path lacks an executable migrate-deps invocation contract. Scenario: Approach step 7 defines migrate-deps behavior in Python, but the normative Split-path doc still documents prepare, annotate, and close-original fences only. Without argv, repo binding, and stdout KV parsing rows mirroring those helpers, prompt-side wiring can drift from `close_original_issue` preconditions and skip migration silently on some entry paths.
- **Proposed resolution**: Add a § migrate-deps fence to the rewritten decompose-panel.md: `python3 ... decompose migrate-deps --design-tmpdir "$DESIGN_TMPDIR" --original-issue "$ISSUE_NUMBER" --repo "$GITHUB_REPOSITORY"` (plus any annotation path flags the Python verb needs), required `DECOMPOSE_DEPS_*` rows, exit-code branching, and explicit ordering after annotate and before close-original.

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:175-176,360,scripts/test-design-structure.sh:613-614
- **Concern**: Stale panel-failure Split-path branches survive after inline-only rewrite. Scenario: The plan removes panel dispatch from Split-path but does not list updates to SKILL.md `PANEL_STATUS=panel-failed` / `failed-judge-panel` handling or the structure harness assertions that require those branches. Inline validation failure is only described as a generic recorded failure with no replacement `SUMMARY_OUTCOME`, terminal staging, or harness contract.
- **Proposed resolution**: Remove Split-path panel-failed Retry/Cancel and `failed-judge-panel` orchestration from SKILL.md; define one terminal outcome for inline partition validation exhaustion (stage + Final summary + preserve tmpdir); add `### UPDATED: scripts/test-design-structure.sh` (and finalize-step5-failures.md if it still ties `failed-judge-panel` to decompose-panel retry).

### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: skills/design/references/decompose-panel.md
- **Concern**: No canonical durable path for the inline partition proposal. Scenario: Step 4 runs `decompose prepare --partition-file` before the single operator question, but the plan never names where the main agent must write the `## Pieces` Markdown (current panel flow used vendor-specific paths and `operator-partition.md`). Pause/resume and prepare repair loops need one stable `<PARTITION_FILE>` under `$DESIGN_TMPDIR/decompose/`.
- **Proposed resolution**: Require writing the validated inline proposal to a single normative path (for example `$DESIGN_TMPDIR/decompose/inline-partition.md`), use it for every prepare rerun, persist it through operator acceptance, and document resume behavior when that file already exists.

### FINDING_5:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: correctness
- **Location**: skills/design/references/decompose-panel.md:172-176
- **Concern**: Rewritten filing section does not explicitly preserve intra-batch dependency Skill flags. Scenario: The plan keeps `partition-deps.tsv` but drops the current §7b contract that passes `--intra-batch-deps-file` and `--no-dep-llm` to `/larch:issue` batch mode. A rewrite that files from `partition-input.txt` alone would create sibling issues without declared intra-piece blocked-by edges even when the TSV is non-empty.
- **Proposed resolution**: State explicitly in the new §7b: when `partition-deps.tsv` is non-empty, invoke `/larch:issue` with `--intra-batch-deps-file "$DESIGN_TMPDIR/decompose/partition-deps.tsv"` and `--no-dep-llm`; omit `--intra-batch-deps-file` only when the TSV is empty (independent pieces).

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/design/references/finalize-step5.md
- **Concern**: Step 5c accepted partition may continue publish instead of terminal exit. Scenario: The plan routes publish-time oversize to the unified Split-path but says accepted partitioning follows filing, annotation, migration, and original closure before ordinary continuation. At Step 5c the original issue is closed and the monolithic plan is obviated; continuing Step 5c publish would target a closed issue or skip the approved-partition terminal contract used at Step 2b.5.
- **Proposed resolution**: State explicitly that Step 5c Split-path acceptance exports SUMMARY_OUTCOME=approved-partition, runs the Final summary block, and exits 0 like Step 2b.5; only Override reruns design-step5c.sh.

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: security
- **Location**: python/larch/design/decompose.py
- **Concern**: migrate-deps lacks session-backed live-mutation authorization. Scenario: Partition filing is session-gated via /larch:issue --context-file source-env.sh, but the new migrate-deps path will call block-issue add/remove directly from issue_block.py, which has no check_live_mutation_auth. A replayed or harness tmpdir could rewire production dependency graphs without LARCH_LIVE_MUTATION_OK.
- **Proposed resolution**: Require migrate-deps_main to validate source-env.sh with check_live_mutation_auth before any dependency read or block-issue mutation, refuse with stable DECOMPOSE_DEPS_STATUS rows on denial, and add a test proving zero gh calls when unauthorized.

### FINDING_9:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: skills/design/references/decompose-panel.md
- **Concern**: Resume-close idempotency omits migrate-deps retry. Scenario: The rewritten flow requires migrate-deps and .decompose-deps-migrated before close-original, but section 0 still resumes with close-original only when .decompose-issues-filed exists. After a comment-post hiccup with migration already complete this is fine; after filing without migration it forces a failing close-original retry instead of converge migrate-deps.
- **Proposed resolution**: Update section 0 so resume-close runs migrate-deps when the filing sentinel exists and the migration sentinel is absent, then close-original only after migration postconditions verify.

### FINDING_10:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/design/references/decompose-panel.md:41-46; plan.txt:164-170
- **Concern**: The validation-failure path can terminate before emitting the required single partition question. Scenario: If inline repair cannot produce a valid multi-piece acyclic proposal, the plan says to terminate the Split-path with a recorded failure. That leaves the operator with zero questions, while the feature requires every partition process to present exactly one question and offer the partition, override, or other/chat outcomes
- **Proposed resolution**: Define a terminal fallback that still emits exactly one AskUserQuestion when proposal validation cannot be repaired, or explicitly route the failure through one existing partition question before terminating; add a test for unrecoverable proposal validation failure

### FINDING_11:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/design/references/decompose-panel.md
- **Concern**: Partition filing must always pass --no-dep-llm with proposal-authoritative deps. Scenario: Removing prepare's automatic serial edges means an empty or sparse partition-deps.tsv no longer forces execution order. The current Split-path §7b documents only dedup-enabled batch filing and never requires --no-dep-llm. /issue Phase 2 can then emit extra intra-batch blocker edges and undo "independent pieces remain independent."
- **Proposed resolution**: Add an explicit §7b contract: always pass --no-dep-llm for partition batches; pass --intra-batch-deps-file only when partition-deps.tsv has rows; pin the empty-TSV all-independent case in test_decompose.py.

### FINDING_12:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: skills/design/references/decompose-panel.md
- **Concern**: Resume-close must run migrate-deps before close-original. Scenario: Today §0 resume-close skips re-filing and reruns only close-original when .decompose-issues-filed exists. The plan gates close-original on .decompose-deps-migrated and live graph verification but does not rewrite §0. After an interrupted run with a filed batch but no migration sentinel, resume-close would call close-original directly and fail closed with no mandated migrate-deps step.
- **Proposed resolution**: Rewrite §0 so resume-close runs python/cli.py decompose migrate-deps when filing is complete and .decompose-deps-migrated is absent, then close-original only after migration success; add a resume fixture in test_decompose.py.

### FINDING_13:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md
- **Concern**: Inline partition validation failure lacks a terminal outcome contract. Scenario: The plan removes panel-driven Split-path prompts but still routes Split-path terminal failures through failed-judge-panel and scripts/test-design-structure.sh panel-failed assertions. Failure modes only say "terminate with a recorded failure" when inline prepare/repair cannot produce a valid multi-piece scheme, with no SUMMARY_OUTCOME, finalize-step5-failures.md entry, or design_terminal.py token. Inline exhaustion can stall or mis-report as a panel failure.
- **Proposed resolution**: Name a dedicated terminal outcome (for example failed-partition-proposal), list it in SKILL.md Final summary exports, update finalize-step5-failures.md and python/larch/design/design_terminal.py, and replace the judge-panel harness assertions in scripts/test-design-structure.sh.

### FINDING_14:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: skills/design/references/decompose-panel.md:11-15
- **Concern**: Resume-close idempotency does not orchestrate migrate-deps. Scenario: The plan inserts `decompose migrate-deps` and `.decompose-deps-migrated` before `close-original`, but the only listed `decompose-panel.md` rewrite bullets cover inline partition, filing, and closure preconditions. §0 resume-close still says that when `.decompose-issues-filed` exists the flow may skip re-filing and only rerun `close-original`. After a successful batch annotate, an interrupted run can therefore re-enter close without ever invoking migration; `close-original` should fail closed, but the operator gets no documented annotate → migrate-deps → close sequence and may treat closure failure as a transient GitHub error.
- **Proposed resolution**: Add an explicit §0 resume branch: when `.decompose-issues-filed` is present and `.decompose-deps-migrated` is absent or stale, run the canonical `decompose migrate-deps` fence (with live-graph revalidation) before any `close-original` retry; only skip migration when the sentinel and postcondition already verify.

### FINDING_15:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/design/references/decompose-panel.md:146-159
- **Concern**: No durable path for the inline partition artifact before `decompose prepare`. Scenario: The plan requires the main agent to compute a concrete proposal, then run `decompose prepare` before the single `AskUserQuestion`, but the firm `decompose-panel.md` update never names where that proposal is written. `prepare` requires `--partition-file`, and pause/resume or a failed prepare/repair loop cannot recover a proposal that exists only in chat. Split-path can halt or re-derive a different partition on resume.
- **Proposed resolution**: Require the inline procedure to write the validated proposal to a canonical durable file under `$DESIGN_TMPDIR/decompose/` (for example `inline-partition-proposal.md`) before every `decompose prepare` call, and mandate that all prepare/repair/resume steps read that same path rather than recomputing from memory.

### FINDING_16:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: code-quality
- **Location**: skills/design/SKILL.md:175-176
- **Concern**: Panel-removal leaves no named terminal outcome for inline partition validation failure. Scenario: Approach 9 removes panel dispatch from Split-path and the failure-modes section says to terminate when inline validation cannot yield a valid multi-piece acyclic scheme, but the listed `SKILL.md` edits do not replace the Split-path `panel-failed` / Retry panel / `failed-judge-panel` branches or update `finalize-step5-failures.md` and `scripts/test-design-structure.sh`, which still assert judge-panel exhaustion semantics. Inline prepare/metadata/cycle failure would either retain dead panel prompts (violating exactly-one-question) or exit without a contract-stable `SUMMARY_OUTCOME`, staging, and harness coverage.
- **Proposed resolution**: Name a single terminal outcome for inline partition validation exhaustion (reuse or replace `failed-judge-panel`), document the `stage-terminal-state` / Final-summary path in `decompose-panel.md` and `finalize-step5-failures.md`, remove Split-path `PANEL_STATUS=panel-failed` and Retry panel prose from `SKILL.md`, and add a `### UPDATED:` entry for `scripts/test-design-structure.sh` (plus the focused decompose test named in the plan) so the new failure route is asserted.

### FINDING_17:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: correctness
- **Location**: skills/design/references/decompose-panel.md:172-176
- **Concern**: Rewritten Split-path does not preserve explicit `/larch:issue` intra-batch dependency flags. Scenario: The plan depends on proposal-declared edges only in `partition-deps.tsv` and removes automatic serial chaining, but the firm `decompose-panel.md` rewrite bullets only say to preserve batch filing behavior. Current §7b documents `partition-deps.tsv` yet does not spell out the Skill invocation flags; a rewrite can drop `--intra-batch-deps-file "$DESIGN_TMPDIR/decompose/partition-deps.tsv"` and `--no-dep-llm`, letting Phase-2 LLM dependency analysis add edges the operator never saw in the single partition question.
- **Proposed resolution**: In the rewritten Split-path §7b, make the `/larch:issue` batch invocation normative: `--input-file` on `partition-input.txt`, `--intra-batch-deps-file` on `partition-deps.tsv`, `--no-dep-llm`, `--context-file "$DESIGN_TMPDIR/source-env.sh"`, dedup enabled, and stdout capture to `issue-run.stdout`, matching today's panel path semantics without the removed serial edges.
