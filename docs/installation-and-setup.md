# Installation and Setup

Larch is distributed as a [Claude Code plugin](https://code.claude.com/docs/en/plugin-marketplaces). Installation starts by registering the marketplace that hosts larch, then installing the plugin from that marketplace.

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

To upgrade larch to the latest stable version, run the `/upgrade-larch` skill in any Claude Code session:

```
/upgrade-larch
```

After `/upgrade-larch` finishes, restart Claude Code only if it actually installed a new version. If it reports that you are already on the latest stable release, no restart is needed. The upgrade script prints an installed-version block when `claude plugin list` succeeds; treat it as best-effort confirmation.

`/upgrade-larch` is idempotent only when `gh` is installed and can resolve the latest stable release: if the currently installed version already matches that stable release, it exits immediately with no changes. If `gh` is unavailable or cannot resolve stable releases, the script warns and upgrades unconditionally, skips stable-version verification, and skips pruning.

When `/upgrade-larch` does verify a stable install successfully, it removes any cached larch versions newer than the verified stable release and then attempts to prune older cached versions toward a total of at most 8 cached versions, always preserving the verified stable release directory when it exists. If a cache-directory removal fails, extra directories can remain on disk and the script warns instead of claiming they were deleted. Before removing any version the script also preserves the currently executing cached plugin version, then scans current-user-owned larch session env files under `${XDG_CACHE_HOME:-${HOME:-/tmp}/.cache}/larch/sessions` plus current-user-owned `/tmp` and `/private/tmp` fallback `claude-*` session dirs and preserves versions still named by a running session's `LARCH_CLAUDE_PLUGIN_ROOT`. Stale session directories can therefore delay pruning until their cache entries are cleaned up.

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

- A bug fix committed to your working tree does not take effect until you reinstall or refresh the plugin from that checkout. `/larch:upgrade-larch` updates the latest stable GitHub install; a local checkout install (`claude --plugin-dir .` or `claude plugin marketplace add .`) needs a local reinstall/refresh instead. Until then, every `/implement` or `/fix-issue` run uses the older cached version.
- Multiple concurrent clones (e.g., `larch1/`, `larch2/`) share the same plugin cache. Upgrading from one clone upgrades for all.

**Automatic detection**: when the installed version is behind your working-tree version, larch emits a warning at session setup time:

```
**⚠ larch: installed plugin version (X.Y.Z) is behind the working tree (A.B.C).
Reinstall or refresh the plugin from this checkout before the next run to pick up the latest fixes.
Continuing with the cached version.**
```

This warning fires once per `session-setup.sh` invocation from a larch dev clone. Typical entrypoints include `/implement`, `/fix-issue`, and `/review`. After reinstalling or refreshing the plugin cache, restart Claude Code to pick up the new version.

### Mermaid CLI (required for the `lint-mermaid-fences` pre-commit hook)

Contributors editing any `.md` file in this repo trigger the
`lint-mermaid-fences` pre-commit hook, which runs `mmdc` against every
` ```mermaid ` fence in the staged Markdown to catch unsafe content
before it lands in tracking-issue summaries or PR bodies. The hook hard-fails
(exit 2) when the Mermaid CLI is not installed, so a one-time
installation is required:

```bash
cd larch
npm install              # creates node_modules/ (gitignored) + binds the lockfile
```

This installs `@mermaid-js/mermaid-cli` (pinned in `package.json` /
`package-lock.json`) plus its Puppeteer/Chromium dependency under
`node_modules/.bin/mmdc`. The hook resolves `mmdc` from
`node_modules/.bin/` first, then falls back to a globally-installed
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
- Add/edit the following in `~/.claude/settings.json` (remember to replace `<your-API-key>` with actual value):
```JSON
  "env": {
    "CLAUDE_CODE_EFFORT_LEVEL": "high"
  },
  "model": "claude-sonnet-4-6[1m]",
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
    modelId: "composer-2-5",
    displayModelId: "composer-2-5",
    displayName: "Composer 2.5",
    displayNameShort: "Composer 2.5",
    aliases: [ "composer" ],
    maxMode: true
  }
```

> **Note — larch overrides the cli-config.json model for its own Cursor invocations.**

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
| Skills | `/design`, `/implement`, `/review`, `/research`, `/fix-issue`, `/issue`, `/set-up-forked-open-source-repo`, `/upgrade-larch`, `/alias`, `/create-skill`, `/simplify-skill`, `/compress-skill`, `/im`, `/imaq`, `/imq` |
| Agents | `code-reviewer` (unified archetype covering code quality, risk/integration, correctness, architecture, security) |
| PreToolUse hooks | `block-submodule-edit.sh` blocks `Edit`/`Write` on files inside any checked-out git submodule of the consuming project; `hook-block-skill-relevant-checks.sh` blocks `/relevant-checks` Skill calls inside active `/implement` or `/review` sessions so orchestrators use the captured helper |
| SessionStart hook | `sessionstart-health.sh` — at session start/resume/clear/compact, probes `jq` and `git` on `PATH`; if either is missing, injects an advisory into session context so the issue is visible before the first `Edit`/`Write`. Non-blocking (always exits 0); silent when both tools are present |

## `/relevant-checks` — required consumer dependency

> **Important:** `/implement` and `/review` run the project-local relevant-checks script after code changes. If your repo does not provide one, these workflows will fail at the validation step.

The `/relevant-checks` skill is **not part of the plugin surface** — it is present in the install directory but not loaded by the plugin runtime. Each consuming repo must provide its own project-level `.claude/skills/relevant-checks/` directory with build and lint commands tailored to that repo. Human operators can invoke that Skill directly; larch orchestrators call `.claude/skills/relevant-checks/scripts/run-checks.sh` through the plugin helper `scripts/run-relevant-checks-captured.sh` so successful checks do not spend LLM tokens.

**To create one for your repo:**

1. Create `.claude/skills/relevant-checks/SKILL.md` with `allowed-tools: Bash`
2. Add a `scripts/run-checks.sh` that runs your repo's linters, tests, or validators
3. Keep the script executable and preserve the documented exit-path matrix: success exits 0 after at least one validation phase, check failures return the underlying tool exit code, and zero validation coverage exits non-zero with an `ERROR:` line.

Larch's own copy at `.claude/skills/relevant-checks/` serves as a reference implementation — it runs `pre-commit` linters plus `agent-lint` (if available on PATH).

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
- **jq** — [JSON processor](https://jqlang.github.io/jq/). Used by validation scripts, session setup, and the post-/design halt-protection hooks (`hook-post-design.sh` PostToolUse + `hook-stop-fail-close.sh` Stop). When `jq` is missing, both hooks short-circuit at their `command -v jq` probe, halt protection is silently disabled, and `/implement` can stop mid-run after `/design` returns. The SessionStart hook (see below) injects an advisory when `jq` is absent so the gap is visible at session start.

### Optional integrations

These tools enhance the workflow but are not required. Fallback behavior varies by tool — see each bullet below.

- **Codex** — [OpenAI Codex CLI](https://github.com/openai/codex). Participates as an external reviewer and voter alongside Claude subagents. When unavailable, Codex-specific reviewer slots are skipped and voting may collapse per threshold rules.
- **Cursor** — [Cursor AI editor](https://cursor.com/). Participates as an external reviewer and voter. When unavailable, Cursor-specific reviewer slots are skipped and voting may collapse per threshold rules.

### Contributor development

- **pre-commit** — `pip install pre-commit` for local linting (`make setup` installs git hooks)
- **Python 3.12+** — required by pre-commit
