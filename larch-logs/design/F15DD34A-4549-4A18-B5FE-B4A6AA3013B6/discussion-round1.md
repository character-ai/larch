## Decision 1: Consumer cutover scope for sourced-only bash libraries
- **Question**: Does B4 update surviving bash orchestrators that SOURCE the B4 lib files, or defer to C-phases?
- **Resolution**: Partial-retire pattern. Executable scripts (run-external-agent.sh, launch-*.sh, agent-model-args.sh, etc.) are retired in migrated-scripts.tsv. Sourced-only lib files (lib-external-launcher-common.sh, lib-cursor-launcher-common.sh, lib-codex-launcher-common.sh, lib-cursor-auth.sh, lib-failed-agent-stderr-tail.sh) are ported to Python but NOT added to migrated-scripts.tsv in B4. Each C-phase issue adds a lib when it rewrites that lib's last bash consumer.
- **Source**: user (AskUserQuestion, Step 1c)

## Decision 2: C-phase issue updates
- **Question**: Should B4 communicate the lib-retirement responsibility to C-phase issues?
- **Resolution**: Yes. B4 posts a comment on the relevant blocking C-phase issues (C1a #3676, C1b #3677, C2 #3678, C3a1 #3680, C3c #3682, C4b #3684) noting that each owns the sourced-lib retirement for its specific consumers.
- **Source**: user (mid-design message)

## Decision 3: launch-codex-implement.sh and launch-cursor-implement.sh
- **Question**: Does B4 update the implement scripts (C4b scope) when their executable references are retired?
- **Resolution**: Yes, minimally. B4 updates only the executable-path references (e.g., run-external-agent.sh → python3 cli.py, agent-model-args.sh → python3 cli.py). Full script rewrite stays with C4b. This keeps lint-retired-scripts green while B4 is merged and C4b is still open.
- **Source**: codebase (migration playbook: lint-retired-scripts CI constraint)

## Decision 4: Surviving bash callers of retired executables (non-lib sourcing)
- **Question**: Which surviving bash scripts need executable-path updates in B4?
- **Resolution**: launch-review.sh, lint-fix-loop.sh, dispatch-plan-voters.sh, run-negotiation-round.sh, dispatch-code-voters.sh, launch-codex-drafter.sh, ship-pr.sh, check-reviewers.sh, dispatch-with-waterfall.sh. Only executable-path references are updated (minimal). Scripts keep sourcing the still-alive lib files.
- **Source**: codebase (grep of direct executable references)

4 decisions resolved.
