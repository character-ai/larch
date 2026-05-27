# scripts/lint-foreground-markers.sh — contract

`scripts/lint-foreground-markers.sh` is a repo-wide static lint over **tracked** Markdown under the skill and rules authoring surface: `skills/*/SKILL.md`, `skills/*/references/*.md`, `skills/shared/*.md`, `.claude/skills/*/SKILL.md`, and `.claude/rules/*.md` (enumerated via `git ls-files` when `--root` is a git worktree; otherwise a deterministic `find` walk mirroring those globs).

Inside **fenced** `bash` / `sh` / `shell` blocks (opening fence may be indented), any **invocation-shaped** line that references one of the Family B denylisted `*.sh` basenames must be preceded in the Markdown stream by the canonical background banner (optionally prefixed once with a Markdown blockquote using the usual `>` line prefix):

`**⚠ Background required — must be paired with breadcrumb-monitor.sh.**`

and **each** invocation-shaped anchor must have a matching comment in the **previous five non-closing fence lines** of that fence body (look-back is per anchor line; one comment can cover multiple anchors only when each anchor lies within five lines below that comment):

`# Background pair required: see BASH_AUTHORING.md §4`

Family B background fences must include both halves of the pair:
`run_in_background: true` and a same-fence `breadcrumb-monitor.sh --stream ...`
consumer. Top-level Family B writers
(`ship-pr.sh`, `run-step5-review.sh`, `run-step2-dispatch.sh`,
`collect-agent-results.sh`, and `dispatch-plan-voters.sh`) must also allocate
and export `LARCH_PAIRED_PID_FILE` with `mktemp` under a session
`breadcrumbs/` directory, pass `--paired-pid-file` to the monitor, end the
writer command with shell `&`, capture `$!` in the next three non-blank lines,
and `wait` on that same identifier after the monitor invocation. Missing tokens
emit `missing LARCH_PAIRED_PID_FILE allocation for <basename>`, `missing
--paired-pid-file monitor argument for <basename>`, `missing shell ampersand`,
`missing PID capture`, `missing breadcrumb-monitor.sh`, `missing wait`, or an
identifier-mismatch diagnostic. The foreground-only
`step-7a.sh` carve-out and nested-only children (`ci-wait.sh`,
`review-and-fix.sh`, `step2-implement.sh`, `dispatch-with-waterfall.sh`) do not
need the paired-PID or writer-wait tokens.

Shell-script parent-unset rule: tracked shell scripts under `scripts/*.sh`,
`skills/*/scripts/*.sh`, `skills/shared/scripts/*.sh`, and `hooks/*.sh` are scanned for
nested-only Family B children that must not inherit a caller-owned
`LARCH_PAIRED_PID_FILE`. Today the enforced child list is
`dispatch-with-waterfall.sh`. A call is anchored either by a basename-shaped
literal invocation or by a variable-backed invocation where a simple assignment
previously resolved a variable to a path ending in the child basename, including
default-expansion forms such as
`DISPATCH_WATERFALL_SH="${EXTERNAL:-$PLUGIN_ROOT/scripts/dispatch-with-waterfall.sh}"`.
Within the prior five non-blank non-comment shell lines, the parent must contain
`unset LARCH_PAIRED_PID_FILE`; otherwise stderr reports
`missing parent-unset (unset LARCH_PAIRED_PID_FILE) before nested
dispatch-with-waterfall.sh`. Exclusions: `larch-logs/**`, `*/test-*.sh`, the
child script itself, diagnostic strings such as `--tool
"dispatch-with-waterfall.sh"`, and variable definitions that do not invoke the
child. A specific invocation line can be suppressed with
`# lint-foreground-markers: ok <reason>`.

Post-fence contradiction rule: after a fenced shell block that contains both
`run_in_background: true` and `breadcrumb-monitor.sh`, the next ten Markdown
lines must not say the foreground-only phrase `Do NOT set run_in_background:
true`. This catches prose that contradicts the required background+monitor pair.
The same inline suppression syntax, `# lint-foreground-markers: ok <reason>`, is
accepted on the contradictory prose line.

Top-level Family B writer wait rule: tracked shell scripts in the same shell
surface that contain `breadcrumb-monitor.sh` are also scanned for top-level
writer invocations and must use the same shell `&` + PID capture + post-monitor
`wait` shape. This keeps reusable shell wrappers aligned with the Markdown
fence contract.

The script never evaluates fence bodies. Lines inside an in-fence shell heredoc opened by a `<<` / `<<-` delimiter (quoted `<<'WORD'`, `<<"WORD"`, or a simple trailing `WORD` token on the opener line per the implementation) are skipped for anchor detection until the closing delimiter line is seen, so tutorial text that quotes denylist-shaped paths inside heredocs does not false-positive. Exit codes: `0` clean, `1` violations (stderr: `<path>:<line>: missing banner|missing comment for <basename>`), `2` CLI/`--root` errors.

Non–git-worktree enumeration uses a `find` subshell piped through `sort`; each `find` is suffixed with `|| true` so missing `skills/`, `.claude/skills/`, or `.claude/rules/` trees do not trip `set -o pipefail` (regression harnesses use bare `mktemp` roots).

Primary callers: `make lint-foreground` (alias of `lint-foreground-markers`), `make lint-foreground-markers`, local `make lint` (between `lint-bash32` and `lint-only`), the `lint-foreground-markers` pre-commit hook (`pass_filenames: false`, `always_run: true`), and `scripts/test-lint-foreground-markers.sh`.

Normative authoring rules live in `BASH_AUTHORING.md` section **Background+propagate markers for blocking Family B script calls**. Edit this linter in sync with that section, `docs/linting.md`, `Makefile`, `.pre-commit-config.yaml`, `agent-lint.toml` (Makefile-only exclusions for this script + harness + sibling `*.md` contracts), and `scripts/test-lint-foreground-markers.md`.
