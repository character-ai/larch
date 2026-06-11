# scripts/lib-sparse-dirs.sh — contract

`scripts/lib-sparse-dirs.sh` is the sourced-only single source of truth for the plugin install sparse allowlist. It defines `LARCH_SPARSE_DIRS` and `normalize_sparse_dirs()` for `python/cli.py upgrade-larch run`, `scripts/sessionstart-health.sh`, the `/release` Step 7 working-tree upgrade path, and the related harnesses.

The file has no shebang, no `set`, no `exec`, no trap, no quiet-log initialization, and no top-level commands beyond function/variable definitions. Line 1 stays `# shellcheck shell=bash`, the file stays non-executable, and `agent-lint.toml` excludes the sourced-only `.sh` plus this sibling contract from dead-script checks.

## Script-root versus installed-root split

`python/cli.py upgrade-larch run` resolves the working tree containing the Python module being executed and ports this library's sparse allowlist. It must not read the sparse allowlist from `CLAUDE_PLUGIN_ROOT` / `PLUGIN_ROOT`: those variables remain the installed/cache root used for quiet mode, `LARCH_CACHE_DIR`, `INSTALLED_VERSION`, install stamps, and prune protection.

`sessionstart-health.sh` sources this library from its own `SCRIPT_DIR`, not from `HOOK_CWD` and not from `upgrade-larch run`. `/release` Step 7 runs the working-tree upgrade Python CLI against the resolved active installed/cache root, so just-released allowlist changes are read from the working-tree implementation even when `CLAUDE_PLUGIN_ROOT` points at an older cached install.

## Edit-in-sync

Prose copies of the sparse install allowlist in `docs/installation-and-setup.md`, `docs/skills.md`, `skills/upgrade-larch/SKILL.md`, `python/upgrade_larch.py`, and `.claude/skills/release/SKILL.md` are illustrative and tracked manually. Allowlist edits must update both the assignment in this file and the intentional expected-literal guard in `python/test_upgrade_larch.py`; do not weaken that guard into a library-vs-itself tautology unless deliberately removing the duplicate assertion.
