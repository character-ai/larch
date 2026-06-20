# Design Discussion — Round 1 (Issue #4775: Score and calibrate voters against realized outcomes)

## Decision 1: Scope depth — lightweight metric only
- **Question**: How deep should this issue go on the lightweight→rich spectrum?
- **Resolution**: Lightweight only. Compute **inter-voter agreement** (each voter slot vs the panel verdict) and **flag chronic outlier voters**, from the per-voter votes vs panel verdict already committed in `findings-classification.tsv`. **No** realized-outcome / issue-fate / revert calibration in this issue.
- **Source**: user

## Decision 2: Two surfaces — live per-run scoreboard AND post-hoc analyzer
- **Question**: Modify the live voting loop, or read-only post-hoc analysis?
- **Resolution**: Both. (a) A **live per-run voter scoreboard** artifact emitted during the voting tally (analogous to the existing reviewer scoreboard). (b) A **post-hoc analyzer** that aggregates voter agreement across committed run-logs.
- **Source**: user

## Decision 3: Post-hoc report home — new sibling skill
- **Question**: Extend `/fluff-analysis` or add a sibling?
- **Resolution**: New sibling skill/script (e.g. `voter-calibration`), separate from `/fluff-analysis`. Keep `fluff-analysis` single-responsibility (reviewer fluff).
- **Source**: user

## Decision 4: Corpora — both panels
- **Question**: Which voter panels are in scope?
- **Resolution**: Both. The /design plan-review panel (Claude/Codex/Cursor) and the /implement & /review code-review panel (3 Cursor archetypes). Shared math in `python/voting.py`; live wiring touches both tally paths; analyzer reads both `larch-logs/design` and `larch-logs/implement` (plus `review` where present).
- **Source**: user

## Decision 5: Dependency #4764 is satisfied
- **Question**: Is the de-biasing prerequisite (strip ballot attribution) in place?
- **Resolution**: Yes. #4764 ("[DONE] Strip author attribution from voting ballots") has landed. Ballot neutralization (`anonymous`) + `proposer-map.tsv` restore machinery already exist in `python/voting.py`. The reshaped classification/tally surface this issue builds on is present.
- **Source**: codebase

## Decision 6: Data already exists — additive, schema-preserving
- **Question**: Is the per-voter data needed for agreement already committed?
- **Resolution**: Yes. 995 design + 851 implement `findings-classification.tsv` files carry per-voter `vN_vote/correctness/severity/quality/uncertain` plus the panel `voting_result`. Design schema is 22-col **with** `vN_tool`; code-review schema is 18-col **without** `vN_tool`. **Hard constraint**: this change must be additive and MUST NOT break those existing schemas or their downstream parsers.
- **Source**: codebase

## Decision 7: Voter identity + degraded panels
- **Question**: How are voters identified across runs, and what about degraded panels?
- **Resolution**: Design voters identified by `vN_tool` (Claude/Codex/Cursor); code-review voters identified positionally by canonical slot (v1=validity, v2=plan-fidelity, v3=pragmatism, Cursor). Single-voter fallback (1 eligible voter, e.g. Claude in code-review) and 0-voter main-agent paths make inter-voter agreement **undefined** — must be handled gracefully (excluded from agreement denominators), not crash.
- **Source**: codebase

## Hard constraints (must not break)
- Existing **reviewer** scoreboard (`python/voting.py::scoreboard_main`) and point competition.
- The voting tally and acceptance thresholds (`accept_finding`, `classify_result`, tier rules).
- Downstream parsers of `findings-classification.tsv` (both 22-col and 18-col schemas) — change must be additive.
- Canonical docs: `docs/voting-process.md`, `docs/point-competition.md` (update prose if behavior is added; do not contradict).

## Non-goals (explicitly out of scope)
- Realized-outcome / issue-fate / revert linkage (the "richer" calibration). OOS realized-fate for **reviewer** points is separately tracked by #4776.
- Changing vote thresholds, acceptance rules, or dedup.
- Token-allocation-by-score (future; #4771).
- Modifying `/fluff-analysis`.
- Any change that penalizes/rewards voters live (this issue measures + reports; it does not yet wire voter scores into spawning or token budgets).
