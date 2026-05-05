# Installation and Setup

Larch is distributed as a [Claude Code plugin](https://code.claude.com/docs/en/plugin-marketplaces). Installation is a two-step process: register the marketplace that hosts larch, then install the plugin from that marketplace.

Slack integration is optional and **on by default** when `LARCH_SLACK_BOT_TOKEN` and `LARCH_SLACK_CHANNEL_ID` are configured. `/implement` posts a single tracking-issue status message near the end of each run; pass `--no-slack` to opt out. See [Environment Variables](configuration-and-permissions.md#environment-variables) — skills degrade gracefully when Slack is not configured.

## Install from GitHub

### Latest stable release

#### Install
```bash
claude plugin marketplace add character-ai/larch
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

To upgrade larch to the latest version, run the `/upgrade-larch` skill in any Claude Code session, then restart Claude Code:

```
/upgrade-larch
```

After the skill completes, restart Claude Code to apply the new version.

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

## Setting Up Claude, Codex, Cursor, Gemini
- **Only `claude` is mandatory.** `codex`, `cursor`, and `gemini` are optional — when `codex` or `cursor` is missing or fails to authenticate, larch skills substitute Claude subagents automatically; `gemini` is additive (skipped silently when unavailable for reviewer use, falls back to Claude when selected as `--coder=gemini`). See [Optional integrations](#optional-integrations) for the full fallback semantics.
- **Larch is agent-agnostic about authentication.** Each agent can be set up either with an **API key** in your shell environment, or with a **subscription plan** via web-based login from the binary itself. Larch does not care which — it only needs the corresponding binary (`claude`, `codex`, `cursor`, `gemini`) to be on your `PATH` and to land in an authenticated session when invoked.
- The subsections below document one concrete setup recipe per agent (API-key path). If you prefer the subscription-plan path, install the binary and follow its own web-login flow instead — the rest of larch's configuration (settings, model overrides) still applies.

### Claude
- Via web UI of your Claude org, create your own API key
- Add it to your env (e.g., in `.bashrc`: `export ANTHROPIC_API_KEY="<your-key>"` (replace `<your-key>`, of course))
- Add/edit the following in `~/.claude/settings.json` (remember to replace `<your-API-key>` with actual value):
```JSON
  "env": {
    "CLAUDE_CODE_EFFORT_LEVEL": "high"
  },
  "model": "claude-opus-4-7[1m]",
```
- Install claude code: `curl -fsSL https://claude.ai/install.sh | bash`
- Run `claude` and verify the above settings
- **Minimum `claude` CLI version**: a build that supports `--permission-mode bypassPermissions` is required. Loop drivers that spawn `claude -p` children carry this flag so an in-child tool-permission prompt cannot stall a non-interactive subprocess until the watchdog fires. Older `claude` binaries that do not recognize the flag fail-fast (subprocess returns non-zero). Verify with `claude --permission-mode bypassPermissions --version` if uncertain.

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
- Edit `~/.cursor/cli-config.json` and change `model` section to read:
```JSON
  "model": {
    "modelId": "composer-2",
    "displayModelId": "composer-2",
    "displayName": "Composer 2",
    "displayNameShort": "Composer 2",
    "aliases": [
      "composer"
    ],
    "maxMode": true
  }
```

> **Note — larch overrides the cli-config.json model for its own Cursor invocations.**

### Gemini
- Install Gemini CLI with Homebrew or npm:
```bash
brew install gemini-cli
# or
npm install -g @google/gemini-cli
```
- Authenticate with OAuth:
```bash
gemini auth login
```
- Add/edit `~/.gemini/settings.json` with your authentication mode and preferred model. For Gemini 3 preview work, use a model name such as:
```JSON
{
  "auth": {
    "type": "oauth"
  },
  "model": {
    "name": "gemini-3-pro-preview"
  }
}
```
- Add every repo you want Gemini to access to `~/.gemini/trustedFolders.json` using case-correct absolute paths:
```JSON
{
  "trustedFolders": [
    "/Users/<your-user-name>/path/to/repo"
  ]
}
```
- `trustedFolders.json` path matching is case-sensitive even on case-insensitive macOS filesystems. If the path case differs from the real checkout path, headless `gemini -p` runs can hang silently behind a trust prompt.
- Gemini CLI 0.40.x does not look up `rg` on `PATH`; it only checks for a bundled binary at `<gemini-pkg>/bundle/vendor/ripgrep/rg-<platform>-<arch>`, which Homebrew/npm installs may omit. Install ripgrep first (`brew install ripgrep`) so `which rg` resolves, then on Apple Silicon macOS create the missing bundled path as a symlink:
```bash
mkdir -p <gemini-pkg>/bundle/vendor/ripgrep
ln -sf "$(which rg)" <gemini-pkg>/bundle/vendor/ripgrep/rg-darwin-arm64
```
  Re-run the symlink command after each `brew upgrade gemini-cli`.
- Free-tier accounts can hit hard `MODEL_CAPACITY_EXHAUSTED` 429s on `gemini-3-*-preview` models when used from the Gemini CLI. Google AI Pro may raise available capacity; Google AI Ultra unblocks these preview-model capacity failures.
- `/implement --coder=gemini` uses the same Gemini CLI install/auth/trusted-folder setup as the Gemini reviewer path, but runs with `--approval-mode yolo --skip-trust` so Gemini can execute shell tools during implementation.

## What the plugin provides

| Component | Description |
|---|---|
| Skills | `/design`, `/implement`, `/review`, `/research`, `/fix-issue`, `/issue`, `/upgrade-larch`, `/alias`, `/create-skill`, `/simplify-skill`, `/compress-skill`, `/im`, `/imaq`, `/imq` |
| Agents | `code-reviewer` (unified archetype covering code quality, risk/integration, correctness, architecture, security) |
| PreToolUse hook | `block-submodule-edit.sh` — blocks `Edit`/`Write` on files inside any checked-out git submodule of the consuming project |
| SessionStart hook | `sessionstart-health.sh` — at session start/resume/clear/compact, probes `jq` and `git` on `PATH`; if either is missing, injects an advisory into session context so the issue is visible before the first `Edit`/`Write`. Non-blocking (always exits 0); silent when both tools are present |

## `/relevant-checks` — required consumer dependency

> **Important:** `/implement` and `/review` invoke `/relevant-checks` after each commit during their workflows. If your repo does not define one, these workflows will fail at the validation step.

The `/relevant-checks` skill is **not part of the plugin surface** — it is present in the install directory but not loaded by the plugin runtime. Each consuming repo must provide its own `/relevant-checks` as a project-level skill at `.claude/skills/relevant-checks/` with build and lint commands tailored to that repo.

**To create one for your repo:**

1. Create `.claude/skills/relevant-checks/SKILL.md` with `allowed-tools: Bash`
2. Add a `scripts/run-checks.sh` that runs your repo's linters, tests, or validators
3. Reference the script from SKILL.md using `$PWD/.claude/skills/relevant-checks/scripts/run-checks.sh`

Larch's own copy at `.claude/skills/relevant-checks/` serves as a reference implementation — it runs `pre-commit` linters plus `agent-lint` (if available on PATH).

## Clean-main entry contract for `/implement` and `/design`

`/implement` and standalone `/design` fail closed at entry unless one of two preconditions holds. The check runs in `preflight.sh` before any side effects — for `/implement`, before any tracking-issue side effects (no issue is created, no anchor comment is planted) and before any branch is created; for standalone `/design` (which does not create a tracking issue at entry), before any branch is created. An aborted entry leaves no remote state behind.

**(a) Default — clean `main`.** The skill asserts that the working tree is on `main`, has no uncommitted changes, fetches `origin/main`, and rebases local `main` onto it. A dirty tree, a non-`main` branch with no recognized prefix, or a fetch failure aborts with a normalized error.

**(b) Continuation opt-in — `<USER_PREFIX>/*` feature branch.** Running on a branch whose name starts with your configured `<USER_PREFIX>/` (e.g., `sergey-zhupanov/foo`) is the explicit signal that you want to continue from current state. The gate is bypassed; the skill keeps working on the current branch.

**(c) `--issue <N>` does not waive the gate.** Adopting an existing tracking issue with `--issue <N>` controls *identity* (which issue is updated and auto-closed) but does not relax the working-tree requirement. You still need either a clean `main` or a `<USER_PREFIX>/*` branch to start.

**(d) Failure modes and recovery.** When preflight fails, the orchestrator prints the raw `PREFLIGHT_ERROR=...` followed by a normalized message naming the skill that was invoked. From `/implement`:

> ⚠ /implement requires clean main to start. To continue, choose one of: (a) `git checkout main && git status` clean → re-run; (b) check out or create a `<USER_PREFIX>/*` feature branch and re-run (the branch naming convention is the explicit opt-in to continue from current state); (c) commit or stash uncommitted changes on `main` first.

Standalone `/design` prints the same message with `/design` substituted for `/implement`. The three remediation paths (clean `main`, `<USER_PREFIX>/*` continuation, commit-or-stash) cover dirty trees, wrong-branch starts, and transient fetch failures.

## Prerequisites

Larch skills have different dependency requirements depending on which features you use.

### Installation dependencies

- **Claude Code** — required. Install via [setup instructions](https://code.claude.com/docs/en/setup).

### Workflow automation (`/implement --merge`, `/review`)

These tools are required for the full design → implement → PR → merge workflow:

- **git** — version control (used by all skills)
- **gh** — [GitHub CLI](https://cli.github.com/), authenticated with repo write access (`gh auth login`). Required for PR creation, CI monitoring, and merge automation.
- **jq** — [JSON processor](https://jqlang.github.io/jq/). Used by validation scripts and session setup.

### Optional integrations

These tools enhance the workflow but are not required. When unavailable, Claude replacement agents fill in automatically:

- **Codex** — [OpenAI Codex CLI](https://github.com/openai/codex). Participates as an external reviewer and voter alongside Claude subagents. When unavailable, a Claude subagent replacement maintains the reviewer count.
- **Cursor** — [Cursor AI editor](https://cursor.com/). Participates as an external reviewer and voter. When unavailable, a Claude subagent replacement maintains the reviewer count.
- **Gemini** — [Gemini CLI](https://github.com/google-gemini/gemini-cli). Adds an optional external reviewer slot in rounds 1-3 and joins the external chain in rounds 4+ when healthy. When unavailable, reviewer use is skipped in rounds 1-3 and falls through to the next external reviewer in rounds 4+; `/implement --coder=gemini` falls back to Claude. See [Gemini](#gemini) for setup details.
- **Slack** — Single tracking-issue status message per `/implement` run (and for `/fix-issue` NON_PR closures). On by default when Slack env vars are configured; pass `--no-slack` to opt out. Requires environment variables or plugin `userConfig` (see [Environment Variables](configuration-and-permissions.md#environment-variables)). When `--no-slack` is passed, all Slack operations are skipped silently. When env vars are missing (and `--no-slack` was not passed), the operation is skipped with a warning at session setup. All other workflow steps proceed normally in either case.

### Contributor development

- **pre-commit** — `pip install pre-commit` for local linting (`make setup` installs git hooks)
- **Python 3.12+** — required by pre-commit
