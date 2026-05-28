## Decision 1: Loop architecture (refactor vs new feature)
- **Question**: Where does the multi-round counter / cap live — extend `plan-review-loop.sh` in-place, or a separate wrapper script?
- **Resolution**: Refactor. The orchestrator-driven multi-round loop (today driven by `SKILL.md` Gate C re-runs of single-pass `plan-review-loop.sh`) is moved into the bash script `plan-review-loop.sh` itself. `LARCH_DESIGN_ROUND_CAP` (default 5) bounds the internal loop. The existing SKILL.md tier caps (3 SIMPLE / 5 HARD via `review-round-count.txt`) remain as the outer cap on Gate-C-driven *fresh loops*.
- **Source**: user

## Decision 2: Gate C "Re-run review panel"
- **Question**: After the internal loop converges, hits cap, or zero-finds, is Gate C's "Re-run review panel" option preserved?
- **Resolution**: Yes — keep it. One click = a fresh multi-round loop. SKILL.md tier cap bounds total fresh loops; LARCH_DESIGN_ROUND_CAP bounds each one.
- **Source**: user

## Decision 3: Forensic publishing pattern
- **Question**: How is forensic evidence balanced against repo bloat in `larch-logs/design/<RUN_ID>/`?
- **Resolution**: Follow `/implement`'s code-review pattern. Per-round subdirectories under `plan-review/round-N/` hold a distilled allowlist (no raw `*-output.txt`, etc.); top-level holds the post-loop plan + accepted-findings + per-round forensics. Mirror `scripts/larch-log.sh write-round`'s allowlist semantics (see lines 73-95).
- **Source**: user

## Decision 4: Convergence threshold scope
- **Question**: Does the convergence threshold count OOS findings, or only in-scope?
- **Resolution**: In-scope only. Match today's `ACCEPTED_COUNT` semantics in `plan-review-loop.sh` (line 676 counts `### FINDING_N:` blocks in `accepted-plan-findings.md`, not OOS). OOS items are filed separately at Step 5b and don't block plan convergence. `IMPORTANT_ACCEPTED_COUNT` also counts in-scope-only.
- **Source**: user

## Decision 5: Revision waterfall total failure
- **Question**: If the Codex → Cursor → Claude revision waterfall fails on all tiers in a mid-round revision, what does the loop do?
- **Resolution**: Bail to Gate B with the un-revised plan, accumulated accepted findings, and a degraded marker. Loop stops iterating; user retains control. Aligns with current "panel-failed" semantics (degraded) but explicitly distinct.
- **Source**: user

## Decision 6: Auto-apply scope (all rounds, no user query)
- **Question**: Are final-round / convergence-round accepted findings auto-applied like mid-round ones, or do they flow to Gate B?
- **Resolution**: All rounds auto-apply accepted findings via `revise-plan-with-waterfall.sh`. No mid-loop user queries. Final/convergence-round findings are ALSO auto-applied. This deviates from the issue body's "Final-round and convergence-round accepted findings are NEVER auto-applied" — user explicitly overrode. Gate B's role becomes a passive summary or is restructured (architectural; Step 2a to resolve). The "assessor" concept the user mentioned is deferred to #2953 — out of scope for #2871.
- **Source**: user

## Decision 7: Round cap by tier
- **Question**: Does `LARCH_DESIGN_ROUND_CAP` differ between SIMPLE and HARD, or is it uniform?
- **Resolution**: Uniform default 5 for both tiers. SIMPLE plans typically converge in 1-2 rounds (smallest-change bias); the cap is a safety net. One env var, one default. Operators can override via env.
- **Source**: user

## Decision 8: OOS timing
- **Question**: When are OOS items filed as GitHub issues during multi-round?
- **Resolution**: Accumulate across all rounds; file once at Step 5b after Gate C. Today's Step 5b flow stays unchanged. `plan-review-loop.sh` writes a top-level `oos-accepted-design.md` that is the union (with per-round dedup) of every round's OOS. No `/larch:issue` calls inside the loop.
- **Source**: user
