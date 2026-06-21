## Decision 1: In-flight overlap with #4776
- **Question**: #4776 (IMPLEMENTING) and #4777 both edit `docs/point-competition.md` and `skills/shared/voting-protocol.md` (different sections; live code disjoint). Postpone, or proceed?
- **Resolution**: Proceed with the design now; wire `#4777 blocked-by #4776` so #4777's `/implement` lands after #4776 merges and the shared docs settle. Edge wired and verified.
- **Source**: user

## Decision 2: Experimental, off by default
- **Question**: Should the uniqueness bonus be default-on or gated?
- **Resolution**: Off by default. Experimental, monitoring-gated. Not a default-on change.
- **Source**: issue

## Decision 3: Skill scope
- **Question**: Apply the sole-finder bonus to /design plan review only, or both /design and /review?
- **Resolution**: Both /design and /review. Implement once in a shared `python/voting.py` helper that both tally layers call. One shared rule in the docs.
- **Source**: user

## Decision 4: Gating knob and magnitude
- **Question**: How is the bonus enabled and sized?
- **Resolution**: Single env-var knob, default `0` (off). A positive float both enables the bonus and sets its magnitude. Suggested experimental value `+0.25`. No separate boolean flag.
- **Source**: user

## Decision 5: Which items qualify
- **Question**: In-scope accepted findings only, or also accepted OOS items?
- **Resolution**: In-scope accepted findings only. OOS scoring/fate is #4776's domain. The panel-diversity rationale targets real in-scope findings.
- **Source**: user

## Decision 6: Additive, not replacement
- **Question**: Does the bonus replace base points or add on top?
- **Resolution**: Additive. Sole finder keeps the base `+1`/`+2`, plus the uniqueness bonus. "A small bonus".
- **Source**: issue

## Decision 7: Definition of "sole finder"
- **Question**: What counts as the sole finder of an accepted finding?
- **Resolution**: A finding whose restored proposer attribution names exactly one reviewer (not merged/deduplicated with any other reviewer). Findings merged across reviewers during dedup are not sole-finder and keep flat shared credit.
- **Source**: codebase

## Hard constraints (must not break)
- Live tally output byte-compatibility contracts: do not change scores when the env var is unset/0. Default-off must reproduce current scoreboard numbers exactly.
- Do not alter `python/voting.py::classify_result` accept/neutral/reject classification or vote thresholds.
- Keep `body_severity` non-scoring (forensic only).
- OOS scoring stays flat (+1/0/-1); the bonus never touches OOS rows.
- Reviewer pruning math stays unweighted accepted-minus-rejected; the bonus does not feed pruning.
- Coordinate with #4776 on the two shared docs; edit only the in-scope sections.
