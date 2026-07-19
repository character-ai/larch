# Installation and Setup

> **New to larch?** Set up your repository first. [Preparing Your Repository](preparing-your-repo.md) covers the instruction files, guardrails, and relevant-checks contract that larch, and coding agents generally, rely on.

## Pre-requisites

### Authentication

Set up GitHub and Google credentials before starting larch. Installing `gh` is
separate from supplying the `GH_TOKEN` that larch uses for authenticated GitHub
requests.

#### GitHub

Larch requires a non-empty `GH_TOKEN` in its environment. It does not fall
back to `GITHUB_TOKEN`.

Choose one source for the token:

- **Reuse an existing GitHub CLI login.** Run this user setup command in your
  shell:

  ```bash
  export GH_TOKEN="$(gh auth token)"
  ```

  To provide the value for one Claude session only, run:

  ```bash
  GH_TOKEN="$(gh auth token)" claude
  ```

  Larch does not run `gh auth token` during normal service calls.

- **Create a personal access token (PAT).** Create it in GitHub
  [Settings > Developer settings > Personal access tokens](https://github.com/settings/tokens).
  Prefer a [fine-grained PAT](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#creating-a-fine-grained-personal-access-token)
  when its [repository permissions and API coverage](https://docs.github.com/en/rest/authentication/permissions-required-for-fine-grained-personal-access-tokens)
  are sufficient. Current larch operations can require a classic PAT when a
  required GitHub API operation is not available to a fine-grained PAT. Export
  the selected token as `GH_TOKEN`. Keep the value in a password manager or
  secret manager; never commit it to a repository or a `.env` file.

Verify the setup without printing the token:

```bash
test -n "$GH_TOKEN"
gh api user >/dev/null
```

The commands succeed silently when `GH_TOKEN` is non-empty and authenticates
to GitHub.

#### Google Application Default Credentials

Google-backed larch features require [Application Default Credentials (ADC)](https://cloud.google.com/docs/authentication/provide-credentials-adc).
Running `gcloud auth login` does not create ADC. For local development, create
them with:

```bash
gcloud auth application-default login
```

By default, ADC are stored at
`~/.config/gcloud/application_default_credentials.json` on macOS and Linux,
and at `%APPDATA%\gcloud\application_default_credentials.json` on Windows.
Set [`GOOGLE_APPLICATION_CREDENTIALS`](https://cloud.google.com/docs/authentication/provide-credentials-adc#local-dev)
to select another credential file. An attached service account or workload
identity can also provide ADC without a local file.

On macOS or Linux, verify a local ADC file is readable and verify ADC without
printing an access token:

```bash
test -r "$HOME/.config/gcloud/application_default_credentials.json"
gcloud auth application-default print-access-token >/dev/null
```

Both commands succeed silently when the expected local file is readable and
ADC can obtain an access token. The second command is an optional operator
setup check. Larch does not run `gcloud` during service calls.

The Rust credential boundary follows the standard ADC order: the file named by
`GOOGLE_APPLICATION_CREDENTIALS`, the well-known local ADC file, then the
attached-service-account metadata service. It requires each service adapter to
request explicit Google OAuth scopes. The official Google authentication layer
owns access-token caching and refresh. Larch does not copy ADC files, print or
persist access tokens, or provide a separate credential store.

External-account ADC must use Google's documented token and provider endpoints.
Executable subject-token sources, custom impersonation endpoints, custom cloud
universes, and `GCE_METADATA_HOST` overrides fail closed in production.

### Install
- **Anthropic / Claude Code**: `curl -fsSL https://claude.ai/install.sh | bash`
- **OpenAI / Codex**: `npm install -g @openai/codex`
- **Cursor / Cursor CLI** (larch uses it only as an agent, but the whole editor package needs to be installed)
- **git**: version control (used by all skills)
- **gh**: [GitHub CLI](https://cli.github.com/), authenticated with repo write access (`gh auth login`). The installed version must provide `gh release verify`, `gh attestation verify`, and immutable release metadata. Larch uses these commands for the first Rust binary install, PR creation, CI monitoring, and merge automation.
- **jq**: [JSON processor](https://jqlang.github.io/jq/).
- **python3**: Python 3.11 or newer

## Auth
All vendor agents work with either web login or API tokens.
### API Token Use
Set these environment variables in the shell where you run `claude`:
- `ANTHROPIC_API_KEY`
- `OPENAI_API_KEY`
- `CURSOR_API_KEY`
### Web login
Log in through the web for each of the three vendors.
### Helpful Aliases
To easily choose between API key use and web login use for Claude Code, I recommend defining aliases that choose the model and undefine the API key for web-based login.  e.g.:
```bash
# claude with sonnet 4.6 API Token
alias c='git fetch && git rebase && [ -z "$(git stash list)" ] && ENABLE_PROMPT_CACHING_1H=1 claude --model "claude-sonnet-4-6[1m]" --settings='\''{"apiKeyHelper": "echo $ANTHROPIC_API_KEY"}'\'' || echo "Stash is not empty"'

# claude with Opus 4.8 API Token
alias opus='git fetch && git rebase && [ -z "$(git stash list)" ] && claude --model "claude-opus-4-8" --effort high --settings='\''{"apiKeyHelper": "echo $ANTHROPIC_API_KEY"}'\'' || echo "Stash is not empty"'

# claude with Fable 5 API Token
alias fable='git fetch && git rebase && [ -z "$(git stash list)" ] && claude --model "claude-fable-5" --effort high --settings='\''{"apiKeyHelper": "echo $ANTHROPIC_API_KEY"}'\'' || echo "Stash is not empty"'

# claude with sonnet 5 web login
alias cm='git fetch && git rebase && [ -z "$(git stash list)" ] && env -u ANTHROPIC_API_KEY claude --model "claude-sonnet-5" || echo "Stash is not empty"'

# claude with Opus 4.8 API web login
alias opusm='git fetch && git rebase && [ -z "$(git stash list)" ] && env -u ANTHROPIC_API_KEY claude --model "claude-opus-4-8[1m]" --effort high || echo "Stash is not empty"'

# claude with Fable 5 API Token
alias fablem='git fetch && git rebase && [ -z "$(git stash list)" ] && env -u ANTHROPIC_API_KEY claude --model "claude-fable-5" --effort high || echo "Stash is not empty"'
```

## Larch Installation
Larch is distributed as a [Claude Code plugin](https://code.claude.com/docs/en/plugin-marketplaces).
### Install
```bash
claude plugin marketplace add https://raw.githubusercontent.com/character-ai/larch/main/.claude-plugin/marketplace.json
claude plugin install larch@larch-local
```

The remote marketplace fetches only the checked runtime projection under
`plugin/`. Both its fetch and the installed cache exclude Rust source,
repository linters, tests, release automation, and CI support files. Python
runtime modules remain because larch still executes them during the Rust
migration.

### Rust executable bootstrap

Every Rust-backed entrypoint must call
`${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh`. On first use, the shim installs the
executable that exactly matches the plugin version.
It downloads the versioned manifest, checksum file, and host archive from the
immutable `v<plugin-version>` release. It verifies release and asset
attestations, the strict manifest, SHA-256 digests, archive members, and the
staged executable's machine-readable identity before atomically installing
`${CLAUDE_PLUGIN_ROOT}/bin/larch`.

Claude Code supplies `CLAUDE_PLUGIN_ROOT` and `CLAUDE_PLUGIN_DATA` to plugin
commands. The latter holds the bounded first-use lock. A failed bootstrap keeps
an existing executable intact and prints retry guidance. Run the same command
again after fixing a missing tool, authentication problem, or interrupted
download.

Local `--plugin-dir` development never downloads into the checkout. Build and
select the executable explicitly:

```bash
cargo build --locked --release --package larch-cli
CLAUDE_PLUGIN_ROOT="$PWD" \
CLAUDE_PLUGIN_DATA="${TMPDIR:-/tmp}/larch-plugin-data" \
LARCH_BINARY="$PWD/target/release/larch" \
"$PWD/scripts/larch.sh" example echo "local build"
```

`LARCH_BINARY` must be an absolute, regular executable. Its version and target
self-check must match the active plugin and host.

### Configure Claude
Edit `~/.claude/settings.json` and add a `permissions`/`allow` section (if it does not have one yet) with this entry. NOTE: replace `<your-user-name>`!

```JSON
  "permissions": {
      "allow": [
        "Bash(/Users/<your-user-name>/.claude/plugins/cache/larch-local/larch/*/scripts/*)"
      ],
      "defaultMode": "bypassPermissions"
  }
```

`"defaultMode": "bypassPermissions"` skips permission prompts entirely, including for larch's skills. This is the simplest correct setup and the one larch's own dev checkout uses.

If you need stricter permissions instead (no `bypassPermissions`), drop that line and add explicit `Skill(...)` entries, one per larch skill you use. A bare `Skill(larch:*)` wildcard does **not** authorize plugin skills. See [Strict-permissions consumers](configuration-and-permissions.md#strict-permissions-consumers--skill-permission-entries) for the exact copy-paste list to add alongside the `Bash` entry above.

**Remove `apiKeyHelper` from `~/.claude/settings.json`**: larch's Claude subprocesses (voters, reviewers, fixers that skills spawn) run `claude --print`, read `~/.claude/settings.json` directly, and do **not** inherit a top-level `--settings` override. A file-level `apiKeyHelper` (for example `"apiKeyHelper": "echo $ANTHROPIC_API_KEY"`) breaks that path: in subscription/OAuth mode (no `ANTHROPIC_API_KEY` in the shell env) the helper returns empty, so `apiKeyHelper failed` leads to `401 Invalid bearer token`. A non-zero helper exit does **not** fall back to OAuth either. Keep the settings file free of `apiKeyHelper`; inject it only where you want API-key billing (the `*_api` aliases above).

### Configure Codex
- larch's Codex launch, probe, and review-fix surfaces prefer a non-whitespace `OPENAI_API_KEY`. When it is unset, empty, or whitespace-only, they fall back to `codex login` / `~/.codex/auth.json`.
- Do not keep the old top-level `env_key = "OPENAI_API_KEY"` setup advice as your Codex path. larch strips that legacy line from copied temp configs on login fallback.

### Configure Cursor
- **Do NOT edit `~/.cursor/cli-config.json` to set model or max-mode.** Cursor manages that file itself and overwrites it on each launch, so any model / `maxMode` change you make there is reverted and silently ignored by larch. For larch's own Cursor invocations, the default model remains **`composer-2.5`** (passed via `cursor agent --model composer-2.5` from `python3 python/cli.py agent model-args`), and reviewer-panel rows use the same default resolution unless a caller supplies an explicit per-slot `cursor_model` override. **Max-mode is forced on** via the `/max-mode on. Prompt:` slash-command prefix prepended by `python3 python/cli.py agent cursor-wrap-prompt`. To override the default model, set `LARCH_CURSOR_MODEL` (or `CLAUDE_PLUGIN_OPTION_CURSOR_MODEL`) in your environment rather than touching the cli-config file.

- **GUI popup suppression (issue #5797).** larch exports `NO_OPEN_BROWSER=1` into every Cursor child's environment so `cursor agent` does not open the Cursor.app "Composer" GUI window (via a `cursor://` deeplink) during headless lanes. Auth is unaffected: larch authenticates via `CURSOR_API_KEY` / keychain, never interactive login.

- **macOS keychain auth.** If `CURSOR_API_KEY` is unset and Cursor's keychain entry is missing or stale, larch fails with a specific, actionable error instead of Cursor's cryptic `Security process exited with code: 45`. See [macOS keychain interactions](macos-keychain-interactions.md) for the full mechanism and the fix.

### Validate
Run `/status` in a `claude` session. Expect a report like this:
```
larch v52.4.17
┌────────┬───────┐
│  Tool  │ State │
├────────┼───────┤
│ Codex  │ ok    │
├────────┼───────┤
│ Cursor │ ok    │
└────────┴───────┘
```

## Upgrade
Run the `/upgrade-larch` skill in your `claude` session. It verifies the exact
immutable stable release before refreshing plugin metadata. It then resolves
the new cache root from `claude plugin list --json`, installs that root's
release-matched executable, and verifies matching plugin and binary versions.
A failure leaves the prior cache root untouched and safe for the running
session. Restart `claude` after a successful install or marketplace repair.
The first upgrade from the old sparse GitHub marketplace registration replaces
that registration with the runtime-only remote source.

## Uninstalling

```bash
claude plugin uninstall larch@larch-local
```
