# scripts/lint-foreground-markers.sh — contract

`scripts/lint-foreground-markers.sh` is a repo-wide static lint over **tracked** Markdown under the skill and rules authoring surface: `skills/*/SKILL.md`, `skills/*/references/*.md`, `skills/shared/*.md`, `.claude/skills/*/SKILL.md`, and `.claude/rules/*.md` (enumerated via `git ls-files` when `--root` is a git worktree; otherwise a deterministic `find` walk mirroring those globs).

Inside **fenced** `bash` / `sh` / `shell` blocks (opening fence may be indented), any **invocation-shaped** line that references one of the denylisted `*.sh` basenames must be preceded in the Markdown stream by the canonical banner (optionally prefixed once with a Markdown blockquote using the usual `>` line prefix):

`**⚠ Foreground required — do NOT set \`run_in_background: true\`.**`

and the first invocation line for each anchor must have a matching comment in the **previous five non-closing fence lines** of that fence body:

`# Foreground required: see BASH_AUTHORING.md §4`

The script never evaluates fence bodies. Exit codes: `0` clean, `1` violations (stderr: `<path>:<line>: missing banner|missing comment for <basename>`), `2` CLI/`--root` errors.

Non–git-worktree enumeration uses a `find` subshell piped through `sort`; each `find` is suffixed with `|| true` so missing `skills/`, `.claude/skills/`, or `.claude/rules/` trees do not trip `set -o pipefail` (regression harnesses use bare `mktemp` roots).

Primary callers: `make lint-foreground-markers`, local `make lint` (between `lint-bash32` and `lint-only`), the `lint-foreground-markers` pre-commit hook (`pass_filenames: false`, `always_run: true`), and `scripts/test-lint-foreground-markers.sh`.

Normative authoring rules live in `BASH_AUTHORING.md` section **Foreground markers for blocking Family B script calls**. Edit this linter in sync with that section, `docs/linting.md`, `Makefile`, `.pre-commit-config.yaml`, `agent-lint.toml` (Makefile-only exclusions for this script + harness + sibling `*.md` contracts), and `scripts/test-lint-foreground-markers.md`.
