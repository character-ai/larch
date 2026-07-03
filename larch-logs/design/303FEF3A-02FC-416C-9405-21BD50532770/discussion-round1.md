## Decision 1: Migration scope — which files
- **Question**: Which files/call sites should the plan migrate off inline `awk -F=` KV-parsing?
- **Resolution**: All 3 at-risk files named in the issue: `.claude/skills/release/SKILL.md` Step 8 (6 call sites, confirmed corrupted), `skills/pause/SKILL.md` (4 call sites), `skills/deps/SKILL.md` (3 KV-parsing call sites, excluding its separate shell-argv `$1`/`$2` dispatch).
- **Source**: user (Step 1c `AskUserQuestion`; no response within 60s, proceeded with the recommended option per established `/design` timeout convention)

## Decision 2: Preventive lint
- **Question**: Should the plan also add a static lint flagging bare `$<digit>` awk field/record references inside `SKILL.md` code fences?
- **Resolution**: Yes, include the lint in this plan.
- **Source**: user (Step 1c `AskUserQuestion`; no response within 60s, proceeded with the recommended option)

## Decision 3: Non-goal — shell positional-parameter dispatch
- **Question**: Does the fix extend to `skills/deps/SKILL.md`'s `case "$1" in` argument dispatch (lines 35-47) or other bash positional-parameter (`$1`/`$2`/`$#`) usage?
- **Resolution**: No. That is bash's own positional-parameter syntax, not an awk field reference, so it cannot move into a Python helper the same way. The issue itself flags this as a more severe, unresolved exposure. Out of scope for this plan.
- **Source**: codebase (issue root-cause analysis; consistent with the Decision 1 scope)

## Decision 4: Non-goal — `$0` bootstrap-recovery variant
- **Question**: Does the fix extend to the `$0`-based bootstrap-recovery awk idiom in `skills/implement/SKILL.md`, `skills/implement/references/bootstrap-recovery.md`, and `skills/implement/references/extracted-script-registry.md`?
- **Resolution**: No. That fallback exists to resolve `CLAUDE_PLUGIN_ROOT` itself, so routing it through a `python3 python/cli.py` helper would be circular — the helper needs `CLAUDE_PLUGIN_ROOT` to be invoked. The issue records no concrete fix for this case. Out of scope for this plan.
- **Source**: codebase (issue's own root-cause analysis)

## Decision 5: Path-convention hard constraint
- **Question**: What CLI-invocation convention must the new helper calls follow in each file?
- **Resolution**: `.claude/skills/release/SKILL.md` is dev-only and already invokes `python3 python/cli.py ...` relative to the repo root (no `CLAUDE_PLUGIN_ROOT`); `skills/pause/SKILL.md` and `skills/deps/SKILL.md` are public skills and must invoke `${CLAUDE_PLUGIN_ROOT}/python/cli.py` per `.claude/rules/skill-runtime-root-paths.md`. New call sites preserve each file's existing convention.
- **Source**: codebase

## Decision 6: Preserve duplicate-key resolution semantics
- **Question**: Must converted call sites preserve each site's original first-match-wins vs. last-match-wins behavior?
- **Resolution**: Yes. The release/SKILL.md awk sites use `exit` (first match wins); pause/SKILL.md sites pipe through `tail -1` (last match wins); deps/SKILL.md sites take whatever awk prints from single-line envelopes (order does not matter there in practice). The replacement helper must preserve the same effective behavior at each site.
- **Source**: codebase
