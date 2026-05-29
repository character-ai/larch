## Decision 1: Tier-selection gate behavior
- **Question**: With SIMPLE as the new default, what happens to the interactive SIMPLE-vs-HARD `AskUserQuestion` "tier gate" (Step 0b sub-step 5) that fires when no tier flag is passed?
- **Resolution**: Remove the gate entirely. No `--hard` ⇒ run SIMPLE directly with no prompt. HARD becomes opt-in via `--hard` only. There is no remaining interactive tier selection.
- **Source**: user

## Decision 2: Behavior when `--simple` is still passed
- **Question**: After `--simple` is removed with no backward compatibility, how should `/design` react if a user still passes `--simple`?
- **Resolution**: Reject with a clear error before Step 0 so `--simple` is never silently swallowed as positional/verbal feature text (a footgun). Prefer a generic "unknown flag" style message rather than a dedicated `--simple`-naming hint, to honor "remove all mentions of --simple". (Exact message wording is a plan-level detail.)
- **Source**: user

## Decision 3: Removal scope
- **Question**: Where must `--simple` mentions be removed?
- **Resolution**: Remove ALL live-surface mentions of the `--simple` argument: `skills/design/SKILL.md`, `skills/design/references/flags.md`, `skills/design/references/approval-gates.md`, `README.md`, `docs/*` (installation-and-setup, issue-anchored-plan, skills, workflow-lifecycle), `.claude-plugin/plugin.json` argument hint, and the design tests (`scripts/test-design-structure.sh`, `skills/design/scripts/test-design-driver.sh`). No backward compatibility (do not accept `--simple` as a deprecated/aliased flag).
- **Source**: user

## Decision 4: Immutable-history boundary (do NOT touch)
- **Question**: Are committed run logs and dated changelog entries in scope?
- **Resolution**: No. Do NOT edit committed `larch-logs/**` run artifacts (immutable history) or dated `CHANGELOG.md` entries (historical record). Mirrors the #3176 `--trivial`-removal scope boundary.
- **Source**: codebase / convention

## Decision 5: Tier semantics unchanged
- **Question**: Does the SIMPLE/HARD tier behavior itself change?
- **Resolution**: No. SIMPLE (no sketches, no dialectic, full review panel, 3 total review runs) and HARD (4 sketches, dialectic, full panel, 5 total review runs) keep their current semantics. Only the DEFAULT tier and the public flag surface change. The now-vacuous `--simple`/`--hard` mutual-exclusion prose collapses to single-tier-flag handling (plan-level detail).
- **Source**: user
