# Installation and Setup

> **New to larch?** Set up your repository first. [Preparing Your Repository](preparing-your-repo.md) covers the instruction files, guardrails, and relevant-checks contract that larch, and coding agents generally, rely on.

Larch is distributed as a [Claude Code plugin](https://code.claude.com/docs/en/plugin-marketplaces). Installation starts by registering the marketplace that hosts larch, then installing the plugin from that marketplace.

## Install from GitHub

### Latest stable release

Maintainers publish GitHub Releases on a release cadence (not on every merge to `main`). `/upgrade-larch` tracks the Latest stable release.

#### Install
```bash
claude plugin marketplace add character-ai/larch --sparse .claude-plugin agents docs hooks python scripts skills
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

After `/upgrade-larch` finishes, restart Claude Code if it installed a new version or repaired the marketplace sparse checkout. If it reports that you are already on the latest stable release and says `No upgrade needed.`, no restart is needed; install-stamp refresh, cache prune, and dev/test cache cleanup may still have run. Cleanup removes larch development and test infrastructure from the installed cache on both reinstall and already-latest paths, including nested test harnesses and dropped top-level directories such as `.claude/`, `.github/`, `.gemini/`, and `tests/`. First-time sparse installs are cleaned after the first `/upgrade-larch`, not by SessionStart. If it reports `LARCH_CONE_RECONCILED=true`, `LARCH_RESTART_REQUIRED=true`, or says the sparse checkout is out of date, the plugin was reinstalled and Claude Code needs a restart. The upgrade script prints an installed-version block when `claude plugin list` succeeds; treat it as best-effort confirmation.

Default `/implement` Step 8+ uses the Python ship driver from the cached plugin (`python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" ship pr`) on the first `/implement` after the upgraded plugin is loaded. Ensure `python3` is Python 3.11 or newer before starting the session. See [Plugin cache vs. working-tree version](#plugin-cache-vs-working-tree-version) for why restart timing controls which cached `SKILL.md` is active.

`/upgrade-larch` is idempotent only when `gh` is installed, can resolve the latest stable release, and the marketplace sparse cone already matches larch's allowlist: if the currently installed version already matches that stable release and the cone matches, it skips reinstall but still refreshes the install stamp, prunes old cache directories, and cleans dev/test cache files. If the version matches but the sparse cone drifted (for example, a new top-level runtime directory was added to larch), `/upgrade-larch` repairs the cone with a sparse re-add and reinstalls the same version. If `gh` is unavailable or cannot resolve stable releases, the script warns and upgrades unconditionally, skips stable-version verification, and skips pruning.

The already-latest path and verified stable install path write `.larch-installed-at` when the installed version resolves safely; pruning still runs only after a verified stable install or on the already-latest path (`gh` unavailable still skips prune). On prune, the script retains both the verified or just-installed target and the currently-running cached version directory (`basename "$PLUGIN_ROOT"`). At prune entry, unstamped numeric cache directories are normally backfilled from directory mtime before ranking; directories may stay unstamped until a prune run or if backfill cannot run. It keeps the eight most-recently-installed cached versions by install-stamp order (stamped directories sort before unstamped). There are no session pins. If a cache-directory removal fails, extra directories can remain on disk and the script warns instead of claiming they were deleted.

`/upgrade-larch` installs via the same sparse checkout shown above. The sparse checkout excludes dev-only top-level directories removed from `LARCH_SPARSE_DIRS` (`.claude/`, `.github/`, `.gemini/`, and `tests/`), plus the committed `larch-logs/` run logs and the dev-only `mermaid-lint/` toolchain. Fresh sparse installs omit those top-level directories. `/upgrade-larch` cleanup removes leftover dev/test infrastructure from older cones and root files that cone mode still includes, so the install carries no run logs, no local test harnesses, and no `npm install` trigger. A valid sparse checkout refreshes in place with `claude plugin marketplace update`; legacy full clones, missing clones, and stale sparse cones are repaired with a one-time `remove` + sparse re-add on the upgrade path, including the already-latest path when the cone drifted. SessionStart also warns when it can see a drifted `larch-local` marketplace cone and points you at `/upgrade-larch`; the warning is read-only and best-effort.

When maintainers cut a release that changes the sparse allowlist, `/release` runs the working-tree upgrade script against the resolved active installed/cache root so the new allowlist can apply in the same release cycle. Release prefers an existing active `CLAUDE_PLUGIN_ROOT` cache root over newer installed metadata for stamp/prune context, and it requires a Claude Code restart after either a version install or a same-version cone reconcile.

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

- A bug fix committed to your working tree does not take effect until you reinstall or refresh the plugin from that checkout. `/larch:upgrade-larch` updates the latest stable GitHub install; a local checkout install (`claude --plugin-dir .` or `claude plugin marketplace add .`) needs a local reinstall/refresh instead. Until then, every `/implement` run uses the older cached version, including ship-driver fixes for Step 8+.
- Multiple concurrent clones (e.g., `larch1/`, `larch2/`) share the same plugin cache. Upgrading from one clone upgrades for all.

**Automatic detection**: when the installed version is behind your working-tree version, larch emits a warning at session setup time:

```
**⚠ larch: installed plugin version (X.Y.Z) is behind the working tree (A.B.C).
Reinstall or refresh the plugin from this checkout before the next run to pick up the latest fixes.
Continuing with the cached version.**
```

This warning fires once per `session-setup.sh` invocation from a larch dev clone when preflight is enabled. Typical entrypoints include `/implement`; `/review` skips preflight and does not emit the warning in its default flow. After reinstalling or refreshing the plugin cache, restart Claude Code to pick up the new version.

### /report-tokens prerequisites

`/report-tokens` runs through the stdlib-only Python entrypoint under `python/` and shares the repository Python floor: Python 3.11 or newer. `gh` is required when the command needs to resolve the repository slug or post the report issue; pass `--no-issue` or set `LARCH_REPORT_TOKENS_NO_ISSUE=1` to run text analysis without posting. Plotting uses optional matplotlib in a subprocess and gracefully skips PNG generation when matplotlib is unavailable; pass `--no-plot` or set `LARCH_REPORT_TOKENS_NO_PLOT=1` to skip it explicitly. Rate override environment variables are documented in `docs/configuration-and-permissions.md`.

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

- The subsections below document per-agent setup, including both API-key and subscription billing for Claude (see dual-auth aliases and `apiKeyHelper`-free guidance). For Codex and Cursor, the steps focus on the API-key path; use each tool's web-login flow for subscription billing where applicable. Larch settings and model overrides apply regardless of billing mode.

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
- Via web UI of your Codex org, create your own API key.
- Add it to your env (e.g., in `.bashrc`: `export OPENAI_API_KEY="<your-key>"`; replace `<your-key>`, of course).
- Install Codex: `npm install -g @openai/codex`.
- Larch's covered Codex launch, probe, and review-fix surfaces prefer a non-whitespace `OPENAI_API_KEY` automatically via per-invocation `-c` overrides. Only the env var name is passed; the key value stays in the environment.
- When `OPENAI_API_KEY` is unset, empty, or whitespace-only, those surfaces fall back to `codex login` / `~/.codex/auth.json`.
- Do not keep the old top-level `env_key = "OPENAI_API_KEY"` setup advice as your Codex path; larch strips that legacy line from copied temp configs on login fallback.

### Cursor
- Via web UI of your Cursor org, create your own API key
- Add it to your env (e.g., in `.bashrc`: `export CURSOR_API_KEY="<your-key>"` (replace `<your-key>`, of course))
> **Do NOT edit `~/.cursor/cli-config.json` to set model or max-mode.** Cursor manages that file itself and overwrites it on each launch, so any model / `maxMode` change you make there is reverted and silently ignored by larch. For larch's own Cursor invocations, the model is **hard-coded to `composer-2.5`** (passed via `cursor agent --model composer-2.5` from `python3 python/cli.py agent model-args`), and **max-mode is forced on** via the `/max-mode on. Prompt:` slash-command prefix prepended by `python3 python/cli.py agent cursor-wrap-prompt`. To override the default model, set `LARCH_CURSOR_MODEL` (or `CLAUDE_PLUGIN_OPTION_CURSOR_MODEL`) in your environment rather than touching the cli-config file.

> **GUI popup suppression (issue #5797).** larch exports `NO_OPEN_BROWSER=1` into every Cursor child's environment so `cursor agent` does not open the Cursor.app "Composer" GUI window (via a `cursor://` deeplink) during headless lanes. Auth is unaffected — larch authenticates via `CURSOR_API_KEY` / keychain, never interactive login.

#### macOS keychain interaction

When `CURSOR_API_KEY` is set in your environment, larch's launchers (`python/cli.py agent launch-review --tool cursor`, `python/cli.py agent launch-cursor-implement`, `python/cli.py agent run-negotiation-round`, plus the runtime markdown templates that emit `cursor agent` invocations) export the normalized `CURSOR_API_KEY` into the environment the `cursor agent` child inherits and pass **no** `--api-key` argv element (issue #3375 — keeping the secret off the command line, `.meta` logs, and `ps`). `cursor agent` reads the key from the `CURSOR_API_KEY` environment variable, bypassing the macOS keychain entirely for that auth path. This is the recommended setup for larch.

When `CURSOR_API_KEY` is unset or empty on macOS, larch's shared Cursor launchers first pre-read the service that Cursor itself uses (`cursor-user` / `cursor-access-token`) and export the result as `CURSOR_API_KEY` for the child invocation. If that read succeeds, the Cursor child inherits `CURSOR_API_KEY` from the environment and does not perform its own keychain read. If the pre-read fails or returns empty, larch falls back to Cursor's default auth resolution, which may consult the keychain entry created by `cursor login`.

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

### `/design` cost

`/design` runs the full plan-review panel once per Step 3 entry; accepted findings auto-apply at Gate B by default, while `--per-round-approval` restores the explicit Gate B operator choices. `--skip-approve`/`-s` auto-approves the Step 1d.7 outline and Gate C final plan without prompting (no other prompts are skipped). Real-world runs can still take tens of minutes because the external panel and voting run before Gate B; the Step 3 review-run counter caps Gate C re-entries separately at the cap of `5`. See [configuration-and-permissions.md](configuration-and-permissions.md) § Environment Variables for the remaining env var contracts.

## Clean-main entry contract for `/implement` and `/design`

`/implement` and standalone `/design` fail closed at entry unless one of two preconditions holds. The check runs in `python/cli.py admission preflight` before any side effects — for `/implement`, before any tracking-issue side effects (no issue is created, no metadata summary is planted) and before any branch is created; for standalone `/design` (which does not create a tracking issue at entry), before any branch is created. An aborted entry leaves no remote state behind.

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
- **jq** — [JSON processor](https://jqlang.github.io/jq/). Used by validation scripts, session setup, and the shipped Stop hook (`hook-stop-fail-close.sh`). When `jq` is missing, JSON-dependent validation and fail-close behavior can be disabled. The SessionStart hook (see below) injects an advisory when `jq` is absent so the gap is visible at session start.
- **python3** — Python 3.11 or newer for the `/implement` Step 8+ ship driver (`python/cli.py ship pr`) and the `/report-tokens` CLI.

### Optional integrations

These tools enhance the workflow but are not required. Fallback behavior varies by tool — see each bullet below.

- **Codex** — [OpenAI Codex CLI](https://github.com/openai/codex). Participates as an external reviewer and voter alongside Claude subagents. When unavailable, Codex-specific reviewer slots are skipped and voting may collapse per threshold rules.
- **Cursor** — [Cursor AI editor](https://cursor.com/). Participates as an external reviewer and voter. When unavailable, Cursor-specific reviewer slots are skipped and voting may collapse per threshold rules.

### Contributor development

- **pre-commit** — `pip install pre-commit` for local linting (`make setup` installs git hooks)
- **Python 3.11+** — required by pre-commit
