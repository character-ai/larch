# Contributing to Larch

## Install

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

## Plugin cache vs. working-tree version

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

## Mermaid diagram rendering

`/design` and `/implement` produce Mermaid architecture and code-flow
diagrams as fenced Markdown blocks. These render automatically in the
Claude Code chat panel and on GitHub. No extra tooling is needed to
view them.

## Mermaid CLI (contributors only: required when editing `.md` files with Mermaid fences)

If you work from a **full dev clone** (not a marketplace sparse checkout)
and edit any `.md` file, the `lint-mermaid-fences` pre-commit hook
validates staged Mermaid fences with `mmdc` before they land in
tracking-issue summaries or PR bodies. If fences are present and the
CLI is not installed, the hook hard-fails (exit 2).

**Prerequisite:** Node.js (LTS recommended, needed by `npm ci`).

```bash
cd larch
(cd mermaid-lint && npm ci)
```

This installs `@mermaid-js/mermaid-cli` 11.12.0 (pinned in
`mermaid-lint/package.json`) plus its Puppeteer/Chromium dependency
under `mermaid-lint/node_modules/.bin/mmdc`. The hook resolves `mmdc`
from `mermaid-lint/node_modules/.bin/` first, then falls back to a
globally-installed `mmdc` on `PATH`.

Marketplace/sparse installs omit `mermaid-lint/` entirely and do not
trigger this hook.

To skip the hook for a single commit without installing the toolchain:

```bash
SKIP=lint-mermaid-fences git commit …
```

CI installs the toolchain itself, so the hook still runs there even
when locally skipped.
