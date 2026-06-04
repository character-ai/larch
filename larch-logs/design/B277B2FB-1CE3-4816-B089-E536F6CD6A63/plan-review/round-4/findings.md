### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-design-structure.sh:517
- **Concern**: Legacy global pin requires postplan stdout KV merge heredoc in SKILL.md. Scenario: Thin-fence migration removes `<<<"${_postplan_out:-}"` from merged Step 2b/Gate B/discussion/Step 1e fences per plan contract; pin 517 still fails `make lint` / `scripts/test-design-structure.sh` even when behavior is correct
- **Proposed resolution**: Add explicit retirement/repoint of the `contains "$SKILL_MD" '<<<"${_postplan_out:-}"'` assertion in the `### UPDATED: scripts/test-design-structure.sh` section (alongside the named `(14c14e)` / `(14c14h)` retirements); replace with thin-fence pins such as `--with-plan-size`, `echo "$out"`, and rc `case` dispatch without stdout KV merge

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:117,219; skills/design/scripts/design-postplan-emit.sh:58-79
- **Concern**: Plan requires ${REPO:+--repo "$REPO"} passthrough on merged design-postplan-emit.sh driver calls, but the proposed argv only adds --with-plan-size and the current parser rejects unknown flags. Scenario: Implementer follows the structure pins and adds --repo to Step 2b/Gate B/discussion driver invocations; design-postplan-emit.sh exits 2 before rc10/11/12/13 handling, breaking the thin fence
- **Proposed resolution**: Keep repo threading on the prelude and rc11 design-pause-save.sh exec arms only, and pin that design-postplan-emit.sh invocations do not receive --repo unless the plan also adds and documents a real --repo parser contract

### FINDING_3:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:835-880
- **Concern**: Step 2b entry pause-save omits REPO while structure pins require it. Scenario: `assert_thin_fence` on `<!-- step:2b`…`<!-- step:3` matches the timing-block pause at ~835 before the merged driver; fork pause-save runs without `--repo` and structure tests fail or miss the regression
- **Proposed resolution**: Thread `${REPO:+--repo "$REPO"}` on every Step 2b pause-save line in that region (timing guard and thin-fence prelude), not only on `design-postplan-emit.sh` / rc11 arms

### FINDING_4:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-postplan-emit.sh:4; scripts/append-tool-failure.sh:100-129
- **Concern**: Plan-size rc2/rc3 is declared nonfatal, but the plan does not require append-tool-failure.sh itself to be best-effort. Scenario: append-tool-failure.sh can exit 2 on missing output file, redaction failure, or log write failure; under set -e that can turn the promised under-threshold rc0 path into an abort
- **Proposed resolution**: Wrap the append call in set +e or || true, redirect its stdout/stderr, then always emit the WARN and exit 0 for plan-size rc2/rc3; add a failing-append regression

### FINDING_5:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/lib-phase-driver.sh:40-57; skills/design/scripts/design-postplan-emit.sh:144-173
- **Concern**: --with-plan-size forbids stdout KV fallback but does not define fail-closed behavior when result-env write fails. Scenario: A symlink, mktemp, permission, or mv failure can leave rc10/Override handlers reading missing or stale .design-postplan-emit-result.env data, causing wrong validator context or silent state corruption
- **Proposed resolution**: In --with-plan-size, make result-env write failure a specific rc1 diagnostic before any action rc that needs context, or provide another safe non-KV handoff; include a symlink/write-failure test

### FINDING_6:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md:636; skills/design/references/discussion-rounds.md:126
- **Concern**: Step 1e and discussion-round2 specs assign conflicting argv to the same post-discussion re-emit path. Scenario: The plan pins Step 1e as --with-plan-size without --force-validate while discussion-round2 remains --with-plan-size --force-validate; in quick mode one doc skips validator defects and the other requires catching them
- **Proposed resolution**: Clarify the split or collapse to one owner: if plan.txt was revised by post-plan discussion, make both files specify the same argv and pin only that canonical path

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/test-design-structure.sh:40-87
- **Concern**: skills/design/SKILL.md:829-966. Scenario: Plan adds assert_thin_fence for Step 2b without scoping or helper change, but scoped assert_thin_fence requires the first pause-save line before read-design-classification.sh to include ${REPO:+--repo "$REPO"}; Step 2b entry guards at skills/design/SKILL.md:835 and :880 omit REPO while Step 3.6 entry at :1163 includes it
- **Proposed resolution**: make test-design-structure fails on Step 2b thin-fence pin, or implementers drop the pin to unblock CI Narrow the pin to a sub-region containing only the merged driver fence (new HTML markers), extend assert_thin_fence with a Step-2b mode that skips the classification ordering check, or add REPO to Step 2b prelude pause-save lines in the pinned region

### FINDING_8:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:600-620
- **Concern**: Retained plan-review-loop path still lacks a concrete partition_requested handoff. Scenario: After /design --partition reaches Step 3 and the multi-round loop auto-revises plan.txt, _run_post_apply_pipeline only reacts to HARD_TRIGGER_FIRED, so a clean small revised plan can proceed without the required Split-path
- **Proposed resolution**: Keep the change local: in the plan-review-loop size block, read partition_requested from run-params.json with the same boolean fallback and surface the existing plan-size-trigger handoff when true and hard is false; add one harness case for that path

### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-doc-topology-sync
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-design-structure.sh:689-695
- **Concern**: FINDING_21 still requires check-plan-size.sh after design-postplan-emit.sh inside the Step 2b SKILL region. Scenario: After Step 2b collapses to --with-plan-size only, that inline helper call disappears and make test-design-structure / scripts/test-design-structure.sh fails despite green unit harnesses
- **Proposed resolution**: Repoint or drop FINDING_21 lines 689-695 in the same test-design-structure.sh pass (e.g. require --with-plan-size on design-postplan-emit.sh and/or assert_thin_fence for <!-- step:2b through <!-- step:3)

### FINDING_10:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:636, skills/design/references/discussion-rounds.md:126, skills/design/references/flags.md:70
- **Concern**: Step 1e no-force pin conflicts with discussion-round2 force-validation contract. Scenario: The plan tells implementers to pin the Step 1e Gate A optional-trailer re-entry rewrite as --with-plan-size without --force-validate, but the existing Step 1e guard is explicitly for plan.txt revised after discussion and routes as design discussion-round2; in quick review_budget runs this can skip validator defects after a discussion edit even though discussion-round2 currently preserves --force-validate.
- **Proposed resolution**: Do not pin no --force-validate on the discussion rewrite path; either align the SKILL.md Step 1e discussion-rewrite fence with discussion-round2 --with-plan-size --force-validate, or split/delete the duplicate SKILL guard so only a truly non-discussion Gate A path uses no-force.

### FINDING_11:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-design-structure.sh:517-517
- **Concern**: Stale stdout KV merge pin conflicts with merged thin-fence contract. Scenario: After Step 2b drops the fat fence, grep for `<<<"${_postplan_out:-}"` still fails `test-design-structure.sh` or forces keeping dead merge prose
- **Proposed resolution**: Retire pin 517 explicitly; replace with a merged-fence pin that forbids stdout KV merge loops (as the plan already proposes for new pins)

### FINDING_12:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1117-1117
- **Concern**: Step 3 `LOOP_STATUS=plan-size-trigger` retained Step 2b.5 caller lacks a site-aware hard-prompt bucket. Scenario: Plan assigns Override only to Gate B / plan-review-loop routes; Step 3 handoff is a separate retained caller but `plan-review-loop.md` requires Split/Override/Cancel there
- **Proposed resolution**: Extend site-aware Step 2b.5 prose and structure pins so Step 3 plan-size-trigger uses the Override-capable prompt set

### FINDING_13:
- **Reviewer(s)**: Cursor-dyn-exit-code-mapper
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:936-965
- **Concern**: Post-driver fat guards still run before any rc 10/11/12/13 dispatch. Scenario: The mandatory-key block runs on rc 0 or 1 (lines 936-940), defects are still handled via `VALIDATE_STATUS=defects-found` after rc 0 (968), and the catch-all `ne 0` abort (962-965) fires before a thin `case` on 10/11/12/13 — rc10/11/12/13 never reach their arms
- **Proposed resolution**: Replace the Step 2b fence with echo-then-case only: drop stdout KV merge and the rc 0/1 mandatory-key gate for merged `--with-plan-size` calls; route defects via rc 10 (not `VALIDATE_STATUS` after rc 0); handle 11/12/13 before the generic `ne 0` abort

### FINDING_14:
- **Reviewer(s)**: Codex-dyn-exit-code-mapper
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:636; skills/design/references/discussion-rounds.md:126
- **Concern**: The plan gives the same post-discussion Gate A rewrite two different argv contracts: discussion-round2 uses --with-plan-size --force-validate, while Step 1e optional-trailer re-entry says --with-plan-size without --force-validate.. Scenario: On review_budget=quick, the no-force Step 1e path skips validation, so rc10 is unreachable even though the discussion-round2 rc10 same-site handler is documented.
- **Proposed resolution**: Clarify the split: either make the Step 1e after-discussion rewrite use --with-plan-size --force-validate, or identify a separate non-discussion Step 1e rewrite site and remove the current “after discussion (per discussion-rounds.md)” overlap.

### FINDING_15:
- **Reviewer(s)**: Codex-dyn-exit-code-mapper
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:600-623; skills/design/references/flags.md:21-44
- **Concern**: The retained plan-review-loop path still only branches on HARD_TRIGGER_FIRED; the plan’s rc2/rc3 work does not spell out the missing partition_requested=true route.. Scenario: For /design --partition, a multi-round auto-apply can rewrite plan.txt under hard thresholds, return clean/converged, and never enter Split-path despite the “every plan write” partition contract.
- **Proposed resolution**: In plan-review-loop.sh, after the hard parse, read partition_requested with the same boolean-safe fallback and surface the retained Step 2b.5 handoff when hard=false and partition_requested=true; add a focused harness case.

### FINDING_16:
- **Reviewer(s)**: Codex-dyn-exit-code-mapper
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/design-postplan-emit.sh:144-173; skills/design/scripts/lib-phase-driver.sh:40-57
- **Concern**: With --with-plan-size, the plan forbids stdout KV fallback but does not make result-env write failure fatal.. Scenario: If .design-postplan-emit-result.env is a symlink or cannot be written, rc10/12/13 can reach callers with no fresh allowlisted context, and old stdout-KV recovery is intentionally disabled.
- **Proposed resolution**: In --with-plan-size, treat result-env write failure as rc1 with a clear diagnostic before any action rc; keep non-flag stdout fallback unchanged and add a symlink/unwritable result-env test.

### FINDING_17:
- **Reviewer(s)**: Cursor-dyn-sentinel-lifecycle
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:88-89 vs skills/design/SKILL.md:973-1013
- **Concern**: Merged rc12/rc13 Refine-return only mandates `.completed/step-2b.5`; legacy always wrote `.completed/step-2b` before Step 2b.5/Split. Scenario: After initial merged hard/partition Split, operator Refines: only `step-2b.5` exists. `design-pause-save.sh` scans `step-name-registry.tsv` and resumes at first missing sentinel (`2b` before `2b.5`), so pause/resume replays Step 2b emit instead of continuing to Step 3/Gate A
- **Proposed resolution**: Write `.completed/step-2b` on merged rc12/rc13 Split entry (after successful emit/validate, before Split-path), matching legacy `SKILL.md:973` timing; keep Refine-return `step-2b.5` touch. Pin Split-entry `step-2b` in `test-design-structure.sh` sentinel pins, not only Refine-return `step-2b.5`

### FINDING_18:
- **Reviewer(s)**: Codex-dyn-sentinel-lifecycle
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:62-88; skills/design/SKILL.md:973-1015
- **Concern**: Initial rc12/rc13 Split Refine returns only require .completed/step-2b.5, but legacy initial flow writes .completed/step-2b before Step 2b.5 runs. Scenario: If initial plan-size hard/partition routes to Split and the user chooses Refine plan myself, the merged path can continue with step-2b.5 present but step-2b missing, unlike the legacy lifecycle
- **Proposed resolution**: Add an initial-site Split Refine-return instruction to write .completed/step-2b before or with .completed/step-2b.5

### FINDING_19:
- **Reviewer(s)**: Cursor-dyn-kv-display-boundary
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:989-996
- **Concern**: skills/design/SKILL.md:62-79. Scenario: Step 2b.5 items 4–6 still require the orchestrator to print hard/partition headers and soft-advisory lines from parsed stdout, while the plan moves those displays into `design-postplan-emit.sh --with-plan-size` FD3 output consumed via `echo "$out"`
- **Proposed resolution**: Merged rc12/rc13 arms that still run Step 2b.5 §4–§6 after the thin fence will duplicate plan-size sections (or, if only the rc arm runs, omit driver-emitted headers the procedure no longer supplies) In `skills/design/SKILL.md`, state that merged fences must not call Step 2b.5 steps 4–6 after `echo "$out"`; rc12/13 only run the AskUserQuestion/Split-path arms. Scope standalone Step 2b.5 to Override, `LOOP_STATUS=plan-size-trigger`, and other retained callers

### FINDING_20:
- **Reviewer(s)**: Codex-dyn-kv-display-boundary
- **Severity**: important
- **Focus area**: security
- **Location**: skills/design/scripts/lib-phase-driver.sh:40-56; skills/design/SKILL.md:897-931
- **Concern**: Merged mode forbids stdout KV fallback but does not define a safe result-env write-failure path. Scenario: If .design-postplan-emit-result.env is a symlink or cannot be written, rc10/rc12/rc0 callers must not parse stdout KVs and cannot read allowlisted validator or plan-size context, causing lost diagnostics or pressure to reintroduce unsafe fallback
- **Proposed resolution**: In --with-plan-size, treat result-env write refusal/failure as rc1 with a display diagnostic and no stdout KVs; add a symlink/write-failure test in test-design-postplan-emit.sh and document the rc1 status in design-postplan-emit.md

### FINDING_21:
- **Reviewer(s)**: Codex-dyn-doc-topology-sync
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:636; skills/design/references/discussion-rounds.md:126; skills/design/scripts/design-postplan-emit.md:15
- **Concern**: The plan assigns two argv contracts to the same post-plan Gate A discussion rewrite path: SKILL Step 1e is to use --with-plan-size without --force-validate, while discussion-round2 remains --with-plan-size --force-validate.. Scenario: Operators following SKILL.md on a quick-budget post-plan discussion rewrite would skip validator execution, while the reference doc and historical driver contract teach that discussion-round2 forces validation. Structural tests would also risk pinning both shapes for one site.
- **Proposed resolution**: Keep one contract for this path. Minimum change: make the Step 1e optional-trailer re-entry rewrite defer to the discussion-round2 argv and pin --with-plan-size --force-validate, or explicitly split and rename any truly non-discussion Gate A rewrite site before pinning a no-force argv.
