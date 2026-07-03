## Decision 1: /design plan-review escalation trigger
- **Question**: /design has no fix-coder, so it can't reuse the full `_step5_post_round_gates` (no structural-LOC / findings-fixed signal). What accepted-finding condition trips escalation from the ceiling-2 (gpt-5.4-mini + Composer pairs) panel to the HARD panel (gpt-5.5 pairs, ceiling 3)?
- **Resolution**: Escalate when a round accepts **≥2 high-severity in-scope findings**. Reuses the existing gate's most portable clause; consistent across all three skills; no arbitrary count.
- **Source**: user

## Decision 2: No-rating fallback tier
- **Question**: When no difficulty rating is resolvable at panel-composition time (scout failed, degraded run, or a skill path that produced no rating), what tier applies?
- **Resolution**: **MODERATE** (matches the existing `--fallback-tier` default). Keeps Codex+Cursor pairs at ceiling 2; avoids under-reviewing a possibly-hard run. Moot for /design (TRIVIAL and MODERATE are the same panel there); only affects /implement + /review where TRIVIAL = singles.
- **Source**: user

## Decision 3: Operator override vs. random audit precedence
- **Question**: If `--difficulty=<below HARD>` is set AND the 1:30 audit fires on that same run, which wins?
- **Resolution**: **Audit still fires** — run HARD, log BOTH `override_source=operator` and `audit_upgrade=true`. The audit is orthogonal to the rating pipeline; suppressing it under override would bias the #5992 calibration sample.
- **Source**: user

## Hard constraints (from issue #5991, binding scope boundaries)
- **Procedure unchanged per tier**: findings aggregator, voting panel (#5887), pruning (#5886), and fix coder (#5888) run identically at every tier. ONLY reviewer composition, reviewer model, and the round ceiling vary with the applied tier.
- **#5733 join fix must not regress**: the round-3 branch (HARD only) generalizes the prune window (round 3 prunes on rounds 1-2 data) and MUST preserve the `-output` label-join fix. Acceptance requires a regression test asserting the round-1 prune ledger populates non-zero before round-2 pruning relies on it.
- **/design always keeps vendor pairs**: every /design tier keeps Codex + Cursor pairs across the 4 static archetypes (58% of accepted plan findings were Cursor-only). The #5886 drop-the-half rule does NOT apply to /design. v1 collapses design TRIVIAL and MODERATE to one panel (gpt-5.4-mini + Composer, ceiling 2); HARD bumps the Codex half to gpt-5.5 with ceiling 3.
- **/implement Step 5 + /review escalation reuses the existing `_step5_post_round_gates`** (≥2 high-sev accepted, ≥100 structural LOC of fixes, ≥8 findings fixed, or bulk-skip). No pruning on an escalated round; escalation precedes pruning. Ceiling follows the tier in effect (escalated-to-HARD-at-round-2 may reach round 3).
- **TRIVIAL singles availability rule** (/implement + /review only): TRIVIAL = one Codex/gpt-5.4-mini reviewer per archetype (3 static + at most 1 dynamic). Codex down → flip the whole panel to Cursor/composer-2.5 singles (NOT drop-the-half; singles have no pair redundancy). Both vendors down → #5889 policy.
- **MODERATE/HARD drop-the-half** (/implement + /review): a missing vendor drops that half (#5886 rule).
- **Ceilings 2/2/3** enforced across all three skills; HARD round 3 reachable only via the substantiality gate.
- **`--difficulty=<tier>` override** on /implement, /review, /design: beats rating and floors, logged `override_source=operator`. Override sets the starting tier; in-run escalation stays active.
- **1:30 random audit**: runs rated below HARD, 1 in 30, run the HARD panel instead, logged `audit_upgrade=true`. Must remain even when early confusion matrices look clean.
- **Out of scope**: the #5992 difficulty-calibration analyzer (separate open issue). This issue only consumes the rating and composes panels.
