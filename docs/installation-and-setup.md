# Installation and Setup

## Pre-requisites
### Install
- **Anthropic / Claude Code**: `curl -fsSL https://claude.ai/install.sh | bash`
- **OpenAI / Codex**: `npm install -g @openai/codex`
- **Cursor / Cursor** (Larch uses it only as an agent, but the whole editor package needs to be installed)
- **git** — version control (used by all skills)
- **gh** — [GitHub CLI](https://cli.github.com/), authenticated with repo write access (`gh auth login`). Required for PR creation, CI monitoring, and merge automation.
- **jq** — [JSON processor](https://jqlang.github.io/jq/).
- **python3** — Python 3.11 or newer

## Auth
All vendor agents can be used either with web login or API tokens.
### API Token Use
For API token use, set up the following env vars containing API keys in the environment where you run `claude`:
- `ANTHROPIC_API_KEY`
- `OPENAI_API_KEY`
- `CURSOR_API_KEY`
### Web login
Perform web log in for each of the three vendors.
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
claude plugin marketplace add character-ai/larch --sparse .claude-plugin agents docs hooks python scripts skills
claude plugin install larch@larch-local
```
### Configure Claude
- Edit your `~/.claude/settings.json` and ensure that it has `permissions`/`allow` section (add it if not yet), and that it has the following 2 entries.  NOTE: make sure to replace `<your-user-name>`!

```JSON
  "permissions": {
      "allow": [
        "Bash(/Users/<your-user-name>/.claude/plugins/cache/larch-local/larch/*/scripts/*)",
        "Skill(larch:*)"
      ]
  }
```

- **Remove `apiKeyHelper` from `~/.claude/settings.json`**: larch's Claude subprocesses (voters, reviewers, fixers that skills spawn) run `claude --print`, read `~/.claude/settings.json` directly, and do **not** inherit a top-level `--settings` override. A file-level `apiKeyHelper` (for example `"apiKeyHelper": "echo $ANTHROPIC_API_KEY"`) breaks that path: in subscription/OAuth mode (no `ANTHROPIC_API_KEY` in the shell env) the helper returns empty → `apiKeyHelper failed` → `401 Invalid bearer token`. A non-zero helper exit does **not** fall back to OAuth either. Keep the settings file free of `apiKeyHelper`; inject it only where you want API-key billing (the `*_api` aliases below).

### Configure Codex
- When `OPENAI_API_KEY` is unset, empty, or whitespace-only, those surfaces fall back to `codex login` / `~/.codex/auth.json`.
- Do not keep the old top-level `env_key = "OPENAI_API_KEY"` setup advice as your Codex path; larch strips that legacy line from copied temp configs on login fallback.

### Configure Cursor
- **Do NOT edit `~/.cursor/cli-config.json` to set model or max-mode.** Cursor manages that file itself and overwrites it on each launch, so any model / `maxMode` change you make there is reverted and silently ignored by larch. For larch's own Cursor invocations, the model is **hard-coded to `composer-2.5`** (passed via `cursor agent --model composer-2.5` from `python3 python/cli.py agent model-args`), and **max-mode is forced on** via the `/max-mode on. Prompt:` slash-command prefix prepended by `python3 python/cli.py agent cursor-wrap-prompt`. To override the default model, set `LARCH_CURSOR_MODEL` (or `CLAUDE_PLUGIN_OPTION_CURSOR_MODEL`) in your environment rather than touching the cli-config file.

- **GUI popup suppression (issue #5797).** larch exports `NO_OPEN_BROWSER=1` into every Cursor child's environment so `cursor agent` does not open the Cursor.app "Composer" GUI window (via a `cursor://` deeplink) during headless lanes. Auth is unaffected — larch authenticates via `CURSOR_API_KEY` / keychain, never interactive login.

### Validate
- Run `/status` in `claude` session, to get report similar to this:
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
- Run `/upgrade-larch` skill in your claude session, and then restart `claude`

