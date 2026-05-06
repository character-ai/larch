# analyze.py

Purpose: generate the `/analyze-issues` backlog-and-process report from a local GitHub issue JSON dump.

Primary callers: `run-analysis.sh`.

Invariants: use only Python stdlib, cap issue bodies to the first 5 KB before analysis, keep output deterministic, assign every issue exactly one category, preserve `[OOS]` and duplicate-title evidence, and keep reviewer attribution regexes ordered so `codex` cannot be counted as `code`.

`load_issues` policy: emit a stderr `WARN load_issues: skipping non-dict element at index <i>: <repr>` line for every list element that is not a dict, and emit `WARN load_issues: skipping issue with missing number at index <i>: <repr>` or `WARN load_issues: skipping issue with non-numeric number at index <i>: <repr>` for every dict whose `number` field is missing, null, bool, non-positive, non-ASCII-digit string, or otherwise non-numeric. All skipped rows share one skip counter, and `load_issues` exits with `ERROR=load_issues skipped … non-dict or malformed-number elements` when the skip ratio exceeds 5% of the input list. The CLI flag `--lenient` suppresses the threshold abort but does NOT silence the per-element stderr warnings; pass it through `run-analysis.sh --lenient` for callers that genuinely tolerate corrupted dumps.

Every issue returned by `load_issues` has a positive integer `number`. Analysis functions including `categorize`, `growth_chart`, `wasteful_findings`, and `reviewer_effectiveness` expect issues produced by `load_issues` or manually constructed with that same shape; raw dicts that bypass the loader are out of contract and may raise `KeyError`.

`default_category` keyword matching uses precompiled per-category word-boundary regexes (`CATEGORY_PATTERNS`). Two compilation modes:

- **Whole-word** (default — `re.escape(KW) + r"\b"`): every keyword in `CATEGORY_RULES` not listed in `_STEM_KEYWORDS`. Short tokens like `fix` / `add` / `new` use this mode so they cannot alias inside `fixture` / `prefix` / `affix`. Documentation drift relies on this mode with explicit enumeration of inflectional forms (`doc`, `docs`, `documentation`, `documented`, `documenting`, `instruction`, `instructions`) — `doc` is intentionally NOT a stem to avoid matching `Docker` / `doctrine` / `documentary`.
- **Prefix-stem** (`re.escape(stem) + r"\w*"`, where `stem` trims a trailing `e`/`y` from the keyword): the `_STEM_KEYWORDS` frozenset (`determin`, `validate`, `sanitize`, `simplify`, `permission`, `secret`, `feature`, `scaffold`, `failure`, `regression`, `assert`, `crash`). These accept inflectional forms — `determinism`, `validation`, `sanitization`, `simplification`, `failures`, `crashes`, `assertions`, etc. — so the stem rewrite preserves the original substring behavior for those keywords.

Makefile wiring: none; this is a dev-only local skill helper.

Test harness: `python3 -c "import ast; ast.parse(open('.claude/skills/analyze-issues/scripts/analyze.py').read())"`.

Edit in sync: update this contract, `run-analysis.sh`, and `SKILL.md` whenever CLI flags, output sections, category rules, or reviewer attribution semantics change.
