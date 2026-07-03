## Plan

## Approach

Use the existing difficulty-rating surface (child-1 `#5990`) as the source of truth; consume `applied_tier` to compose tiered reviewer panels. Keep the review procedure unchanged; vary only reviewer composition, Codex reviewer model role, round ceiling, escalation state, and audit-upgrade state.

- Add shared tier resolution in `python/larch/calibration/difficulty.py`.
- Draft from repo inspection only (supplied `NO_SKETCHES` synthesis is binding).
- Apply Round 1 decisions:
  - /design escalates on round-total `>=2` high-severity in-scope accepted findings.
  - missing rating falls back to `MODERATE`.
  - the 1:30 audit is orthogonal to the operator override: it may still upgrade a below-HARD run (including an operator-overridden one) to HARD, logging BOTH `override_source=operator` and `audit_upgrade=true`.

**Override vs. audit precedence (binding, from Round 1; resolves reviewer FINDING_21/23).** The acceptance line "`--difficulty` override wins and is logged" scopes the override's precedence to "beats rating and floors" — the tier-*selection* inputs. It does not name audits. The 1:30 audit is a separate, orthogonal sampling mechanism whose purpose is an unbiased estimate of what cheap panels miss; suppressing it under an operator override would bias the #5992 calibration sample. Therefore: the override sets the starting tier and wins over rating and floors; the audit may independently upgrade a below-HARD run (operator-overridden or not) to HARD and logs both fields. This behavior is deliberate and documented; do not reverse it. (Audit never fires when the effective starting tier is already HARD.)

**Escalation direction (resolves reviewer FINDING_22).** /implement Step 5 and /review escalate one tier up via `next_tier` (TRIVIAL→MODERATE→HARD). /design escalates the not-HARD panel **directly to HARD**: on /design, TRIVIAL and MODERATE collapse to the identical ceiling-2 (gpt-5.4-mini + Composer pairs) panel, so `next_tier(TRIVIAL)=MODERATE` would be an inert no-op that can never reach the HARD (gpt-5.5, ceiling-3) panel. Design escalation sets the effective tier to HARD from any not-HARD tier. HARD model role and ceiling apply only once the effective tier is HARD.

## Files to modify/create

### UPDATED: python/larch/core/config.py

Keep `config.py` **leaf-only** — it must NOT import `calibration.difficulty` (core→domain import fails the layering-ratchet lint; FINDING_9/16). Make config the lower-tier source of tier literals and add single-source `Final` constants (G-Cfg-1):

- Canonical tier literals `DIFFICULTY_TIER_TRIVIAL = "TRIVIAL"`, `DIFFICULTY_TIER_MODERATE = "MODERATE"`, `DIFFICULTY_TIER_HARD = "HARD"` (bare string literals; `difficulty.py` imports these, never the reverse).
- `DIFFICULTY_AUDIT_DENOMINATOR = 30`.
- Tier ceilings `{TRIVIAL: 2, MODERATE: 2, HARD: 3}`.
- Tier→Codex model role: TRIVIAL/MODERATE → `review` (`gpt-5.4-mini`); HARD → `default` (`gpt-5.5`).
- Tier→legacy `--panel` threshold token: `TRIVIAL→simple`, `MODERATE→hard`, `HARD→hard` (see FINDING_5).
- Keep Cursor model unchanged at `composer-2.5`. Do not change voter model defaults.

### UPDATED: python/larch/calibration/difficulty.py

Import the canonical tier literals and tunable maps (ceilings, role map, audit denominator, `--panel` token map) from `core/config.py` (calibration→core is allowed); re-export `TRIVIAL`/`MODERATE`/`HARD`/`TIERS` from the imported config values so existing `difficulty.TRIVIAL` references keep working (FINDING_9/16). Never define tier strings divergently from config.

Add frozen dataclasses (G-Py-1): `TierPolicy`, `TierResolution`, `PanelComposition`, `AuditDecision`.

Extend `DifficultyRecord` (or documented top-level `difficulty-rating.json` keys) with the persisted TierResolution/resume fields: `panel_tier`, `round_cap`, `codex_model_role`, `audit_evaluated`, `escalated_round` (FINDING_8). `escalated_round` is **round-specific**: derive it from the escalation entries' target round rather than a sticky boolean, so resume does not treat a later non-escalated round as escalated (FINDING_11).

Add helpers:

- `normalize_tier(value, default="")`, `tier_rank(tier)`, `next_tier(tier)`, `tier_ceiling(tier)`, `codex_review_model_role(tier)`, `panel_shape_for_tier(tier)` (singles for TRIVIAL, pairs otherwise), `threshold_panel_for_tier(tier)` (`simple` for TRIVIAL, `hard` otherwise).
- `resolve_applied_tier(record_or_rating, floors, override, fallback_tier="MODERATE")`.
- `maybe_audit_upgrade(tier, rng, *, override_source="")` — the RNG seam (G-Py-5). Returns an `AuditDecision`. Fires the 1:30 roll for any below-HARD starting tier **regardless of `override_source`** (Round 1 decision); never fires when tier is already HARD.
- `resolve_panel_tier(record_path, override, rng, audit_enabled=True)` → `TierResolution` with `panel_tier`, `round_cap`, `codex_model_role`, `audit_evaluated`, `audit_upgrade`, `override_source`, `escalations`.
- `append_escalation(record_path, round_num, from_tier, to_tier, trigger)` — atomically appends the escalation line (recording the target round), sets `applied_tier=to_tier`, and updates round-specific `escalated_round` in the same record write (FINDING_12, FINDING_11).

Behavior:

- If `--difficulty` is present, set the starting tier from the override and log `override_source=operator`; the override beats rating and floors (floors never raise an operator override).
- If no rating is usable, synthesize `MODERATE`.
- If the below-HARD starting tier's 1:30 audit fires, use HARD and log `audit_upgrade=true`; preserve `override_source=operator` alongside it when both apply (FINDING_21/23 reconciliation — keep both, do not suppress the audit under override).
- Fold a compact escalation/override summary from `record.escalations` (and `override_source=operator`) into `difficulty_line()` so `final_report.py` and the mandated test share one contract (FINDING_12).
- **Merge-on-existing-output for `difficulty write-record`** (FINDING_13, FINDING_8): when `--output` already exists, merge the existing record's `override_source`, `audit_upgrade`, `escalations`, `applied_tier`, and every TierResolution field (`panel_tier`, `round_cap`, `codex_model_role`, `audit_evaluated`, `escalated_round`) forward unless an explicit arg replaces them; forbid floor logic from overwriting `operator`. Keep backward compatibility for callers that pass no override/audit fields.

CLI:

- Add `difficulty resolve-panel` (registered in `cli.py` per G-CLI-1). Inputs: `--record-file`, optional `--override`, and a deterministic `--audit-roll` (or `--rng-seed`) test seam. Outputs: `PANEL_TIER`, `ROUND_CAP`, `CODEX_MODEL_ROLE`, `AUDIT_EVALUATED`, `AUDIT_UPGRADE`, `OVERRIDE_SOURCE`.

### UPDATED: python/larch/review/review_threshold.py

(FINDING_5) `check-reviewer-failure-threshold` validates `--panel hard|simple` and exits on any other token. Keep that contract stable: callers map the resolved tier to the legacy `--panel` token via `difficulty.threshold_panel_for_tier` (`TRIVIAL→simple`, `MODERATE/HARD→hard`) at the dispatch/core boundary. Do NOT pass tier names into `--panel`. No behavior change inside this file unless a test shows the mapping cannot be expressed; in that case add tier-token acceptance here. List consumers that must adopt the mapping: `review_dispatch_panel.py`, `review_core_body.py`, `skills/review/SKILL.md`, `skills/implement/scripts/test-implement-review-token-propagation.sh`.

### UPDATED: python/larch/review/review_dispatch_panel.py

Thread tier into panel dispatch. Add accepted args: `--tier TRIVIAL|MODERATE|HARD`, `--escalated-round true|false`, optional `--skip-prune true|false`.

Panel composition (gated on `--tier`; FINDING_10):

- **TRIVIAL** (singles): emit one Codex row per static archetype and at most one Codex dynamic row; **suppress the Cursor half** in both static and dynamic paths. If Codex is unavailable and Cursor is available, flip the whole singles panel to Cursor rows. Do NOT apply drop-the-half logic (there is no pair). Both vendors down → existing degraded-tools/#5889 policy.
- **MODERATE**: Codex + Cursor pairs per static and dynamic archetype; Codex rows use model role `review`; a missing vendor drops that half (#5886).
- **HARD**: same pair shape; Codex rows use model role `default`.
- **Dynamic archetype rows** use the same tier→Codex model role as static rows via `codex_review_model_role(tier)` (`review` for TRIVIAL/MODERATE, `default` for HARD); do not hardcode the default role for dynamic Codex rows (FINDING_5 round 2).

Emit derived `PANEL_SHAPE` (`singles` for TRIVIAL, `pairs` otherwise) so existing `PANEL_SHAPE` consumers keep working, plus `PANEL_TIER`, `PANEL_ROUND_CAP`, `PANEL_ESCALATED_ROUND`, and `AUDIT_UPGRADE` when known. Map tier→`--panel simple|hard` for the failure-threshold call.

Pruning: round 1 unpruned; prune before non-escalated round 2 for MODERATE/HARD; never prune a round with `--escalated-round=true`; allow round-3 pruning when HARD reaches round 3; preserve the #5733 `-output` normalization path.

### UPDATED: python/larch/review/review_core_body.py

(FINDING_9) `review core` currently emits `cap-reached` once `round_num >= 2` with accepted findings. Replace that with tier-aware logic: emit `fix-required` while `round_num < resolved_round_cap`, and `cap-reached` only on the final allowed round for the resolved tier. Accept `--tier` and `--escalated-round`; thread the resolved cap from `--tier` / `PANEL_ROUND_CAP`; forward both to `review dispatch-panel`; emit tier KVs (`PANEL_TIER`, `EFFECTIVE_ROUND_CAP`) in `REVIEW_CORE_STATUS`. Map tier→`--panel simple|hard` at this boundary. Do not change aggregation, voting, or tally.

### UPDATED: python/larch/review/round_runner.py

Replace hard-coded panel assumptions with tier-aware args: add `args.panel_tier` and `args.escalated_round`; pass `--tier`, `--escalated-round`, and the current prune ledger to `review core`. Keep the review-core procedure unchanged; include tier and escalation fields in round summaries; keep the dynamic archetype cap at `0..1`.

### UPDATED: python/larch/review/plan_review_round.py

(FINDING_11) Thread tier state through the plan-review round dispatch. In `run_plan_review_round` / `_round_args` (see `plan_review_loop.py`), read the persisted effective tier + escalated flag each round and pass `--tier` and `--escalated-round` into `plan-review panel-dispatch`. Do not rebuild fixed reviewer args.

### UPDATED: python/larch/review/review_and_fix.py

Make /implement Step 5 tier-aware.

- Add parser args: `--difficulty TRIVIAL|MODERATE|HARD` and an injected `--audit-roll` / RNG test seam.
- Resolve the initial `TierResolution` from `$IMPLEMENT_TMPDIR/difficulty-rating.json`, override, floors, and the audit via `difficulty.resolve_panel_tier`; set `round_cap = tier_ceiling(effective_tier)`; track `effective_tier` per round.
- **Escalation computed separately from cap enforcement, applied before cap-hit** (FINDING_8): after each fix-applied round run the existing `_step5_post_round_gates` to get the substantiality/bulk-skip signal, but decide escalation first. When the gate signals substantial (or bulk-skip) at a TRIVIAL/MODERATE tier: bump `effective_tier = next_tier(effective_tier)`, recompute `round_cap = tier_ceiling(effective_tier)`, log the trigger via `append_escalation` (also sets `applied_tier`), mark the next round escalated, skip pruning for that escalated round, and continue instead of returning `cap-hit` until the HARD cap is exhausted. A run escalated to HARD at round 2 may reach round 3.
- **Resume never re-rolls** (FINDING_3, FINDING_17): when `--starting-round > 1`, load `applied_tier`, `audit_upgrade`, `escalations`, and `escalated_round` from `$IMPLEMENT_TMPDIR/difficulty-rating.json`, derive `round_cap` from the effective tier, and pass `--tier` / `--escalated-round` into the round runner. Never re-roll the audit on resume.
- Keep `bulk-skip` as an escalation trigger; keep `panel_skipped=self-review` behavior unchanged.
- Update KVs: `EFFECTIVE_ROUND_CAP`, `PANEL_TIER`, `AUDIT_UPGRADE`, `ESCALATED_FROM`, `ESCALATED_TO`, `ESCALATION_TRIGGER`.

### UPDATED: python/larch/review/review_prune.py

Generalize prune history:

- `prune_window_evaluated(round_num)` returns true for `round_num >= 2`, except callers explicitly skip pruning for an escalated round.
- `reviewer_prune_filter` for round 3 uses all prior ledger rows (rounds 1–2), not only round 1.
- Preserve `_normalize_code_label` exactly enough to keep the #5733 `-output` join fix.
- Regression coverage lives in `test_review_pipeline.py` (FINDING_6), not a new prune-only file.

### UPDATED: python/larch/review/plan_review_common.py

Replace constant `ROUND_CAP = 2` with tier-aware helpers. Keep default fallback `MODERATE`; return cap 2 for TRIVIAL/MODERATE and cap 3 for HARD. Expose a design-side resolver that reads `run-params.json` `difficulty_override`, `difficulty-rating.json` (or plan `difficulty:` metadata), and audit-upgrade state. Expose an **effective authorized cap** helper (distinct from the raw tier ceiling): authorized cap is 2 unless the continuation/escalation state recorded a substantiality/escalation reason permitting round 3. Use it for the design Step 3 pre-launch cap guard, `plan_review_continuation`, AND Gate C rendering — not only Gate C — so a HARD run cannot schedule round 3 without recorded authorization (FINDING_18/24, FINDING_10).

### UPDATED: python/larch/review/plan_review.py

Make the Step 3 loop tier-aware:

- Resolve the design plan-review `TierResolution` before the loop and persist it (see TierResolution sidecar below); store `PANEL_TIER`, `ROUND_CAP`, and audit state in Step 3 result envs; use the tier cap for the cap guard.
- Every design tier keeps Codex + Cursor pairs when available; never apply code-review vendor-shedding to design.
- Escalate from not-HARD **directly to HARD** when a round accepts round-total `>=2` high-severity in-scope findings (FINDING_14, FINDING_22 rationale). On an escalated design round: use the HARD model role, ceiling becomes 3, skip pruning for that round, and record the escalation so Gate C may authorize round 3.
- Keep Gate B, Gate C, tally, aggregation, and voters unchanged.

### UPDATED: python/larch/review/plan_review_loop.py

Update continuation logic:

- Replace static `ROUND_CAP` uses with the resolved cap, including the `review_count >= ROUND_CAP` branch in `plan_review_continuation` (FINDING_3).
- **Define escalation separately from continuation** (FINDING_14): compute the design escalation trigger from **round-total** accepted in-scope high severity — structured `blocking` or `important`, falling back to the high regex only when structured severity is absent. Bump to HARD only when total round `high >= 2` (one high finding must not escalate). Emit `PLAN_REVIEW_CONTINUE_REASON=escalated-high-accepted`, `PANEL_TIER`, and `REVIEW_ROUND_CAP`. Record the escalation/substantiality reason so the Gate C authorized-cap helper can permit round 3.

### UPDATED: python/larch/review/plan_review_panel.py

Add `--tier` and `--escalated-round`. TRIVIAL and MODERATE design panels are identical: Codex + Cursor pairs across the 4 static archetypes, Codex model role `review`. HARD: same pairs, Codex model role `default`. Dynamic plan-review rows follow the same design rule. Never drop a Cursor or Codex half by tier (existing availability handling may still omit an unavailable vendor's rows). Skip pruning only for escalated rounds. Preserve `--no-fallback`.

### UPDATED: python/larch/design/design_argv.py

Parse `/design --difficulty <tier>`: accept only `TRIVIAL|MODERATE|HARD` (case-insensitive, normalized to uppercase); reject missing/invalid values via the existing validation error path; add a parsed output key.

### UPDATED: python/larch/design/design_step0_env.py

(FINDING_15) Include `difficulty` in `PARSED_ENV_KEYS` and the emitted Step 0 parse-cache KVs so the override survives the Step 0-pre → Step 0b subshell boundary.

### UPDATED: python/larch/design/design_step0.py

(FINDING_15, FINDING_4) Forward the parsed `difficulty` override into the `design route` and `design init-runparams` commands so it reaches `run-params.json`. Add `--difficulty` to `init_runparams_main` and extend `_step0_init_driver_cmd` to pass the parsed Step 0-pre value through to `session write-run-params` (the same contract as `route_main`).

### UPDATED: python/larch/design/design_router.py

Persist `/design --difficulty` via `route_main`: forward the parsed override into `session write-run-params`; no OR-merge (use the latest explicit override only); on resume, keep the existing override unless a new valid `--difficulty` is passed (extend `route_main` optional args to accept a resume-time override).

### UPDATED: python/larch/design/design_gate_render.py

(FINDING_18/24) Render Gate C with the **effective authorized cap** from `plan_review_common`, not the raw tier ceiling. Keep option-hiding behavior; only offer another review (round 3) when the current count is below the authorized cap AND `plan_review_continuation` recorded an escalation/substantiality reason that permits round 3. Do not surface HARD round 3 after two non-substantial design rounds.

### UPDATED: python/larch/state/session_env.py

Extend `session write-run-params`: add optional `--difficulty`; validate empty|`TRIVIAL`|`MODERATE`|`HARD`; write `difficulty_override` in `run-params.json`; preserve backward compatibility for the missing key.

### UPDATED: python/larch/state/bootstrap.py

Persist the /implement override: add bootstrap option `difficulty_override`; write it into existing run flags (prefer no new sidecar file); when writing the initial `difficulty-rating.json`, pass the override into difficulty record construction (`override_source=operator`). Keep design-prior extraction unchanged.

### UPDATED: python/larch/report/run_log_flush.py

(FINDING_13) When refreshing/flushing a difficulty record, do not overwrite `audit_upgrade`, `override_source`, or `escalations`. Merge the existing record forward (through `difficulty write-record` merge-on-existing-output, or `resolve_applied_tier`) preserving `override_source`, `audit_upgrade`, `escalations`, and post-escalation `applied_tier` before `write_record`; forbid floor logic from replacing `operator`. Include escalation entries from Step 5 and design Step 3 records. Route `design_publish.py` and /review Step 4 (`skills/review/SKILL.md` `review log-phase` → `difficulty write-record`) through the same merged record.

### UPDATED: python/larch/report/progress_report.py

Include audit and escalation metadata in progress records when present; keep missing fields backward compatible; no #5992 analyzer logic.

### UPDATED: python/larch/report/final_report.py

Show the difficulty line with audit/escalation details when present, reusing `difficulty.difficulty_line`; keep existing final-summary structure.

### UPDATED: python/larch/git/pr_body.py

No behavior change unless the difficulty summary line needs to show audit/escalation text from `difficulty_line`.

### TierResolution sidecar (persisted, in `difficulty-rating.json`)

(FINDING_17) Before the first round on each surface, persist the resolved `TierResolution` into `difficulty-rating.json` (or a merged resume sidecar): `PANEL_TIER`, `ROUND_CAP`, `CODEX_MODEL_ROLE`, `AUDIT_EVALUATED`, `AUDIT_UPGRADE`, `OVERRIDE_SOURCE`. Update it after each audit/escalation via `resolve_panel_tier` / `append_escalation`. All resume, cap, dispatch, and heavy-worker paths read these fields and NEVER call the RNG again.

### UPDATED: skills/design/SKILL.md

Add `--difficulty <TRIVIAL|MODERATE|HARD>` to `argument-hint` and a compact flag-table row. State the override sets the starting plan-review tier, beats rating and floors, and is logged `override_source=operator`; state the 1:30 audit can still upgrade a below-HARD run (including operator-overridden) to HARD, logging both. Update Step 3 prose from fixed cap 2 to tier cap 2/2/3; keep design vendor pairs documented.

### UPDATED: skills/design/references/flags.md

Document `--difficulty <tier>` and `difficulty_override` in `run-params.json`; replace stale fixed-cap prose with 2/2/3 tier-cap prose; state no env knob disables the audit; state the audit is orthogonal to the override.

### UPDATED: skills/design/references/approval-gates.md

Update Gate C cap prose: replace static-cap references with the effective authorized cap (round 3 only when escalation/substantiality was recorded); keep renderer authority unchanged.

### UPDATED: skills/design/references/plan-review.md

Update topology docs: TRIVIAL/MODERATE → Codex `gpt-5.4-mini` + Cursor pairs, cap 2; HARD → Codex `gpt-5.5` + Cursor pairs, cap 3; escalation trigger round-total `>=2` high-severity accepted in-scope findings; escalated rounds skip pruning; round-3 prune window uses rounds 1–2.

### UPDATED: skills/implement/SKILL.md

Add `/implement --difficulty <tier>`: update `argument-hint`; add flag parsing; pass the override into Step 0 bootstrap and Step 5 review; replace fixed Step 5 cap prose with tier cap 2/2/3; state `--self-review` still skips the external panel but logs panel skipped; state the audit can upgrade a below-HARD override.

### UPDATED: skills/implement/scripts/step-0-bootstrap.sh

Accept `--difficulty`; validate empty|one of three tiers; pass it to `python/cli.py bootstrap invoke`; preserve resume behavior.

### UPDATED: skills/implement/scripts/step-5-review.sh

Read the difficulty override from persisted bootstrap run flags; call `review-and-fix step5 --difficulty "$DIFFICULTY_OVERRIDE"` when set; replace banner text with tier-aware cap wording; no `--panel` token.

### UPDATED: skills/implement/scripts/step-5-resume.sh

(FINDING_3) Read the persisted difficulty override and resolved tier state; pass `--difficulty` and the resolved cap to `review-and-fix step5` when resuming after MAV or coder handoff; do NOT recompute the random audit on resume — reuse recorded audit state.

### UPDATED: skills/review/SKILL.md

Add `/review --difficulty <tier>`: update `argument-hint`; parse the flag; run `difficulty resolve-panel` before the loop; keep default fallback `MODERATE`; track `effective_tier`, `round_cap`, `audit_upgrade`, `escalated_round`; pass `--tier` and `--escalated-round` to `review core`; after fix/check/classification use the existing substantiality judgment to decide escalation (escalation precedes pruning and skips pruning on the escalated round); allow HARD round 3 only when the substantiality gate continues the loop.

### UPDATED: skills/review/references/heavy-worker.md

(FINDING_11) Mirror `/review` tier behavior for the heavy-worker path: run `difficulty resolve-panel` once at parent Step 0 and pass `PANEL_TIER`, `ROUND_CAP`, `AUDIT_UPGRADE`, and `escalated_round` into the heavy-worker prompt/inputs; require the worker loop to reuse them (no RNG in the worker); replace the fixed two-round cap with the tier cap; preserve emitted scout and classification artifacts.

### UPDATED: README.md

Add `--difficulty` to the `/implement`, `/review`, and `/design` flag tables; replace fixed Step 5 / Step 3 cap prose with tier-cap prose.

### UPDATED: docs/review-agents.md

Document tiered composition: code review — TRIVIAL singles (Codex preferred, Cursor flip when Codex down), MODERATE pairs, HARD pairs with Codex hard model role; design review — always pairs, TRIVIAL/MODERATE share the v1 shape, HARD bumps Codex role and cap. Note the audit is orthogonal to the operator override.

### UPDATED: docs/collaborative-sketches.md

Update /design plan-review description: tier cap 2/2/3, design escalation trigger (round-total `>=2` high accepted), no design vendor shedding.

### UPDATED: docs/workflow-lifecycle.md

Update lifecycle summaries for the review loops and escalation.

### MAY_UPDATE: docs/skills.md

Update maintained skill docs for the three public `--difficulty` flags if this file enumerates skill flags.

### MAY_UPDATE: docs/configuration-and-permissions.md

Only if a new operator-visible config key is introduced (prefer none; `difficulty_override` lives in per-run `run-params.json`, not global config).

### MAY_UPDATE: docs/linting.md

Only if a new focused test target or harness contract is added.

### UPDATED: python/tests/calibration/test_difficulty.py

Add unit tests: no-rating fallback `MODERATE`; operator override beats floors; audit upgrades a below-HARD tier and logs `audit_upgrade=true`; **audit still fires under `override_source=operator` and logs both fields** (FINDING_21/23 behavior lock); HARD is never audit-upgraded; tier ceilings 2/2/3; `append_escalation` sets `applied_tier=to_tier`; `difficulty_line` renders audit/escalation compactly; `write-record` merge-on-existing-output preserves `override_source`/`audit_upgrade`/`escalations`/`applied_tier` and every TierResolution field (`panel_tier`/`round_cap`/`codex_model_role`/`audit_evaluated`/`escalated_round`) and floor cannot replace `operator` (FINDING_8); `append_escalation` sets round-specific `escalated_round` so resume does not treat a later non-escalated round as escalated (FINDING_11).

### UPDATED: python/tests/review/test_review_pipeline.py

(FINDING_6) Add `review core` tier arg parsing + pass-through (`--tier TRIVIAL` reaches dispatch; invalid tier exits 2; `--escalated-round true` skips pruning) AND the prune-window regression coverage: round 2 uses round-1 ledger data; round 3 uses rounds 1–2 ledger data; **`-output` label normalization yields non-zero round-1 ledger counts before round-2 pruning relies on them** (#5733 lock); escalated-round skip leaves the manifest unpruned. Add tier→`--panel simple|hard` mapping and `PANEL_SHAPE` compatibility assertions.

### UPDATED: python/tests/review/test_review_and_fix.py

Add Step 5 loop tests: TRIVIAL starts with Codex singles; TRIVIAL Codex-down flips to Cursor singles; MODERATE uses pairs and drops the missing half; HARD uses cap 3 and Codex hard role; **substantial round 1 escalates TRIVIAL→MODERATE for round 2**; substantial escalation reaches HARD and permits round 3; **escalation is applied before `cap-hit`** (substantiality on the last allowed lower-tier round bumps rather than stopping) (FINDING_8); escalated round does not prune; audit upgrade runs HARD and logs `audit_upgrade=true`; operator override + audit logs both; resume loads recorded tier state and does not re-roll the audit.

### UPDATED: python/tests/review/test_plan_review.py

Add design loop tests: TRIVIAL and MODERATE both use cap 2; HARD uses cap 3; round-total `>=2` high-severity accepted escalates to HARD; **one high finding does NOT escalate** (FINDING_14); design escalates not-HARD→HARD directly (not through an inert MODERATE); escalated design round skips pruning; **Gate C exposes round 3 only when an escalation/substantiality reason was recorded** (FINDING_18/24); **the authorized-cap guard also blocks a HARD round 3 at the Step 3 pre-launch/continuation guard without recorded authorization** (FINDING_10, HARD one-high no-round-3 case); Gate C cap rendering tracks the authorized cap.

### UPDATED: python/tests/review/test_plan_review_panel.py

Add panel-manifest tests: design TRIVIAL/MODERATE keep Codex+Cursor pairs; design HARD keeps pairs but uses the Codex hard model role; code-side TRIVIAL emits singles (one vendor) and flips to Cursor when Codex is down; dynamic rows follow the same model-role/vendor rule.

### UPDATED: skills/design/scripts/test-step3-review-cap.sh

Update the cap harness for tier cap 2/2/3: keep existing cap-entry behavior; add a HARD round-3-reachable case; add a design escalation-trigger case; add a Gate-C authorized-cap case (no round 3 without recorded escalation).

### UPDATED: skills/design/scripts/test-dispatch-plan-review-panel.sh

Add static checks for model roles and pair shape by tier (design always pairs; HARD Codex role `default`).

### UPDATED: skills/implement/scripts/test-implement-review-token-propagation.sh

Update argv parsing to allow `--difficulty`; assert tier→`--panel` mapping and `PANEL_SHAPE` propagation stay compatible.

### MAY_UPDATE: skills/implement/scripts/test-implement-fence-shape.sh

Only if Step 5 fence prose changes the checked fence shape.

### MAY_UPDATE: python/tests/implement/test_checks.py

Only if relevant-check targeting needs new focused files or target mappings.

## Edge cases

- **No rating file**: use `MODERATE`.
- **Operator override below floor**: use the override as the starting tier; log `override_source=operator`; floors do not raise it.
- **Operator override + audit (1:30)**: run HARD; log BOTH `override_source=operator` and `audit_upgrade=true` (binding Round 1 decision).
- **Effective starting tier already HARD**: audit never fires (nothing to upgrade).
- **Resume after audit/escalation**: never re-roll; read recorded `applied_tier` / `audit_upgrade` / `escalations` from `difficulty-rating.json`.
- **TRIVIAL with Codex down**: flip the whole singles panel to Cursor (no drop-the-half).
- **TRIVIAL with both vendors down**: existing degraded-tools / #5889 policy.
- **MODERATE/HARD with one vendor down**: drop that vendor half (#5886).
- **Design review**: never use code-review vendor-shedding; escalation goes not-HARD→HARD directly.
- **Escalated round**: run the full next-tier (code/review) or HARD (design) panel; no pruning.
- **HARD round 3**: reachable only via the substantiality gate (code/review) or a recorded design high-severity escalation; Gate C never surfaces it without that record.

## Failure modes

- **Random audit non-deterministic in tests**: inject the roll/RNG seam (`--audit-roll` / `--rng-seed`).
- **Record refresh drops audit/escalation/override fields**: merge existing record fields forward before `write_record` (FINDING_13); regression test in `test_difficulty.py`.
- **Prune regression empties panels via label drift**: `-output` non-zero round-1 ledger assertion in `test_review_pipeline.py` (#5733 lock).
- **Tier token leaks into `--panel` and fails the threshold check**: map tier→`simple|hard` at the dispatch/core boundary; keep `PANEL_SHAPE=singles|pairs` (FINDING_5); token-propagation harness asserts it.
- **Escalation lost to premature `cap-hit`**: compute escalation before cap enforcement (FINDING_8); test the TRIVIAL→MODERATE→HARD path.
- **Prompt-side /review or heavy-worker loses tier state**: persist `PANEL_TIER`/`ROUND_CAP`/audit fields and read them on resume (FINDING_11, FINDING_17).

## Testing strategy

Run focused Python tests:

- `python3 -m pytest python/tests/calibration/test_difficulty.py`
- `python3 -m pytest python/tests/review/test_review_and_fix.py`
- `python3 -m pytest python/tests/review/test_review_pipeline.py`
- `python3 -m pytest python/tests/review/test_plan_review.py`
- `python3 -m pytest python/tests/review/test_plan_review_panel.py`

Run focused harnesses:

- `make test-review-and-fix`
- `make test-review-core`
- `make test-dispatch-panel-core`
- `make test-dispatch-plan-review-panel`
- `make test-step3-review-cap`
- `make test-implement-review-token-propagation`
- `make test-implement-fence-shape` (only if Step 5 fence literals changed)

Run lint for changed Python:

- `make py-lint`
- `make py-test` if the touched Python surface is broad enough that focused tests are insufficient.


## Acceptance

- Panels resolve per the tier tables across all three skills; ceilings 2/2/3 enforced; HARD round 3 reachable only via the substantiality gate.
- Escalated rounds run the next tier's full panel; escalation precedes pruning (design escalates the not-HARD panel directly to HARD, since design TRIVIAL and MODERATE share one panel).
- 1:30 audit upgrades occur and are flagged; `--difficulty` override wins over rating and floors and is logged `override_source=operator`. The audit stays orthogonal: it may still upgrade a below-HARD run (including an operator-overridden one) to HARD, logging both `override_source=operator` and `audit_upgrade=true`.
- TRIVIAL with Codex down flips to Cursor singles; both-down follows #5889.
- No regression of the #5733 join fix; a regression test asserts the round-1 prune ledger populates non-zero before round-2 pruning relies on it.

difficulty: HARD
review_status: complete
rounds_completed: 2
diff_added: 1900
diff_deleted: 210
mechanical_churn: false
diff_lines: 2110
