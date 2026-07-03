## Proposed Design Outline

### Goals
- Verify the last N closed [BUG] issues were actually fixed in main for ~$12-15 per full 200-bug run.
- Make periodic re-runs incremental (~$1-3) and interruption-safe via a local verdict ledger.
- Spend LLM tokens only where semantic judgment is needed: deterministic prefetch, Haiku screen, Sonnet deep pass.

### Non-goals
- No test execution during verification; deep pass is read-only code inspection at HEAD.
- No committed state: ledger lives under `~/.cache/larch/analyze-bugs/<repo>/` only.
- No automatic issue filing: report-only by default; one combined follow-up issue offered behind operator approval.

### Approach sketch
- Stage 0: new stdlib-only `python/analyze_bugs.py` behind `python3 python/cli.py analyze-bugs {prefetch,ledger,report}` (G-CLI-1 verb table): one `gh issue list` call, mechanical verdicts (OPEN, WONTFIX, NEEDS_DEEP), `git log --grep "Fixes #N"` fix mapping, capped per-bug bundle files with plan blocks stripped.
- Stage 1: dev-only agent `.claude/agents/bug-fix-triage.md` (model: haiku, no tools); ~10 inlined bundles per agent; strict JSONL verdicts; escalate on doubt.
- Stage 2: dev-only agent `.claude/agents/bug-fix-verifier.md` (model: sonnet, Read/Grep/Glob only); flagged bugs only, capped by `--deep-max`; read budget stated in prompt.
- Stage 3: Python merges ledger verdicts into a markdown report; skill offers ONE combined /issue follow-up, then prints an end-of-run token/cost summary line.
- Dev-only `.claude/skills/analyze-bugs/SKILL.md` orchestrates stages 0-3 with flags `-n`, `--deep-max`, `--deep-model`, `--refresh`, `--sample`; logic stays in Python, SKILL.md thin (G-Skill-2).

### Surfaces in scope
- `python/analyze_bugs.py` (new), `python/cli.py` verb registration, regression test module for analyze-bugs.
- `.claude/agents/bug-fix-triage.md` (new), `.claude/agents/bug-fix-verifier.md` (new).
- `.claude/skills/analyze-bugs/SKILL.md` (new, dev-only, `$PWD/...` paths, S017 "Use when" trigger).

### Open questions
- None.
