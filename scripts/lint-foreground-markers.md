# scripts/lint-foreground-markers.sh — contract

`scripts/lint-foreground-markers.sh` is a repo-wide static lint over **tracked** Markdown under the skill and rules authoring surface: `skills/*/SKILL.md`, `skills/*/references/*.md`, `skills/shared/*.md`, `.claude/skills/*/SKILL.md`, and `.claude/rules/*.md` (enumerated via `git ls-files` when `--root` is a git worktree; otherwise a deterministic `find` walk mirroring those globs).

Inside **fenced** `bash` / `sh` / `shell` blocks (opening fence may be indented), any **invocation-shaped** line that references one of the denylisted `*.sh` basenames must be preceded in the Markdown stream by the canonical banner (optionally prefixed once with a Markdown blockquote using the usual `>` line prefix):

`**⚠ Foreground required — do NOT set \`run_in_background: true\`.**`

and **each** invocation-shaped anchor must have a matching comment in the **previous five non-closing fence lines** of that fence body (look-back is per anchor line; one comment can cover multiple anchors only when each anchor lies within five lines below that comment):

`# Foreground required: see BASH_AUTHORING.md §4`

Family B background fences use the background banner/comment pair instead and
must include both halves of the pair: `run_in_background: true` and a
`breadcrumb-monitor.sh --stream ...` consumer. Top-level Family B writers
(`ship-pr.sh`, `run-step5-review.sh`, `run-step2-dispatch.sh`,
`collect-agent-results.sh`, and `dispatch-plan-voters.sh`) must also allocate
and export `LARCH_PAIRED_PID_FILE` with `mktemp` under a session
`breadcrumbs/` directory and pass `--paired-pid-file` to the monitor. Missing
tokens emit `missing LARCH_PAIRED_PID_FILE allocation for <basename>` or
`missing --paired-pid-file monitor argument for <basename>`. The foreground-only
`step-7a.sh` carve-out and nested-only children (`ci-wait.sh`,
`review-and-fix.sh`, `step2-implement.sh`, `dispatch-with-waterfall.sh`) do not
need the new paired-PID tokens.

The script never evaluates fence bodies. Lines inside an in-fence shell heredoc opened by a `<<` / `<<-` delimiter (quoted `<<'WORD'`, `<<"WORD"`, or a simple trailing `WORD` token on the opener line per the implementation) are skipped for anchor detection until the closing delimiter line is seen, so tutorial text that quotes denylist-shaped paths inside heredocs does not false-positive. Exit codes: `0` clean, `1` violations (stderr: `<path>:<line>: missing banner|missing comment for <basename>`), `2` CLI/`--root` errors.

Non–git-worktree enumeration uses a `find` subshell piped through `sort`; each `find` is suffixed with `|| true` so missing `skills/`, `.claude/skills/`, or `.claude/rules/` trees do not trip `set -o pipefail` (regression harnesses use bare `mktemp` roots).

Primary callers: `make lint-foreground` (alias of `lint-foreground-markers`), `make lint-foreground-markers`, local `make lint` (between `lint-bash32` and `lint-only`), the `lint-foreground-markers` pre-commit hook (`pass_filenames: false`, `always_run: true`), and `scripts/test-lint-foreground-markers.sh`.

Normative authoring rules live in `BASH_AUTHORING.md` section **Foreground markers for blocking Family B script calls**. Edit this linter in sync with that section, `docs/linting.md`, `Makefile`, `.pre-commit-config.yaml`, `agent-lint.toml` (Makefile-only exclusions for this script + harness + sibling `*.md` contracts), and `scripts/test-lint-foreground-markers.md`.
