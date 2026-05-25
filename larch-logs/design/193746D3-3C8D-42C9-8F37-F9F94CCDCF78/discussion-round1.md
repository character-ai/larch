## Decision 1: Brainstorm kind (operational meaning)
- **Question**: What does "brainstorm session" mean operationally for /design?
- **Resolution**: Multi-agent ideation panel — Codex/Cursor/Claude agents independently propose feature-level interpretations and alternatives (NOT architectural sketches; that is Step 2a). Main agent synthesizes and engages the user.
- **Source**: user

## Decision 2: Brainstorm position in the flow
- **Question**: Where in the /design flow does --brainstorm fire?
- **Resolution**: AFTER all clarifying-question steps (Step 1c clarifying + Step 1d Round 1 discussion) but BEFORE any design proposals (Step 2a sketches). Concretely: a new step inserted between Step 1d's terminal point and Step 1e Gate A — so brainstorm output is part of the context Gate A's "Ready for review" / "Discuss more" approval considers.
- **Source**: user

## Decision 3: Brainstorm output artifact
- **Question**: What artifact(s) does the brainstorm produce, and what reads them?
- **Resolution**: Writes `$DESIGN_TMPDIR/brainstorm.md`. Downstream steps (Step 2a sketches, Step 2b plan, Step 2a.5 dialectic, Step 3 plan review) read it as additional context, similar to how Step 2b reads `approach-synthesis.txt` and `discussion-round1.md`. The GitHub issue body is NOT mutated by brainstorm.
- **Source**: user

## Decision 4: Tier flag compatibility (general)
- **Question**: How does --brainstorm interact with tier flags (--trivial/--simple/--hard) and --partition?
- **Resolution**: --brainstorm is an additive modifier independent of tier. `--brainstorm --simple` and `--brainstorm --hard` both valid. `--brainstorm` alone is valid (combines with the standard tier-gate AskUserQuestion). `--brainstorm --partition` is allowed.
- **Source**: user

## Decision 5: --brainstorm + --trivial collision
- **Question**: When `--brainstorm --trivial` are passed together, what should Pre-Step-0 do?
- **Resolution**: Interactive AskUserQuestion with options `Upgrade to --simple` / `Cancel`. Pre-Step-0 normally rejects flag collisions non-interactively, but this case prompts because --trivial implies "skip ideation" and --brainstorm implies "ideate" — let the operator decide.
- **Source**: user

## Decision 6: Already-planned router behavior
- **Question**: Should --brainstorm be allowed when the issue body already contains a `larch:plan` block?
- **Resolution**: Always fire brainstorm when --brainstorm is on argv. The already-planned router's `replace via full flow` / `ad-hoc Q&A only` / `cancel` AskUserQuestion still runs, but brainstorm fires unconditionally on both `replace` and `ad-hoc Q&A` paths once the user chooses to continue. Only `cancel` skips brainstorm (because /design exits).
- **Source**: user

## Decision 7: Brainstorm panel shape
- **Question**: How many participants in the multi-agent ideation panel, and which mix?
- **Resolution**: 3 agents — 1 Codex + 1 Cursor + 1 Claude. Per-slot Claude fallback maintains the 3-agent count when an external is unavailable. When BOTH externals are unavailable, all 3 slots are filled by Claude subagents with distinct prompts.
- **Source**: user

## Decision 8: Backward-compat strictness
- **Question**: Is --brainstorm a hard-constraint preservation requirement?
- **Resolution**: Not strict byte-identity. Small ergonomic refactors of existing Step 1c/1d/1e prose are permitted if they make brainstorm integration cleaner. Existing tier flows must remain functionally equivalent (existing tests pass) when --brainstorm is NOT on argv, but minor prose / helper-script edits are acceptable.
- **Source**: user

## Decision 9: User interaction after brainstorm panel returns
- **Question**: After the 3-agent brainstorm panel returns, what happens with the output?
- **Resolution**: Main agent synthesizes, deduplicates, and sorts the 3 brainstorm outputs into an optimal ordering (per main agent's judgment), presents the synthesis to the user, and enters an **open free-form discussion** with the user. User can react, refine, add ideas, override the ordering, or signal completion in natural language. Main agent updates the synthesis based on user input. Discussion continues until user signals ready to proceed.
- **Source**: user

## Decision 10: Re-fire policy
- **Question**: Is brainstorm one-shot per /design invocation, or re-runnable?
- **Resolution**: One-shot. Sentinel (e.g., `$DESIGN_TMPDIR/.brainstorm-done` or equivalent guard) marks completion. Gate A's "Discuss more" branch re-enters Step 1c/1d only — brainstorm does NOT re-fire. Gate B and Gate C also do not re-run brainstorm. brainstorm.md is written exactly once per /design invocation.
- **Source**: user

## Decision 11: Externals-unavailable failure mode
- **Question**: If both external tools (Codex AND Cursor) are unavailable, what does the brainstorm panel do?
- **Resolution**: All-Claude fallback. Three Claude subagents with distinct prompts fill the 3 slots, preserving the 3-agent count. brainstorm.md is always produced (no skip path, no abort). Distinct prompts should give the 3 Claude subagents different framings to retain diversity (e.g., contrarian, pragmatic, explorer, or similar).
- **Source**: user

## Decision 12: --brainstorm exposure in public argv
- **Question**: Should --brainstorm be a public flag exposed in the SKILL.md argv-hint, or an internal/experimental flag?
- **Resolution**: Public flag, listed alongside --trivial/--simple/--hard/--partition/--no-dedup/--run-id in the SKILL.md compact table and references/flags.md.
- **Source**: codebase (precedent — all other user-facing /design behaviors are public flags)
