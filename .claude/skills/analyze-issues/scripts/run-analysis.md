# run-analysis.sh

Purpose: top-level coordinator for the project-local `/analyze-issues` skill.

Primary callers: `.claude/skills/analyze-issues/SKILL.md` invokes this script through the Bash tool.

Invariants: parse only the documented flags, detect the current GitHub repo, write the raw issue dump to `/tmp/<repo>-issues.json`, delegate fetching to `fetch-issues.sh`, and delegate report generation to `analyze.py`. Keep shell scripts on `set -euo pipefail`.

Makefile wiring: none; this is a dev-only local skill helper.

Test harness: `bash -n .claude/skills/analyze-issues/scripts/*.sh`.

Edit in sync: update this contract and `SKILL.md` whenever flags, output paths, or helper responsibilities change.
