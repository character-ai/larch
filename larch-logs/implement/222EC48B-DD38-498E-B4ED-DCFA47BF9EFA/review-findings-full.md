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

### FINDING_12: panel [code-review/accepted]

## code-quality: skills/upgrade-larch/scripts/upgrade-larch.md:31-36 skills/upgrade-larch/scripts/test-upgrade-larch-prune.md:17-17

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Edit-in-sync lists omit Makefile harness wiring Editors may change scripts without updating CI shard targets Add Makefile bullet to both edit-in-sync lists
- **Suggested revision**: Address the concern above.

### FINDING_14: panel [code-review/accepted]

## correctness: implementation_plan §Regression test structure case 2; skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh (no-sessions-prunes-old); skills/upgrade-larch/scripts/upgrade-larch.sh (ACTIVE_SESSION_VERSIONS += INSTALLED_VERSION)

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Literal plan acceptance "no sessions -> prune 29.1.19 and 29.1.20" is not met; executing numeric cache version is always kept. Checklists or reviewers using the plan text expect 29.1.20 removed with no sessions; tests and code require 29.1.20 to remain. Update the plan/issue acceptance to match shipped contract (executing cached version preserved; only unused olds pruned).
- **Suggested revision**: Address the concern above.

### FINDING_17: panel [code-review/accepted]

## correctness: skills/upgrade-larch/scripts/upgrade-larch.sh:117-128

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] CRLF or trailing whitespace on LARCH_CLAUDE_PLUGIN_ROOT value breaks is_safe_version. A valid absolute path whose basename should be 29.1.x is ignored; that cached version can be pruned while a session still uses the path. Strip \r and trim trailing whitespace before basename / is_safe_version; add a CRLF regression case in test-upgrade-larch-prune.sh.
- **Suggested revision**: Address the concern above.

### FINDING_26: panel [code-review/accepted]

## security: skills/upgrade-larch/scripts/upgrade-larch.sh:97-131

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Prune guard honors session-env pins discovered under world-writable /tmp and /private/tmp via claude-* globs. On a shared host, another local user can create /tmp/claude-<name>/session-env.sh with LARCH_CLAUDE_PLUGIN_ROOT=/x/<numericVersion> so the victim's upgrade run skips pruning that cached version even without a real session, enabling cleanup denial or disk-retention harassment. Restrict fallback scanning to dirs owned by the current euid, drop /tmp fallback, or otherwise tie pins to the operator's session roots only.
- **Suggested revision**: Address the concern above.

### FINDING_9: panel [code-review/accepted]

## code-quality: docs/installation-and-setup.md:40 vs skills/upgrade-larch/scripts/upgrade-larch.md:18

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Install doc omits /private/tmp fallback present in script contract Operators on macOS may misunderstand which dirs participate in the prune guard Mention /private/tmp next to /tmp in installation-and-setup.md
- **Suggested revision**: Address the concern above.

### FINDING_11: panel [code-review/accepted]

## risk-integration: skills/upgrade-larch/scripts/upgrade-larch.sh:107-114;skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Global /tmp claude-* session-env scan is always on; harness does not isolate /tmp. Host has unrelated /tmp/claude-*/session-env.sh pinning the same basename as a version the test expects pruned from an isolated fake cache; assertion on removal fails. Document CI-only assumption; or add test-only env to narrow fallback scan; or use a container with clean /tmp.
- **Suggested revision**: Address the concern above.

### FINDING_12: panel [code-review/accepted]

## risk-integration: skills/upgrade-larch/scripts/upgrade-larch.sh:292-293

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Warning text claims an active session while behavior is env-pin and stale-dir driven. Operators misinterpret logs or over-trust liveness semantics when diagnosing prune behavior. Reword warning to match upgrade-larch.md (session env pins / stale dirs).
- **Suggested revision**: Address the concern above.

### FINDING_13: panel [code-review/accepted]

## security: skills/upgrade-larch/scripts/upgrade-larch.sh:121-127

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Primary LARCH_SESSIONS_DIR session-env.sh reads lack the ownership check used for /tmp fallback. If larch/sessions (or LARCH_SESSIONS_DIR) is writable by another local UID, a peer can plant or replace session-env files (or symlinks) affecting prune pins or triggering reads of unintended files under the awk read path. Require [ -O "$env_file" ] (or equivalent) before awk for all session-env.sh paths, not only /tmp and /private/tmp.
- **Suggested revision**: Address the concern above.

### FINDING_3: panel [code-review/accepted]

## code-quality: skills/upgrade-larch/scripts/upgrade-larch.sh:290-297

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Redundant empty-array guard wraps the inner active-version loop. No concrete breakage; extra nesting without behavior change. Remove the outer length check and rely on the inner for-loop over an empty array.
- **Suggested revision**: Address the concern above.

### FINDING_4: panel [code-review/accepted]

## code-quality: skills/upgrade-larch/scripts/upgrade-larch.sh:292-294

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Prune-skip warning says an active session is using the version while the documented contract is session-env pins including stale dirs on disk. An operator infers live-process detection from stderr and is surprised when pruning is delayed by abandoned session directories only. Rephrase the warning to reference session-env pins or stale session metadata so it matches upgrade-larch.md and installation docs.
- **Suggested revision**: Address the concern above.

### FINDING_5: panel [code-review/accepted]

## correctness: implementation_plan §Regression test structure case 2; skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh; skills/upgrade-larch/scripts/upgrade-larch.sh

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Written plan expected no-session prune to remove both 29.1.19 and 29.1.20; implementation preserves executing INSTALLED_VERSION and test keeps 29.1.20. A contributor or bot reconciling PR against the old acceptance table concludes the harness violates the plan or demands deletion of the executing cache slot. Update the authoritative plan / acceptance table: no session-env pins still preserve executing numeric cached PLUGIN_ROOT per delivered contract.
- **Suggested revision**: Address the concern above.

### FINDING_6: panel [code-review/accepted]

## correctness: skills/upgrade-larch/scripts/upgrade-larch.md:18;docs/installation-and-setup.md:40

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Default LARCH_SESSIONS_DIR wording omits HOME fallback to /tmp used by the script and session-setup. Readers assume $HOME/.cache when HOME is unset; actual default is ${HOME:-/tmp}/.cache per upgrade-larch.sh:149. Update both doc strings to match upgrade-larch.sh:149 / session-setup session_cache_root().
- **Suggested revision**: Address the concern above.

### FINDING_8: panel [code-review/accepted]

## correctness: skills/upgrade-larch/scripts/upgrade-larch.sh:292-294

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Warning says active session though stale env pins and executing PLUGIN_ROOT also trigger the skip. Operator infers live process detection from wording; behavior is broader. Align warning string with upgrade-larch.md pin semantics.
- **Suggested revision**: Address the concern above.

