# run-analysis.sh

Purpose: top-level coordinator for the project-local `/analyze-issues` skill.

Primary callers: `.claude/skills/analyze-issues/SKILL.md` invokes this script through the Bash tool.

Invariants: parse only the documented flags, detect the current GitHub repo, write the raw issue dump to `${TMPDIR:-/tmp}/<sanitized-repo>-issues.json` where the slug converts `/` to `-` and keeps only alnum, `-`, and `_`, use `umask 077` plus `fetch-issues.sh`'s atomic temp+mv write for user-private dumps, and delegate report generation to `analyze.py`. Keep shell scripts on `set -euo pipefail`.

Documented flags: `--limit`, `--span-days`, `--top-K`/`--top-k`, `--categories[=]`, `--lenient`. The `--lenient` flag is forwarded verbatim into `ANALYZE_ARGS` and disables `analyze.py`'s `>5% non-dict or malformed-number abort` in `load_issues`; per-element stderr `WARN` lines are unaffected.

Makefile wiring: none; this is a dev-only local skill helper.

Test harness: `bash -n .claude/skills/analyze-issues/scripts/*.sh`.

Edit in sync: update this contract and `SKILL.md` whenever flags, output paths, or helper responsibilities change.
