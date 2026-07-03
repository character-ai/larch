# Discussion Round 1 — resolved decisions

All decisions below were resolved in the issue body ("Confirmed decisions (operator, 2026-07-03)") or by codebase inspection. No AskUserQuestion calls were needed.

## Decision 1: Deep-pass execution model
- **Question**: Does Stage 2 deep verification run tests or only inspect code?
- **Resolution**: Read-only code inspection at HEAD; no test execution.
- **Source**: user (issue confirmed decision 1)

## Decision 2: Ledger persistence
- **Question**: Is the verdict ledger committed to the repo or kept local?
- **Resolution**: Local cache only at `~/.cache/larch/analyze-bugs/<repo>/ledger.jsonl`; never committed.
- **Source**: user (issue confirmed decision 2)

## Decision 3: Deep model default
- **Question**: Which model runs Stage 2 deep verification by default?
- **Resolution**: Sonnet; overridable via `--deep-model sonnet|opus|fable`.
- **Source**: user (issue confirmed decision 3)

## Decision 4: Output mode
- **Question**: Does the skill file follow-up issues automatically?
- **Resolution**: Report-only by default. Offer to file ONE combined follow-up issue via /issue listing NOT_FIXED / INCOMPLETE / REGRESSED findings, gated on operator approval.
- **Source**: user (issue confirmed decision 4)

## Decision 5: Surface tier
- **Question**: Shipped skill or dev-only?
- **Resolution**: Dev-only: `.claude/skills/analyze-bugs/SKILL.md` with `$PWD/...` paths, plus dev-only agents `.claude/agents/bug-fix-triage.md` and `.claude/agents/bug-fix-verifier.md`.
- **Source**: user (issue work items 2-3)

## Decision 6: Runtime constraints
- **Question**: What are the hard implementation constraints?
- **Resolution**: `python/analyze_bugs.py` stdlib-only behind `python3 python/cli.py analyze-bugs ...` per AGENTS.md Python-first rule; regression coverage in a test module; skill frontmatter description carries a "Use when" trigger per S017.
- **Source**: user (issue work items 1, 3) + codebase (AGENTS.md conventions)

## Decision 7: Window semantics
- **Question**: Which issues enter the audit window?
- **Resolution**: Last N issues with `[BUG]` title prefix regardless of state; mechanical verdicts: OPEN becomes NOT_FIXED, closed not-planned becomes WONTFIX, closed completed with no traceable fix commit becomes NEEDS_DEEP.
- **Source**: user (issue Stage 0 spec + measured baseline)

7 decisions resolved.
