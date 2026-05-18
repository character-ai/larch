### FINDING_1: panel [code-review/accepted]

## **Important** `correctness` — `skills/upgrade-larch/scripts/upgrade-larch.sh:127` defaults `LARCH_SESSIONS_DIR` to `$HOME/.cache/larch/sessions`, but sessions are created under `${XDG_CACHE_HOME:-$HOME/.cache}/larch/sessions` in `scripts/session-setup.sh:203-205`. If an operator has `XDG_CACHE_HOME=/tmp/xdg`, an active session env under `/tmp/xdg/larch/sessions/.../session-env.sh` is invisible to pruning, so its pinned version can still be deleted. Default to `${XDG_CACHE_HOME:-${HOME:-/tmp}/.cache}/larch/sessions`, and add a regression case that does not override `LARCH_SESSIONS_DIR`.

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `correctness` — `skills/upgrade-larch/scripts/upgrade-larch.sh:127` defaults `LARCH_SESSIONS_DIR` to `$HOME/.cache/larch/sessions`, but sessions are created under `${XDG_CACHE_HOME:-$HOME/.cache}/larch/sessions` in `scripts/session-setup.sh:203-205`. If an operator has `XDG_CACHE_HOME=/tmp/xdg`, an active session env under `/tmp/xdg/larch/sessions/.../session-env.sh` is invisible to pruning, so its pinned version can still be deleted. Default to `${XDG_CACHE_HOME:-${HOME:-/tmp}/.cache}/larch/sessions`, and add a regression case that does not override `LARCH_SESSIONS_DIR`.
- **Suggested revision**: Address the concern above.

### FINDING_14: panel [code-review/accepted]

## correctness: skills/upgrade-larch/scripts/upgrade-larch.sh:126-127

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Default LARCH_SESSIONS_DIR ignores XDG_CACHE_HOME while implement session tmpdirs are rooted at ${XDG_CACHE_HOME:-$HOME/.cache}/larch/sessions Operator sets XDG_CACHE_HOME; running session writes session-env.sh under that tree; upgrade-larch scans only $HOME/.cache/larch/sessions, misses the pin, prunes the in-use cached plugin version Default LARCH_SESSIONS_DIR to ${XDG_CACHE_HOME:-${HOME:-/tmp}/.cache}/larch/sessions (match lib-resolve-implement-tmpdir) and update contract docs accordingly
- **Suggested revision**: Address the concern above.

### FINDING_16: panel [code-review/accepted]

## correctness: skills/upgrade-larch/scripts/upgrade-larch.sh:97-127

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Default LARCH_SESSIONS_DIR does not match session-setup session roots (XDG_CACHE_HOME and /tmp fallback). (A) XDG_CACHE_HOME=/custom/xdg: live session-env under /custom/xdg/larch/sessions/.../session-env.sh pins 29.1.20 but scanner only reads ~/.cache/larch/sessions/*/session-env.sh so prune removes 29.1.20. (B) session-setup cache probe fails: SESSION_TMPDIR=<TMPDIR> with session-env.sh there; scanner never visits /tmp so same prune miss. Default to the same cache root formula as session-setup.sh session_cache_root() and add scan of /tmp (and /private/tmp) claude-* session dirs—or reuse shared resolver logic if available.
- **Suggested revision**: Address the concern above.

### FINDING_17: panel [code-review/accepted]

## risk-integration: Makefile; .github/workflows/ci.yaml

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] New prune regression harness is not wired into Makefile test-harness shards or CI. Merge can ship broken active-session pruning if local skill validation is skipped. Add skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh (and ideally test-upgrade-larch.sh) to a Makefile test-harness target consumed by CI.
- **Suggested revision**: Address the concern above.

### FINDING_18: panel [code-review/accepted]

## risk-integration: docs/installation-and-setup.md

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Upgrade prose says running session while implementation scans session-env files under LARCH_SESSIONS_DIR. Operators may misunderstand when versions are preserved (stale session dirs vs live process). Align wording with upgrade-larch.md contract (env pins / stale dirs).
- **Suggested revision**: Address the concern above.

### FINDING_19: panel [code-review/accepted]

## risk-integration: skills/upgrade-larch/scripts/test-upgrade-larch-prune.md

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Edit-in-sync list omits docs/installation-and-setup.md despite parallel doc change. Future contributors may forget to update user-facing install docs when pruning rules change. Include docs/installation-and-setup.md in the edit-in-sync list.
- **Suggested revision**: Address the concern above.

### FINDING_2: panel [code-review/accepted]

## **Important** `correctness` — `skills/upgrade-larch/scripts/upgrade-larch.sh:230-274` only protects versions discovered from session env files; `/upgrade-larch` itself does not create one (`skills/upgrade-larch/SKILL.md:15-19`). Concrete scenario: a Claude Code session running from cached version `29.1.20` upgrades to `29.1.22`, previous stable is `29.1.21`, and no larch session env exists; the prune loop deletes `29.1.20`, leaving the still-running session’s `CLAUDE_PLUGIN_ROOT` pointing at a removed directory until restart. Seed the protected set with the executing `PLUGIN_ROOT`/`INSTALLED_VERSION` when it is a safe numeric cached version, and update `skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh:173-184` so the no-session case does not assert pruning the current in-use root.

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Important** `correctness` — `skills/upgrade-larch/scripts/upgrade-larch.sh:230-274` only protects versions discovered from session env files; `/upgrade-larch` itself does not create one (`skills/upgrade-larch/SKILL.md:15-19`). Concrete scenario: a Claude Code session running from cached version `29.1.20` upgrades to `29.1.22`, previous stable is `29.1.21`, and no larch session env exists; the prune loop deletes `29.1.20`, leaving the still-running session’s `CLAUDE_PLUGIN_ROOT` pointing at a removed directory until restart. Seed the protected set with the executing `PLUGIN_ROOT`/`INSTALLED_VERSION` when it is a safe numeric cached version, and update `skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh:173-184` so the no-session case does not assert pruning the current in-use root.
- **Suggested revision**: Address the concern above.

### FINDING_9: panel [code-review/accepted]

## correctness: docs/installation-and-setup.md:40

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] "Running session" implies liveness Stale session dirs also pin; doc overstates detection Match wording to upgrade-larch.md session-cache semantics
- **Suggested revision**: Address the concern above.

