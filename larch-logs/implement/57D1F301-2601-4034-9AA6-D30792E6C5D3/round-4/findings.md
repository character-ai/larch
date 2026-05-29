Normalized aggregator output from the supplied reviewer slots:

### FINDING_1: Dead code — `snapshot_optional_trailer_values` unused
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `snapshot_optional_trailer_values` in `lib-plan-optional-trailers.sh` is never called while callers use key-only validation; maintainers may assume value snapshots are enforced and trailer value downgrades can slip through until plan-size re-fires.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: Duplicated dedup + trailer guard (`plan-review-loop.sh` vs `gate-b-dedup-plan.sh`)
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: ~40 lines of dedup and optional-trailer preservation logic are duplicated between `plan-review-loop.sh` (501–539) and `gate-b-dedup-plan.sh` (78–120); fixing restore/exit behavior in one path can leave the other stale for Gate B vs review-loop flows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: Trailer preservation validates keys only, not values
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `validate_optional_trailers_preserved` checks key presence only. A revision can keep keys (e.g. `mechanical_churn`) while changing values (`false`, lower `diff_added`); validation passes, then `check-plan-size` hard-triggers or plan-size-trigger fires unexpectedly mid review loop / at Step 2b.5.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_4: Zero-padded `diff_added` 08/09 cleared in bash — legacy `diff_lines` gating
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Values like `diff_added: 08` / `09` match strict awk grammar but are cleared in bash (`check-plan-size.sh` ~101–106), so hard gating falls back to legacy `diff_lines` while preservation still sees the `diff_added` key. A plan can hard-trigger on `diff_lines` despite deletion-heavy intent and empty effective `DIFF_ADDED`. Harness covers `08` (case 32c) but not symmetric `09`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_5: Gate B dedup script lacks dedicated regression harness
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `gate-b-dedup-plan.sh` has no dedicated test harness; regressions in post-rewrite dedup, trailer snapshot, restore, or exit codes may only surface on manual Gate B paths. `plan-review-loop` coverage does not exercise this script’s persistent `.gate-b-optional-trailer-keys` path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_6: `--dedup` without prior `--snapshot-trailers` fails open on rewrite-time trailer loss
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `--dedup` without a prior `--snapshot-trailers` only guards dedup-time loss, not rewrite-time loss. Gate B Write can drop optional trailers; `--dedup` then runs with an ephemeral empty snapshot and legacy hard gate on `diff_lines` proceeds undetected. Should fail closed if `.gate-b-optional-trailer-keys` is missing when `--dedup` runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_7: Documentation gaps for 08/09 trailer handling
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Contract/docs (`check-plan-size.md`, `test-check-plan-size.md` case 32) omit or misstate the 08/09 special case implemented in `check-plan-size.sh` (awk may parse/subtract metadata lines while bash treats values as absent for threshold). Operators can misread `PLAN_LINES` vs trigger behavior for leading-zero trailers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_8: `diff_deleted`-only legacy fallback untested for high total churn
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: A plan with high `diff_deleted` and `diff_lines` but no `diff_added` or `mechanical_churn` can still legacy hard-trigger; no harness asserts `HARD_TRIGGER_FIRED=true` / `TRIGGER_REASONS=diff-lines` for that path—regression could reintroduce #3118-style false negatives if `diff_deleted` were wired into the gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_9: Self-declared diff trailers — honor-system trust boundary
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Self-declared `diff_added` and `mechanical_churn` control hard vs soft diff gating with no independent verification; designers/agents can under-report additions or set `mechanical_churn: true` to bypass Split/Cancel on large estimated diffs while still reaching `/implement`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_10: New optional trailers allowed when original plan had none
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Preservation validates only snapshotted keys; an empty snapshot allows newly introduced optional trailers during revision (e.g. append `mechanical_churn: true` on a legacy plan), skipping validation and avoiding plan-size-trigger / Step 2b.5 AskUserQuestion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_11: Review loop ignores `SOFT_ADVISORY` from `check-plan-size`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Mechanical downgrade during review can suppress the hard gate silently; the operator never sees Step 2b.5 advisory copy. `plan-review-loop.sh` should emit a breadcrumb or parse `SOFT_ADVISORY` in `_run_post_apply_pipeline` to match SKILL Step 2b.5.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_12: Gate A/B direct rewrites lack mechanical trailer enforcement beyond prose
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Operator can skip gate-b snapshot before rewrite; dedup snapshots post-rewrite keys and cannot detect trailers dropped at rewrite time. Needs mechanical pre-`EMIT_PLAN` check against `.gate-b-optional-trailer-keys` on all Gate B paths (and related Gate A discussion rewrites per `approval-gates.md`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_13: `SKILL.md` missing Gate A/B trailer snapshot/validate prose
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Plan required Gate A/B trailer snapshot/validate guidance in `SKILL.md`; only reference docs contain it. An orchestrator following Step 2b/2b.5 without loading `approval-gates.md` / `discussion-rounds.md` on Gate A/B rewrites can drop optional trailers and fall back to legacy `diff_lines` hard gating.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_14: Plan byte-stable `check-plan-size.sh` lines 1–90 vs shared lib extraction
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Plan said keep lines 1–90 byte-stable; implementation extracted a shared library instead. Low risk if harness stays green, but reviewers expecting minimal append-only diff may be surprised.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### OOS_1: [OUT_OF_SCOPE] Unused `snapshot_optional_trailer_values` expands untested API surface
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `snapshot_optional_trailer_values()` is unused dead code on a new shared library—not a regression risk from current callers, but expands untested API surface and suggests incomplete value-validation design.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] `LARCH_DEDUP_PLAN_LINES_PY` env override — arbitrary script execution
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `LARCH_DEDUP_PLAN_LINES_PY` in `plan-review-loop.sh` can point `python3` at an attacker-chosen script; malicious env in the design process could achieve code execution during dedup (pre-existing).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] `check-plan-size` exit 2 skips threshold enforcement
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `check-plan-size` exit 2 proceeds without threshold enforcement when `diff_lines` is missing/malformed; documented operational risk vs fail-closed (pre-existing, `SKILL.md` ~883).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
