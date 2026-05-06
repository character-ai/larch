# analyze.py

Purpose: generate the `/analyze-issues` backlog-and-process report from a local GitHub issue JSON dump.

Primary callers: `run-analysis.sh`.

Invariants: use only Python stdlib, cap issue bodies to the first 5 KB before analysis, keep output deterministic, assign every issue exactly one category, preserve `[OOS]` and duplicate-title evidence, and keep reviewer attribution regexes ordered so `codex` cannot be counted as `code`.

Makefile wiring: none; this is a dev-only local skill helper.

Test harness: `python3 -c "import ast; ast.parse(open('.claude/skills/analyze-issues/scripts/analyze.py').read())"`.

Edit in sync: update this contract, `run-analysis.sh`, and `SKILL.md` whenever CLI flags, output sections, category rules, or reviewer attribution semantics change.
