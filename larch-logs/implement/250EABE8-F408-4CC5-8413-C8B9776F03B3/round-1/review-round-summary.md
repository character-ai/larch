# Review Round 1

- Mode: `diff`
- 2 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Cursor max-mode docs still describe risk gating while launch is unconditional
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: important
- **Concern**: Item 1 fixes Codex effort docs but leaves Cursor max-mode described as risk-gated in the same edited bullet. `_review_launch_cursor` always wraps with `/max-mode on.` regardless of `args.risk`; docs-only low-risk or `launch-review --risk low` still runs full max-mode. Either gate Cursor wrapping on coerced risk (and wire `classify-diff` to `--risk` on initial launch) or narrow the Cursor sentences to say max-mode is unconditional, like Codex effort.


### FINDING_10: Structural harness `list_tail` missing `--emergency` after SKILL.md update
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: important
- **Concern**: `SKILL.md` removed-argv list now includes `--emergency` but `scripts/test-implement-positional-issue.sh` still greps the old exact tail ending at `--no-dynamic-archetypes`. `make test-implement-positional-issue` / `make lint` fails with "missing removed-argv flag list tail" on this branch. Update `list_tail` in `scripts/test-implement-positional-issue.sh` to include `--emergency` (and optionally grep the migration error text); rerun `make test-implement-positional-issue`.


