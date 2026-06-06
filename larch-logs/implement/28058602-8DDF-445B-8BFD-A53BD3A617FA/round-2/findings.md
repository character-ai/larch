Normalized reviewer input into merged findings below. Positive/OOS-only attestations (FINDING_30, 31, 37–40, 45, 46, 52, 53) are omitted — they are not actionable defects.

### FINDING_1: design-step3-state.sh referenced but not committed to HEAD
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-step3-contract-output.txt
- **Severity**: important
- **Concern**: `SKILL.md`, `scripts/test-design-structure.sh`, `test-step3-orchestrator-fence.sh`, and `test-design-pause-resume.sh` invoke `skills/design/scripts/design-step3-state.sh` for Gate-B-bypass sentinels and direct-review re-entry, but the script is untracked/absent from HEAD. A clean checkout, CI run, or plugin publish will hit exit 127 on Step 3 / Gate-B-bypass Bash fences and fail related harnesses before plan review can run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Commit design-step3-state.sh with tests; add test-design-structure.sh executable-file pin.
  - From cursor-specialist-correctness-output.txt: Commit design-step3-state.sh to the branch; add harness doc if test-design-structure.sh pins require it; re-run test-step3-orchestrator-fence and test-design-pause-resume.
  - From cursor-specialist-edge-cases-output.txt: Commit skills/design/scripts/design-step3-state.sh plus harness contract; ensure Makefile/relevant-checks exercise it.
  - From cursor-specialist-plan-fidelity-output.txt: Commit skills/design/scripts/design-step3-state.sh (and tests) or revert SKILL to inline sentinel writes until the helper ships.
  - From dyn-step3-contract-output.txt: Add `design-step3-state.sh` (plus a short contract `.md` if you follow sibling script conventions), wire it into `Makefile` harness targets if needed, and ensure `test-design-structure.sh` pins a committed path.

### FINDING_2: test-step3-review-cap.sh still expects removed LOOP_STATUS values
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-step3-contract-output.txt, dyn-resume-compat-output.txt, dyn-interactive-flow-output.txt
- **Severity**: important
- **Concern**: The `passive-summary statuses parse and persist` block (lines ~103–119) still stubs `LOOP_STATUS=converged` and `LOOP_STATUS=cap-hit` and expects them to pass through `run-step3-review.sh`, but the driver now only accepts the reduced enum and normalizes anything else (including `converged` / `cap-hit`) to `panel-failed` (`run-step3-review.sh:372–374`). This contradicts the single-pass contract in `plan-review-loop.md` and should fail `make test-step3-review-cap` / `test-harnesses-15` despite correct runtime behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Remove or re-scope passive-summary cases to single-pass contract; keep outer cap-reached tests only.
  - From cursor-specialist-testing-output.txt: Rewrite or remove the passive-summary block; test cap-reached and normalized invalid statuses only
  - From cursor-specialist-plan-fidelity-output.txt: Remove or rewrite passive-summary cases to assert panel-failed normalization per single-pass contract.
  - From dyn-step3-contract-output.txt: Remove or rewrite the passive-summary section to assert `complete` (or explicit bypass statuses like `cap-reached` from the **outer** cap guard), and add a case that removed loop statuses from stub stdout normalize to `panel-failed` with the invalid-status warning.
  - From dyn-resume-compat-output.txt: Remove or rewrite the passive-summary section to assert `complete` (and/or `cap-reached` from the outer cap guard) with the reduced enum; drop `converged` / `cap-hit` expectations entirely.
  - From dyn-interactive-flow-output.txt: Delete or rewrite the passive-summary block to assert `complete` single-pass behavior and `cap-reached` from the outer cap guard; expect `panel-failed` if a stub emits removed statuses.

### FINDING_3: Gate B invariant #4 contradicts always-explicit Gate B contract
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-resume-compat-output.txt, dyn-interactive-flow-output.txt
- **Severity**: important
- **Concern**: `skills/design/references/approval-gates.md` is internally contradictory after manual-flag removal: §Gate B mode says Gate B **always** prompts (`AskUserQuestion` with Apply all / Go through each / Switch to discussion mode), but state invariant **4. Gate B apply contract** (line ~191) still says Gate B revises `plan.txt` "**with no user prompt**" (leftover auto-apply wording). An orchestrator sourcing invariant #4 could skip the explicit Gate B prompt and silently apply accepted findings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Rewrite item 4: application only after operator Apply all / per-finding choices; delete no user prompt wording.
  - From dyn-resume-compat-output.txt: Rewrite invariant #4 so apply happens only after operator choice (Apply all / per-finding apply), and remove "with no user prompt" and any "default explicit apply mode … no removed manual flag" phrasing that implies silent apply.
  - From dyn-interactive-flow-output.txt: Reword invariant #4 to state that Gate B always prompts first; only after **Apply all** or per-finding **Apply** choices does the rewrite run without further per-finding prompts.

### FINDING_4: [OUT_OF_SCOPE] Duplicate HTML-comment footer in approval-gates.md
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Duplicate HTML-comment footer repeats Gate B always-explicit contract after numbered invariants. Prompt noise only; no runtime effect.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Remove redundant comment block or fold into item 4.

### FINDING_5: [OUT_OF_SCOPE] Stale failure message in test-design-pause-resume.sh
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Failure message at line ~558 still references removed plan-size-trigger handoff. Misleading test diagnostics only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Rename message to gate-b-bypass or cap-reached/panel-failed bypass.

### FINDING_6: cap-reached path may publish stale session-root review artifacts
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: On `cap-reached`, `run-step3-review.sh` skips `plan-review-loop`, so session-root review artifacts are never cleared but may still be published. Stale `accepted-plan-findings.md` from an earlier Gate C re-run can land in committed `larch-logs` via top-level tmpdir staging while Gate B is bypassed, misleading operators and auditors.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Clear session-root review artifacts on cap-reached (shared helper with plan-review-loop) or exclude them from publish when no fresh round ran.

### FINDING_7: Unreadable drift-baseline.env disables drift and may emit false baseline KVs
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-drift-guard-output.txt
- **Severity**: important
- **Concern**: In `check-plan-size.sh`, when `drift-baseline.env` is unreadable or partially corrupt, drift is disabled with only a `WARN`, but stdout may still emit `BASELINE_PLAN_LINES` / `BASELINE_DIFF_LINES` using **current** plan metrics (lines 163–164) as if they were the anchored baseline. Step 2b.5 and merged rc `14` fences can therefore show a false baseline equal to current size while drift is silently off. Same-UID tmpdir tampering or corruption silences the anti-sprawl guard for the remainder of the run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Fail closed on unreadable baseline or require operator acknowledgment before continuing without drift checks.
  - From dyn-drift-guard-output.txt: On unreadable baseline, emit empty or `unknown` baseline KVs (or repeat the parsed file values with an explicit `BASELINE_STATUS=unreadable` flag) and require orchestrator fences to treat unreadable baseline as a loud warning, not as display evidence.

### FINDING_8: Override recovery re-anchors drift baseline to bloated plan
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Override recovery in `check-plan-size.sh` (lines ~184–191) seeds the drift baseline from the current expanded plan when the snapshot is absent. Operator Override after a hard cap re-anchors drift to the bloated plan, allowing further growth within 2× of an inflated baseline.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Seed baseline only from initial Step 2b snapshot; do not write baseline on Override-first check-plan-size path.

### FINDING_9: Orphaned revise-plan-with-waterfall.sh remains shipped
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Orphaned LLM patch-apply helper `revise-plan-with-waterfall.sh` remains in-tree though Step 3 no longer invokes it. Future mis-wiring or manual invocation reintroduces the highest-risk automated plan-mutation path. Plan marks removal as follow-up OOS.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Remove script per planned follow-up or guard behind explicit dev-only flag; trim publish allowlist when safe.
  - From cursor-specialist-plan-fidelity-output.txt: Track follow-up issue to delete helper/docs/tests as planned.

### FINDING_10: LARCH_DESIGN_DRIFT_MULTIPLE missing from configuration-and-permissions.md
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-drift-guard-output.txt
- **Severity**: important
- **Concern**: Plan-required `LARCH_DESIGN_DRIFT_MULTIPLE` documentation is absent from the canonical env-var doc (`docs/configuration-and-permissions.md`); only `flags.md` documents drift. Operators tuning drift thresholds via the configuration doc never see the knob; misconfiguration defaults silently to 2×. `LARCH_DESIGN_ROUND_CAP` deprecation is also not mirrored.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Add ### LARCH_DESIGN_DRIFT_MULTIPLE section and mark LARCH_DESIGN_ROUND_CAP deprecated to match flags.md.

### FINDING_11: Missing drift harness coverage for design-postplan-emit.sh
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-drift-guard-output.txt
- **Severity**: important
- **Concern**: Acceptance-required drift tests for `design-postplan-emit.sh` were not added: baseline snapshot seed, no overwrite on re-emit, and `--with-plan-size` rc `14` with `## Plan Size — Drift` output. Drift baseline write-once regressions or merged exit-14 wiring can break without CI signal despite live drift guard in production scripts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Add harness cases for snapshot baseline seed, no overwrite on re-emit, and --with-plan-size rc 14 with ## Plan Size — Drift output.

### FINDING_12: test-design-structure.sh postplan thin-fence helpers omit rc 14 arm
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `assert_postplan_thin_fence` helpers omit rc arm `14` though plan and `SKILL.md` require non-falling-through drift handling. A future edit can remove the Step 2b case `14` arm and lint will still pass; drift after validator fix-and-retry falls through to default abort.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Extend assert_postplan_thin_fence and assert_postplan_reference_thin_fence to require case arm 14 and Step 2b.5 DRIFT_* parse pins.

### FINDING_13: assert_gate_b_bypass_branch_sentinels stubbed to no-op
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `assert_gate_b_bypass_branch_sentinels` in `scripts/test-design-structure.sh` (lines ~514–516) is stubbed to return 0. Gate-B-bypass sentinel regressions (including post plan-size-trigger removal) are no longer mechanically enforced.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Restore real sentinel assertions aligned with design-step3-state.sh or inline SKILL prose.

### FINDING_14: Gate-B-bypass sentinel handling split across incompatible SKILL.md mechanisms
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-step3-contract-output.txt, dyn-shell-state-output.txt
- **Severity**: important
- **Concern**: Gate-B-bypass sentinel handling in `SKILL.md` (lines ~1189–1207) is split across two incompatible mechanisms: the branch matrix still instructs inline `mkdir` / `: > .completed/step-*` writes, while later prose mandates `design-step3-state.sh --gate-b-bypass`. The helper exits `1` with `STEP3_STATE=refused-partial-gate-b-bypass` when `step-3.5` or `step-3.6` already exists, but orchestrator fences redirect helper output to `/dev/null` and do not branch on exit code. An agent following only the matrix—or ignoring helper failures—can leave bypass sentinels stale while the run continues toward Step 3b.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Unify on one sentinel mechanism in branch matrix and downstream prose.
  - From dyn-step3-contract-output.txt: Make `design-step3-state.sh --gate-b-bypass` the sole normative path in the branch matrix and delete the inline `mkdir` prose; document exit `1` / `STEP3_STATE=refused-partial-gate-b-bypass` handling (abort or operator repair) in the same fence.
  - From dyn-shell-state-output.txt: Make bypass paths use only `design-step3-state.sh --gate-b-bypass`, parse `STEP3_STATE=` from stdout, fail closed on `refused-partial-gate-b-bypass` or non-zero rc, and remove the duplicate inline sentinel prose from the branch matrix.

### FINDING_15: design-postplan-emit.sh rc 2 skips drift when baseline exists
- **Reviewer(s)**: dyn-drift-guard-output.txt
- **Severity**: important
- **Concern**: When `check-plan-size.sh` returns rc `2` (missing/malformed `diff_lines` trailer, missing plan, etc.), `_postplan_finish_merged_plan_size` (`design-postplan-emit.sh:401–407`) flushes and exits `0` without ever evaluating drift, even if `drift-baseline.env` was written earlier. A Gate B / discussion rewrite can grow `plan.txt` substantially while leaving the trailer broken; the merged fence proceeds as "ok" and skips both hard-size and drift prompts, defeating the sprawl guard on a realistic failure path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-drift-guard-output.txt: On rc `2`, if a readable `drift-baseline.env` exists, still parse `plan_lines` from the body (or run a drift-only helper) and surface drift via rc `14` or a dedicated warning before the degraded proceed; at minimum, do not treat rc `2` as unconditional success when a baseline snapshot is present.

### FINDING_16: Drift baseline anchoring split and silently fragile in design-postplan-emit.sh
- **Reviewer(s)**: dyn-drift-guard-output.txt, dyn-shell-state-output.txt
- **Severity**: important
- **Concern**: Baseline anchoring is split across `_postplan_seed_initial_drift_baseline` (runs after emit, **before** validator) and `_postplan_snapshot_drift_baseline` (runs only after successful `_postplan_run_plan_size`). The early seed call discards stdout/stderr, ignores `_seed_rc`, and always returns 0; a symlink at `drift-baseline.env` is treated as "already present" and skips the write silently. If seeding fails or baseline is misaligned with the post-validator plan-size parse, drift guard can be disabled without operator-visible breadcrumb while later passes believe seeding is done.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-drift-guard-output.txt: Write `drift-baseline.env` only once in a single place immediately after the first successful `_postplan_run_plan_size` when `--snapshot-original` is set (remove the early seed call), and keep the Override-path seed solely inside `check-plan-size.sh` when no file exists.
  - From dyn-shell-state-output.txt: On non-zero `_seed_rc` or a missing `drift-baseline.env` after the call, append the captured stderr through `append-tool-failure.sh` (Warnings) and/or emit a `WARN=` KV; only return success when the baseline file exists and is a regular non-symlink file.
  - From dyn-shell-state-output.txt: Mirror `check-plan-size.sh` and require `[[ ! -e "$_baseline" ]]` for creation plus `[[ -f "$_baseline" && ! -L "$_baseline" ]]` before treating baseline as present; WARN and continue when only a symlink or unreadable file exists.

### FINDING_17: SKILL.md still references removed passive-summary auto-continue
- **Reviewer(s)**: dyn-step3-contract-output.txt, dyn-interactive-flow-output.txt
- **Severity**: important
- **Concern**: The MainAgent re-tally paragraph (`SKILL.md:1195`) still says settled Gate B paths include "passive-summary auto-continue," which belonged to the removed `LOOP_STATUS=converged|cap-hit` multi-round contract. Under single-pass review, Gate B is always explicit and `plan.txt` is unchanged until Gate B applies findings. An agent following that stale phrase can skip the always-explicit Gate B `AskUserQuestion` and jump straight to Step 3.6.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-step3-contract-output.txt: Replace that phrase with "zero-findings short-circuit or operator-approved apply" so Step 3 / Gate B / Step 3.6 routing prose matches the reduced `LOOP_STATUS` enum.
  - From dyn-interactive-flow-output.txt: Replace the passive-summary reference with explicit language: after MAV re-tally sets `LOOP_STATUS=complete`, always enter Gate B; only the zero-findings short-circuit may bypass the prompt.

### FINDING_18: parse-design-argv.md documents stale eight-KV contract
- **Reviewer(s)**: dyn-resume-compat-output.txt
- **Severity**: important
- **Concern**: The normative parser contract in `parse-design-argv.md` (lines ~17–27) still documents **eight** success KVs and lists a bogus `removed manual env key=true|false` line, but `parse-design-argv.sh` now emits **seven** real keys with no `MANUAL_REQUESTED`, and `SKILL.md` Step 0-pre enforces `_success_kv_count -ne 7`. Anyone following the doc (or tooling keyed off it) will mis-parse argv output or reintroduce the removed eighth KV.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-resume-compat-output.txt: Rewrite the Machine output and exit-code sections to seven KVs, delete the placeholder line, and mirror the live key list from `parse-design-argv.sh` lines 99–105.

### FINDING_19: Missing resume regression for stale manual_gate_b in run-params.json
- **Reviewer(s)**: dyn-resume-compat-output.txt
- **Severity**: important
- **Concern**: The plan's acceptance criteria called for pins that stale `manual_gate_b` in old `run-params.json` is ignored on pause/resume, but the branch only left a comment and did not add a `design-route.sh` resume fixture with `manual_gate_b: true` plus an assertion that env refresh omits `MANUAL_REQUESTED` and Gate B stays explicit. Resume-compat for paused sessions upgraded from the old plugin is unverified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-resume-compat-output.txt: Extend `test-design-structure.sh` pause/resume smoke (or add a focused harness) that loads a pause marker with stale `manual_gate_b` in `run-params.json`, resumes via `design-route.sh`, and asserts `source-env.sh` has no `MANUAL_REQUESTED` and `write-design-current-env.sh` is invoked without `--manual-requested`.

### FINDING_20: check-plan-size.sh drift ratio depends on unguarded python3
- **Reviewer(s)**: dyn-shell-state-output.txt
- **Severity**: important
- **Concern**: New drift ratio emission in `check-plan-size.sh` (lines ~132–151) depends on `python3` inside `ratio_token` with no availability guard. Under `set -euo pipefail`, a missing or failing `python3` aborts `check-plan-size.sh` before any `DRIFT_*` / `PLAN_LINES` KVs are emitted, which can break Step 2b.5 and merged post-plan fences that assume exit 0 with a full KV contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-state-output.txt: Add a `command -v python3` guard that falls back to integer ceiling division in pure bash (or `awk`) for ratio tokens, emitting a WARN when degraded.

### FINDING_21: Gate B applies plan mutations before drift check with no rollback on Cancel
- **Reviewer(s)**: dyn-interactive-flow-output.txt
- **Severity**: important
- **Concern**: The shared post-apply pipeline in `approval-gates.md` (lines ~130–141) applies accepted findings to `plan.txt` **before** the merged `design-postplan-emit.sh --with-plan-size` drift check. If `_postplan_rc=14` fires and the operator picks **Cancel**, the run exits with `SUMMARY_OUTCOME=cancelled-sprawl` while `plan.txt` already contains the Gate B rewrites. The operator sees a "sprawl cancelled" terminal summary but a mutated plan in `$DESIGN_TMPDIR`, with no documented rollback to the pre-apply snapshot.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-interactive-flow-output.txt: Either run drift sizing on a dry-run copy before mutating `plan.txt`, snapshot `plan.txt` before Gate B apply and restore on drift Cancel, or at minimum use a distinct outcome (e.g. `cancelled-plan-drift`) and print an explicit warning that Gate B edits were retained in the tmpdir.

### FINDING_22: Drift Continue completion sentinels inconsistent across SKILL.md callers
- **Reviewer(s)**: dyn-interactive-flow-output.txt
- **Severity**: important
- **Concern**: Drift **Continue** completion sentinels are inconsistent: the Step 2b thin fence touches both `.completed/step-2b` and `.completed/step-2b.5` (`SKILL.md:1066–1068`), while the standalone Step 2b.5 drift branch and Gate B/discussion merged fences touch only `step-2b.5`. After a Gate B or discussion re-emit drift Continue, pause/resume may believe Step 2b is incomplete relative to the Step 2b thin-fence contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-interactive-flow-output.txt: Align all drift-Continue paths to touch the same sentinel set the invoking caller uses on a clean rc `0` path (Step 2b initial: both; Gate B/discussion: at least document that `step-2b` remains from the initial emit).
