# analyze.py

Purpose: generate the `/analyze-issues` backlog-and-process report from a local GitHub issue JSON dump.

Primary callers: `run-analysis.sh`.

Invariants: use only Python stdlib, cap issue bodies to the first 5 KB before analysis, keep output deterministic, assign every issue exactly one category, preserve `[OOS]` and duplicate-title evidence, and keep reviewer attribution regexes ordered so `codex` cannot be counted as `code`.

`load_issues` policy: emit a stderr `WARN load_issues: skipping non-dict element at index <i>: <repr>` line for every list element that is not a dict, and exit with `ERROR=load_issues skipped …` when the skip ratio exceeds 5% of the input list. The CLI flag `--lenient` suppresses the threshold abort but does NOT silence the per-element stderr warnings; pass it through `run-analysis.sh --lenient` for callers that genuinely tolerate corrupted dumps.

`default_category` keyword matching uses precompiled per-category word-boundary regexes (`CATEGORY_PATTERNS`). Short keywords like `fix` / `add` / `new` match strictly (`\bKW\b`) so they cannot alias inside `fixture` / `prefix` / `affix`. Keywords listed in `_STEM_KEYWORDS` (e.g. `doc`, `determin`, `validate`, `sanitize`, `simplify`, `instruction`) match as prefixes (`\bKW\w*`) so inflectional forms — `documentation`, `determinism`, `validation`, `sanitization` — still classify into the intended category.

Makefile wiring: none; this is a dev-only local skill helper.

Test harness: `python3 -c "import ast; ast.parse(open('.claude/skills/analyze-issues/scripts/analyze.py').read())"`.

Edit in sync: update this contract, `run-analysis.sh`, and `SKILL.md` whenever CLI flags, output sections, category rules, or reviewer attribution semantics change.
