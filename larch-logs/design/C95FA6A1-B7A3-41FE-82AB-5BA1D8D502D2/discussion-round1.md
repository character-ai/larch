## Decision 1: Is the blocker (#6158) resolved?
- **Question**: Issue #6160 is "Blocked by the scaffold/payload instrumentation child" — is that child done?
- **Resolution**: Yes. #6158 ("per-section scaffold/payload instrumentation for generated slot prompts") is closed/DONE, merged via PR #6223. `scaffold_bytes`/`scaffold_tokens`/`payload_bytes`/`payload_tokens` columns now exist in `panel-prompt-sizes.tsv` (`python/larch/report/tokens.py`), and `measure_panel_cost()` ranks by scaffold bytes. #6160 is unblocked.
- **Source**: codebase (gh issue/PR history, git log)

## Decision 2: Which builders and code paths are in scope?
- **Question**: "Specialist and voter generated prompt scaffolds" — which exact functions/paths?
- **Resolution**: In scope: (a) the dynamic "no-agent" implement-specialist prompt construction in `python/larch/review/review_dispatch_panel.py` (backs `generated/no-agent:specialist` slots dispatched at /implement Step 5); (b) the static prose inside `render_voter_main` in `python/larch/rendering/rendering.py`, which serves both design plan-review and implement code-review voter prompts. Out of scope: static `agents/*.md` specialist files (round XI's territory, protected by the panel-tier skill-closure-growth ratchet), the design plan-review specialist builder in `plan_review_panel.py` (sibling #6159), and aggregator builders (sibling #6161). Per umbrella #6166: "Children are designed independently."
- **Source**: codebase (issue "Sources:" line, sibling issue titles, #6166 umbrella)

## Decision 3: What must stay byte-identical (frozen surface)?
- **Question**: What parser-facing grammar must not change?
- **Resolution**: Finding and OOS anchors, `YES`/`NO`, the severity set, `ELIGIBLE_VOTERS`/`EFFECTIVE_VOTERS`/`vN_tool` keys, and the anti-format directive — explicitly enumerated in the issue's Scope section. Treat as byte-identical constraints on the compressed output.
- **Source**: issue body (explicit)

## Decision 4: What compression style/precedent applies?
- **Question**: How aggressive should the rewrite be — full restructure or minimal trims?
- **Resolution**: Follow the #5979 precedent (prior voter-prose density pass, round XI): prefer deletion and sentence folding over rewrites; never touch parser-facing tokens (`FINDING_N`, `OOS_N`, severity/uncertain keys, etc.); smallest-change bias per repo convention.
- **Source**: codebase (#5979 "Implementation notes")

## Decision 5: How is "measured pass" satisfied?
- **Question**: The acceptance requires a "measured scaffold-byte drop per the new columns" — how should this be captured?
- **Resolution**: Use the #6158 instrumentation directly: render the specialist/voter prompts with `--payload-bytes-output` (or inspect `panel-prompt-sizes.tsv` rows) before and after the prose edit, and/or run `python3 python/cli.py token measure-panel-cost` to compare scaffold-byte totals for the affected slot kinds. This becomes a concrete plan step, not a user decision.
- **Source**: codebase (#6158 plan, `tokens.py`)

## Decision 6: How is "no ratchet raise" checked?
- **Question**: Which ratchet does the acceptance criterion refer to?
- **Resolution**: The panel-tier `skill-closure-growth` lint (`python/larch/lint/lint_skill_closure_growth.py`, `python/skill-closure-baseline.json`), which guards `agents/*.md` sizes — there is no separate scaffold-byte ratchet yet. Since this task only edits Python string literals, not `.md` files, it's expected to be a no-op check; the plan will still run `python3 python/cli.py lint skill-closure-growth --skill panel-tier` as a safety net, matching #5979's testing strategy.
- **Source**: codebase (`lint_skill_closure_growth.py`, #5979 testing strategy)
