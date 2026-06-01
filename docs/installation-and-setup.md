# Installation and Setup

Larch is distributed as a [Claude Code plugin](https://code.claude.com/docs/en/plugin-marketplaces). Installation starts by registering the marketplace that hosts larch, then installing the plugin from that marketplace.

## Install from GitHub

### Latest stable release

#### Install
```bash
claude plugin marketplace add character-ai/larch --sparse .claude .claude-plugin .gemini .github agents docs hooks scripts skills tests
claude plugin install larch@larch-local
```
The first command registers larch's marketplace manifest (`.claude-plugin/marketplace.json`). The second command installs the `larch` plugin into your Claude Code user scope. Once installed, all larch skills (e.g., /implement) become available in every Claude Code session.  Note that both commands make changes to your `~/.claude/settings.json`.

#### Configure
Edit your `~/.claude/settings.json` and ensure that it has `permissions`/`allow` section (add it if not yet), and that it has the following 2 entries.  NOTE: make sure to replace `<your-user-name>`!

```JSON
  "permissions": {
      "allow": [
        "Bash(/Users/<your-user-name>/.claude/plugins/cache/larch-local/larch/*/scripts/*)",
        "Skill(larch:*)"
      ]
  }
```

#### Upgrade

To upgrade larch to the latest stable version, run the `/upgrade-larch` skill in any Claude Code session:

```
/upgrade-larch
```

After `/upgrade-larch` finishes, restart Claude Code only if it actually installed a new version. If it reports that you are already on the latest stable release, no restart is needed; install-stamp refresh and cache prune may still have run. A legacy full active install is slimmed on the next real upgrade path; reinstall once if you need that disk reduction immediately. The upgrade script prints an installed-version block when `claude plugin list` succeeds; treat it as best-effort confirmation.

`/upgrade-larch` is idempotent only when `gh` is installed and can resolve the latest stable release: if the currently installed version already matches that stable release, it skips reinstall but still refreshes the install stamp and prunes old cache directories. If `gh` is unavailable or cannot resolve stable releases, the script warns and upgrades unconditionally, skips stable-version verification, and skips pruning.

Any successful install writes `.larch-installed-at` when the installed version resolves safely; pruning still runs only after a verified stable install or on the already-latest path (`gh` unavailable still skips prune). On prune, the script retains both the verified or just-installed target and the currently-running cached version directory (`basename "$PLUGIN_ROOT"`). At prune entry, unstamped numeric cache directories are normally backfilled from directory mtime before ranking; directories may stay unstamped until a prune run or if backfill cannot run. It keeps the eight most-recently-installed cached versions by install-stamp order (stamped directories sort before unstamped). There are no session pins. If a cache-directory removal fails, extra directories can remain on disk and the script warns instead of claiming they were deleted.

`/upgrade-larch` installs via the same sparse checkout shown above. The sparse checkout excludes the committed `larch-logs/` run logs and the dev-only `mermaid-lint/` toolchain, so the install carries no run logs and triggers no `npm install`. A valid sparse checkout refreshes in place with `claude plugin marketplace update`; legacy full clones, missing clones, and stale sparse cones are repaired with a one-time `remove` + sparse re-add on the upgrade path. The already-latest path does not mutate the marketplace or reinstall the active plugin.

## Install ast-grep
1. Install the CLI (shell)
`brew install ast-grep`

2. Add the marketplace (Claude Code)
`/plugin marketplace add ast-grep/agent-skill`

3. Install the plugin (Claude Code)
`/plugin install ast-grep@ast-grep-marketplace`

4. Reload plugins (Claude Code)
`/reload-plugins`

## Install for local development (contributors)

If you are hacking on larch itself and want Claude Code to load the plugin directly from your working checkout (so `${CLAUDE_PLUGIN_ROOT}` resolves to the repo you are editing), launch Claude Code with `--plugin-dir`:

```bash
git clone https://github.com/character-ai/larch.git
cd larch
claude --plugin-dir .
```

Alternatively, add the working checkout as a local marketplace and install from it:

```bash
cd larch
claude plugin marketplace add .
claude plugin install larch@larch-local
```

### Plugin cache vs. working-tree version

When larch is installed via the plugin system, Claude Code caches the installed version under `~/.claude/plugins/cache/larch-local/larch/<version>/`. Skills and scripts run from this **cached copy**, not from your live working tree. This means:

- A bug fix committed to your working tree does not take effect until you reinstall or refresh the plugin from that checkout. `/larch:upgrade-larch` updates the latest stable GitHub install; a local checkout install (`claude --plugin-dir .` or `claude plugin marketplace add .`) needs a local reinstall/refresh instead. Until then, every `/implement` run uses the older cached version.
- Multiple concurrent clones (e.g., `larch1/`, `larch2/`) share the same plugin cache. Upgrading from one clone upgrades for all.

**Automatic detection**: when the installed version is behind your working-tree version, larch emits a warning at session setup time:

```
**⚠ larch: installed plugin version (X.Y.Z) is behind the working tree (A.B.C).
Reinstall or refresh the plugin from this checkout before the next run to pick up the latest fixes.
Continuing with the cached version.**
```

This warning fires once per `session-setup.sh` invocation from a larch dev clone when preflight is enabled. Typical entrypoints include `/implement`; `/review` skips preflight and does not emit the warning in its default flow. After reinstalling or refreshing the plugin cache, restart Claude Code to pick up the new version.

### Mermaid CLI (required when Markdown changes contain Mermaid fences)

Contributors editing any `.md` file in this repo trigger the
`lint-mermaid-fences` pre-commit hook. When staged Markdown contains
` ```mermaid ` fences, the hook runs `mmdc` against them to catch unsafe
content before it lands in tracking-issue summaries or PR bodies. Markdown
changes without Mermaid fences do not require the Mermaid CLI. If fences are
present and the CLI is not installed, the hook hard-fails (exit 2), so install
the local toolchain first:

```bash
cd larch
(cd mermaid-lint && npm ci)   # creates mermaid-lint/node_modules/ (gitignored) + binds the lockfile
```

This installs `@mermaid-js/mermaid-cli` (pinned in `mermaid-lint/package.json` /
`mermaid-lint/package-lock.json`) plus its Puppeteer/Chromium dependency under
`mermaid-lint/node_modules/.bin/mmdc`. The hook resolves `mmdc` from
`mermaid-lint/node_modules/.bin/` first, then falls back to a globally-installed
`mmdc` on `PATH`.

If you are intentionally working on a machine without a Node toolchain
and want to skip the hook for a single commit, set `SKIP=lint-mermaid-fences`
on the commit (or on `make lint-only` / `pre-commit run`). CI installs
the toolchain itself, so the hook still runs there even when locally
skipped.

- The subsections below document one concrete setup recipe per agent (API-key path). If you prefer the subscription-plan path, install the binary and follow its own web-login flow instead — the rest of larch's configuration (settings, model overrides) still applies.

### Claude
- Via web UI of your Claude org, create your own API key
- Add it to your env (e.g., in `.bashrc`: `export ANTHROPIC_API_KEY="<your-key>"` (replace `<your-key>`, of course))
- Add/edit the following in `~/.claude/settings.json` (set `ANTHROPIC_API_KEY` in your shell env, not in this file — see the `apiKeyHelper`-free guidance below):
```JSON
  "env": {
    "CLAUDE_CODE_EFFORT_LEVEL": "high"
  },
  "model": "claude-sonnet-4-6[1m]",
```
- Install claude code: `curl -fsSL https://claude.ai/install.sh | bash`
- Run `claude` and verify the above settings
- **Minimum `claude` CLI version**: a build that supports `--permission-mode bypassPermissions` is required. Loop drivers that spawn `claude -p` children carry this flag so an in-child tool-permission prompt cannot stall a non-interactive subprocess until the watchdog fires. Older `claude` binaries that do not recognize the flag fail-fast (subprocess returns non-zero). Verify with `claude --permission-mode bypassPermissions --version` if uncertain.
- **Remove `apiKeyHelper` from `~/.claude/settings.json`**: larch's Claude subprocesses (voters, reviewers, fixers that skills spawn) run `claude --print`, read `~/.claude/settings.json` directly, and do **not** inherit a top-level `--settings` override. A file-level `apiKeyHelper` (for example `"apiKeyHelper": "echo $ANTHROPIC_API_KEY"`) breaks that path: in subscription/OAuth mode (no `ANTHROPIC_API_KEY` in the shell env) the helper returns empty → `apiKeyHelper failed` → `401 Invalid bearer token`. A non-zero helper exit does **not** fall back to OAuth either. Keep the settings file free of `apiKeyHelper`; inject it only where you want API-key billing (the `*_api` aliases below).
- **Dual-auth aliases** (illustrative; personal git-fetch/stash wrappers are out of scope):

```bash
# Per-token / API-key billing — inject apiKeyHelper via --settings (forces the key in interactive)
alias claude_api='claude --settings='\''{"apiKeyHelper": "echo $ANTHROPIC_API_KEY"}'\'''
alias opus_api='claude --model "claude-opus-4-8[1m]" --effort high --settings='\''{"apiKeyHelper": "echo $ANTHROPIC_API_KEY"}'\'''

# Subscription / browser-login billing — unset the key so auth falls through to stored OAuth
alias claude_login='env -u ANTHROPIC_API_KEY claude'
alias opus_login='env -u ANTHROPIC_API_KEY claude --model "claude-opus-4-8[1m]" --effort high'
```

Subprocesses inherit the top-level session's environment, so billing tracks the top-level account: `*_api` → API token (`ANTHROPIC_API_KEY`, which `claude --print` uses directly); `*_login` → subscription OAuth (macOS Keychain). Credential precedence is `ANTHROPIC_API_KEY` (env) > `apiKeyHelper` > stored OAuth, and a configured `apiKeyHelper` never falls back to OAuth — which is why the settings file stays clean and `apiKeyHelper` lives only in the `*_api` aliases.

### Codex
- Via web UI of your Codex org, create your own API key
- Add it to your env (e.g., in `.bashrc`: `export OPENAI_API_KEY="<your-key>"` (replace `<your-key>`, of course))
- Add to `~/.codex/config.toml`:
`env_key = "OPENAI_API_KEY"`
- Install Codex: `npm install -g @openai/codex`
- Run `codex` and verify the above settings

### Cursor
- Via web UI of your Cursor org, create your own API key
- Add it to your env (e.g., in `.bashrc`: `export CURSOR_API_KEY="<your-key>"` (replace `<your-key>`, of course))
> **Do NOT edit `~/.cursor/cli-config.json` to set model or max-mode.** Cursor manages that file itself and overwrites it on each launch, so any model / `maxMode` change you make there is reverted and silently ignored by larch. For larch's own Cursor invocations, the model is **hard-coded to `composer-2.5`** (passed via `cursor agent --model composer-2.5` from `scripts/agent-model-args.sh`), and **max-mode is forced on** via the `/max-mode on. Prompt:` slash-command prefix prepended by `scripts/cursor-wrap-prompt.sh`. To override the default model, set `LARCH_CURSOR_MODEL` (or `CLAUDE_PLUGIN_OPTION_CURSOR_MODEL`) in your environment rather than touching the cli-config file.

#### macOS keychain interaction

When `CURSOR_API_KEY` is set in your environment, larch's launchers (`scripts/launch-review.sh --tool cursor`, `scripts/launch-cursor-implement.sh`, `scripts/run-negotiation-round.sh`, plus the runtime markdown templates that emit `cursor agent` invocations) pass `--api-key "$CURSOR_API_KEY"` explicitly to `cursor agent`, bypassing the macOS keychain entirely for that auth path. This is the recommended setup for larch.

When `CURSOR_API_KEY` is unset or empty on macOS, larch's shared Cursor launchers first pre-read the service that Cursor itself uses (`cursor-user` / `cursor-access-token`) and export the result as `CURSOR_API_KEY` for the child invocation. If that read succeeds, the Cursor child receives `--api-key` and does not perform its own keychain read. If the pre-read fails or returns empty, larch falls back to Cursor's default auth resolution, which may consult the keychain entry created by `cursor login`.

A stale or transiently-unhealthy `cursor-user` keychain entry can produce intermittent failures during parallel reviewer launches with errors like:

```
Password not found for account 'cursor-user'
Security process exited with code: 45
```

If you hit this, the simplest workaround is:

```sh
security delete-generic-password -a cursor-user 2>/dev/null
# then either:
export CURSOR_API_KEY="<your-key>"   # recommended for larch (env-only, deterministic)
# or:
cursor login                          # recreates the keychain entry interactively
```

On Darwin only, larch's launchers run a read-only pre-launch check: if `CURSOR_API_KEY` is empty AND no `cursor-user` / `cursor-access-token` keychain entry exists, the launcher exits early with an actionable message rather than letting `cursor agent` emit the cryptic `Security process exited with code: 45`. The check and pre-read are strictly read-only — they do NOT delete keychain entries or invoke `cursor` as a subprocess. On Linux/CI, the check and pre-read are no-ops (`CURSOR_API_KEY` is the only auth path).

For the at-rest secret-persistence tradeoff (the API key appears in `.meta` `CMD_JSON` sidecars under the session tmpdir, because the collector's empty-output retry path relies on faithful argv reconstruction), see `SECURITY.md`.

```bash
# or
```
- Authenticate with OAuth:
```bash
```
```JSON
{
  "auth": {
    "type": "oauth"
  },
  "model": {
  }
}
```
```JSON
{
  "trustedFolders": [
    "/Users/<your-user-name>/path/to/repo"
  ]
}
```
```bash
```

## What the plugin provides

| Component | Description |
|---|---|
| Skills | `/design`, `/implement`, `/review`, `/research`, `/issue`, `/set-up-forked-open-source-repo`, `/upgrade-larch`, `/alias`, `/im` |
| Agents | `code-reviewer` (unified archetype covering code quality, risk/integration, correctness, architecture, security) |
| PreToolUse hooks | `block-submodule-edit.sh` blocks `Edit`/`Write` on files inside any checked-out git submodule of the consuming project |
| SessionStart hook | `sessionstart-health.sh` — at session start/resume/clear/compact, probes `jq` and `git` on `PATH`; if either is missing, injects an advisory into session context so the issue is visible before the first `Edit`/`Write`. Non-blocking (always exits 0); silent when both tools are present |

### SIMPLE-tier `/design` cost

With the multi-round plan-review loop landed, `/design` (SIMPLE, the default) runs the full plan-review panel and up to `LARCH_DESIGN_ROUND_CAP`-bounded inner rounds with the plan-revision waterfall between rounds. Real-world runs therefore take roughly tens of minutes (inner-round count is operator-tunable via `LARCH_DESIGN_ROUND_CAP`; the Step 3 review-run counter caps Gate C re-entries separately at the tier-derived cap of `3` for SIMPLE). See [configuration-and-permissions.md](configuration-and-permissions.md) § Environment Variables for the env var contracts.

## `scripts/relevant-checks.sh` — required consumer contract

> **Important:** `/implement` and `/review` run `scripts/relevant-checks.sh` after code changes when the file exists. If your repo omits it, orchestrators observe `RELEVANT_CHECKS_SKIPPED=true` (exit 0) from `run-relevant-checks-captured.sh` — treat that as explicit observability that local checks did **not** run; it is not equivalent to a green `make lint` / CI result.

Each consuming repo should ship an executable `scripts/relevant-checks.sh` tailored to that repo's linters and tests. Larch's own repository includes a reference implementation at `scripts/relevant-checks.sh` plus `scripts/relevant-checks.md`.

**To adopt the contract in another repo:**

1. Add `scripts/relevant-checks.sh` (executable) that runs your repo's linters/tests.
2. Keep the documented exit-path matrix aligned with `scripts/relevant-checks.md`: success exits 0 after at least one validation phase, check failures return the underlying tool exit code, and zero validation coverage exits non-zero with an `ERROR:` line.

Human operators can run `bash scripts/relevant-checks.sh` directly; larch orchestrators always go through `scripts/run-relevant-checks-captured.sh` so stdout stays bounded.

## Clean-main entry contract for `/implement` and `/design`

`/implement` and standalone `/design` fail closed at entry unless one of two preconditions holds. The check runs in `preflight.sh` before any side effects — for `/implement`, before any tracking-issue side effects (no issue is created, no metadata summary is planted) and before any branch is created; for standalone `/design` (which does not create a tracking issue at entry), before any branch is created. An aborted entry leaves no remote state behind.

**(a) Default — clean `main`.** The skill asserts that the working tree is on `main`, has no uncommitted changes, fetches `origin/main`, and rebases local `main` onto it. A dirty tree, a non-`main` branch with no recognized prefix, or a fetch failure aborts with a normalized error.

**(b) Continuation opt-in — `<USER_PREFIX>/*` feature branch.** Running on a branch whose name starts with your configured `<USER_PREFIX>/` (e.g., `sergey-zhupanov/foo`) is the explicit signal that you want to continue from current state. The gate is bypassed; the skill keeps working on the current branch.

**(c) `--issue <N>` does not waive the gate.** Adopting an existing tracking issue with `--issue <N>` controls *identity* (which issue is updated and auto-closed) but does not relax the working-tree requirement. You still need either a clean `main` or a `<USER_PREFIX>/*` branch to start.

**(d) Failure modes and recovery.** When preflight fails, the orchestrator prints the raw `PREFLIGHT_ERROR=...` followed by a normalized message naming the skill that was invoked. From `/implement`:

> ⚠ /implement requires clean main to start. To continue, choose one of: (a) `git checkout main && git status` clean → re-run; (b) check out or create a `<USER_PREFIX>/*` feature branch and re-run (the branch naming convention is the explicit opt-in to continue from current state); (c) commit or stash uncommitted changes on `main` first.

Standalone `/design` prints the same message with `/design` substituted for `/implement`. The three remediation paths (clean `main`, `<USER_PREFIX>/*` continuation, commit-or-stash) cover dirty trees, wrong-branch starts, and transient fetch failures.

## Fork CI dry-runs

`/implement --forked` is for open-source fork workflows where `origin` is the contributor fork and `upstream` is the canonical repository. Configure remotes before running:

```bash
git remote -v
git remote add upstream git@github.com:OWNER/UPSTREAM.git
```

## Prerequisites

Larch skills have different dependency requirements depending on which features you use.

### Installation dependencies

- **Claude Code** — required. Install via [setup instructions](https://code.claude.com/docs/en/setup).

### Workflow automation (`/implement --merge`, `/review`)

These tools are required for the full design → implement → PR → merge workflow:

- **git** — version control (used by all skills)
- **gh** — [GitHub CLI](https://cli.github.com/), authenticated with repo write access (`gh auth login`). Required for PR creation, CI monitoring, and merge automation.
- **jq** — [JSON processor](https://jqlang.github.io/jq/). Used by validation scripts, session setup, and the shipped hooks (`hook-post-bump-version.sh` PostToolUse on `Skill` + `hook-stop-fail-close.sh` Stop). When `jq` is missing, both hooks short-circuit at their `command -v jq` probe, and resume-hygiene / fail-close behaviors that depend on JSON parsing are silently disabled. The SessionStart hook (see below) injects an advisory when `jq` is absent so the gap is visible at session start.

### Optional integrations

These tools enhance the workflow but are not required. Fallback behavior varies by tool — see each bullet below.

- **Codex** — [OpenAI Codex CLI](https://github.com/openai/codex). Participates as an external reviewer and voter alongside Claude subagents. When unavailable, Codex-specific reviewer slots are skipped and voting may collapse per threshold rules.
- **Cursor** — [Cursor AI editor](https://cursor.com/). Participates as an external reviewer and voter. When unavailable, Cursor-specific reviewer slots are skipped and voting may collapse per threshold rules.

### Contributor development

- **pre-commit** — `pip install pre-commit` for local linting (`make setup` installs git hooks)
- **Python 3.12+** — required by pre-commit
