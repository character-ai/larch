## Goal
Implement issue #3231: [IMPLEMENTING] Slim & speed up /upgrade-larch: --sparse out larch-logs, drop install-time npm, in-place marketplace update\n\n## Problem.

## Implementation Plan
## Plan

### Scope (closed decisions — do not re-open, do NOT defer any part)

ALL of the following land in a **single PR**. Nothing is out-of-scope; do not spin off OOS follow-up issues for any item below.

- **Part 1 — exclude `larch-logs/` from the install via `claude plugin marketplace add --sparse`** (cone-mode include-list = every top-level tracked directory EXCEPT `larch-logs/` and the new `mermaid-lint/` from Part 3).
- **Part 2 — replace the unconditional `marketplace remove` + `marketplace add` roundtrip with an in-place `claude plugin marketplace update`** on the steady-state path; keep `uninstall` + `install` (preserves prune-keeps-8 rollback). Do NOT use `claude plugin update`.
- **Part 3 — eliminate the install-time `npm install`** by moving the mermaid toolchain (`package.json` + `package-lock.json`) into a new top-level `mermaid-lint/` directory that is excluded from the sparse checkout. The installed plugin then has no `package.json` anywhere, so the installer runs no `npm install` and ships no `node_modules`. Dev/CI keep using `npm ci`, repointed to `mermaid-lint/`.
- **Part 4 — remove all `/upgrade-larch` tests and add NO new tests.** Delete `skills/upgrade-larch/scripts/test-upgrade-larch.sh`, `test-upgrade-larch-prune.sh`, and `test-upgrade-larch-prune.md`, plus every Makefile/doc reference. `/release` has no tests. Add no replacement tests, no drift guard, no test-case additions anywhere. Test removal is intentional and required — reviewers must not flag it.
- **Approach decisions (closed):** `--sparse` cone list = full top-level surface minus `larch-logs` and `mermaid-lint` (provably zero runtime regression — `.claude/` stays listed because `/implement` Step 8 uses `.claude/skills/bump-version`); mermaid toolchain relocated to a non-shipped dir (NOT removed, NOT switched to `npx`, NOT kept at root); `marketplace update` over `plugin update`. The sparse include-list is maintained by a code comment only (no test).

### Background the implementer needs

- `upgrade-larch.sh` pieces: the `recover()` function near the top (manual-recovery banner), the teardown-and-reinstall block (the four `claude plugin` calls beginning with the `Uninstalling larch plugin...` log line), and a second manual-recovery banner inside the post-install verification-failure branch.
- The script already assumes the `~/.claude/plugins/` layout (it reads `$HOME/.claude/plugins/installed_plugins.json`). Marketplace clone: `$HOME/.claude/plugins/marketplaces/larch-local`. A SPARSE clone has NO `larch-logs/` subdir; a legacy FULL clone has it.
- `shellcheck` and `actionlint` run in `make lint`; unquoted `$LARCH_SPARSE_DIRS` (intentional word-splitting) needs `# shellcheck disable=SC2086` on each line that expands it. `.gitignore` already ignores `node_modules/` at any depth, so `mermaid-lint/node_modules/` is ignored.

---

### Part 1 — `skills/upgrade-larch/scripts/upgrade-larch.sh`

**1a.** Immediately after the `exec 1>&3` line and before `recover()`, add the include-list constant:

```bash
# Top-level repo directories shipped to consumers via the plugin install:
# every top-level tracked directory EXCEPT larch-logs/ (committed run logs,
# ~317 MB, never read from the install at runtime) and mermaid-lint/ (dev-only
# Mermaid lint toolchain — excluded so the installed plugin has no package.json
# and the installer runs no npm install). Passed to
# `claude plugin marketplace add --sparse` (git sparse-checkout, cone mode);
# cone mode always keeps top-level files, so root markdown imports ship anyway.
# MAINTENANCE: if a new top-level directory is added to the repo and must ship,
# add it here; larch-logs/ and mermaid-lint/ must NOT be added.
LARCH_SPARSE_DIRS=".claude .claude-plugin .gemini .github agents docs hooks scripts skills tests"
```

**1b.** In `recover()`, change `  claude plugin marketplace add character-ai/larch` to:

```bash
    larch_err "  claude plugin marketplace add character-ai/larch --sparse $LARCH_SPARSE_DIRS"
```

**1c.** Replace the entire teardown-and-reinstall block (from the `Uninstalling larch plugin...` log line through the `claude plugin install larch@larch-local 2>&1` line) with exactly:

```bash
larch_err "Uninstalling larch plugin..."
claude plugin uninstall larch@larch-local 2>&1 || true

# Marketplace refresh. A SPARSE clone (cone excludes larch-logs/) is detected by
# the ABSENCE of its larch-logs/ subdir. When a sparse clone already exists,
# refresh it in place with `marketplace update` (a git pull — seconds) instead
# of the old remove + full re-clone. A legacy FULL clone (larch-logs/ present)
# or a missing clone triggers a one-time remove + sparse re-add to establish the
# cone; every subsequent run then takes the cheap update path.
MARKETPLACE_CLONE="$HOME/.claude/plugins/marketplaces/larch-local"
if [ -d "$MARKETPLACE_CLONE/.git" ] && [ ! -d "$MARKETPLACE_CLONE/larch-logs" ]; then
    larch_err "Refreshing larch marketplace in place (sparse clone present)..."
    if ! claude plugin marketplace update larch-local 2>&1; then
        larch_err "marketplace update failed; falling back to sparse re-add..."
        claude plugin marketplace remove larch-local 2>&1 || true
        # shellcheck disable=SC2086  # intentional word-splitting into --sparse args
        claude plugin marketplace add character-ai/larch --sparse $LARCH_SPARSE_DIRS 2>&1
    fi
else
    larch_err "Adding larch marketplace (sparse checkout; excludes larch-logs)..."
    claude plugin marketplace remove larch-local 2>&1 || true
    # shellcheck disable=SC2086  # intentional word-splitting into --sparse args
    claude plugin marketplace add character-ai/larch --sparse $LARCH_SPARSE_DIRS 2>&1
fi

larch_err "Installing larch plugin..."
claude plugin install larch@larch-local 2>&1
```

**1d.** In the post-install verification-failure branch, change its `  claude plugin marketplace add character-ai/larch` line to `  claude plugin marketplace add character-ai/larch --sparse $LARCH_SPARSE_DIRS`.

### Part 2 — `skills/upgrade-larch/scripts/upgrade-larch.md`

Rewrite the `## Behavior` "Uninstalls / Removes / Re-adds / Installs" steps to describe: the sparse include-list (all top-level dirs except `larch-logs/` and `mermaid-lint/`); the steady-state in-place `marketplace update` path vs the one-time/legacy/fallback `remove` + `add --sparse` path keyed on the absence of `$MARKETPLACE_CLONE/larch-logs`; that `uninstall` + `install` are unchanged (old version dirs persist for prune-keeps-8); and that `export-ignore` in `.gitattributes` is now superseded for the install path (kept only for `git archive`). Do not edit the `## gh availability` or pruning sections. Remove the two test-harness entries from the `## Edit-in-sync` list (Part 4). Do not edit `SECURITY.md` for Parts 1–2 (install-stamp prune trust model unchanged).

### Part 3 — eliminate the install-time `npm install` (relocate the mermaid toolchain)

**3a.** Move the toolchain into a new top-level directory (preserve git history):

```bash
mkdir -p mermaid-lint
git mv package.json mermaid-lint/package.json
git mv package-lock.json mermaid-lint/package-lock.json
```

The repo root now has no `package.json`. `mermaid-lint/` is a new top-level tracked dir and is intentionally NOT added to `LARCH_SPARSE_DIRS` (Part 1a), so it is excluded from the sparse checkout and absent from the installed plugin — the installer finds no `package.json` and runs no `npm install`.

**3b.** `scripts/lint-mermaid-fences.sh` — in `resolve_mmdc()`, repoint the node_modules probe:

```bash
    if [ -x "$REPO_ROOT/mermaid-lint/node_modules/.bin/mmdc" ]; then
        printf '%s\n' "$REPO_ROOT/mermaid-lint/node_modules/.bin/mmdc"
        return 0
    fi
```

Also update the missing-toolchain error string to suggest `(cd mermaid-lint && npm ci)` instead of `npm install`.

**3c.** `Makefile` — in the `lint-mermaid` recipe, repoint the install line:

```make
	if [ ! -f mermaid-lint/node_modules/.package-lock.json ]; then (cd mermaid-lint && npm ci); fi
	scripts/lint-mermaid-fences.sh --changed-only
```

**3d.** `.github/workflows/ci.yaml` — in the `lint-mermaid` job, repoint the five package paths (exact replacements):

- `cache-dependency-path: package-lock.json` → `cache-dependency-path: mermaid-lint/package-lock.json`
- node_modules cache `path: node_modules` → `path: mermaid-lint/node_modules`
- node_modules cache `key: node-modules-${{ runner.os }}-${{ hashFiles('package.json', 'package-lock.json') }}` → `key: node-modules-${{ runner.os }}-${{ hashFiles('mermaid-lint/package.json', 'mermaid-lint/package-lock.json') }}`
- puppeteer cache `key: puppeteer-${{ runner.os }}-${{ hashFiles('package-lock.json') }}` → `key: puppeteer-${{ runner.os }}-${{ hashFiles('mermaid-lint/package-lock.json') }}`
- `run: npm ci` → `run: cd mermaid-lint && npm ci`

Leave the `actions/setup-node` `cache: npm`, `fetch-depth: 0`, the cache-hit `if:` condition, and the `Lint Mermaid fences` / `Pipe SIGPIPE safety` steps otherwise unchanged.

**3e.** Repoint mermaid path references in docs/contracts (substitute `node_modules/.bin/mmdc` → `mermaid-lint/node_modules/.bin/mmdc` and the mermaid-pinning `package.json` → `mermaid-lint/package.json`, and `npm install`/`npm ci` dev-setup commands → `(cd mermaid-lint && npm ci)`):

- `docs/installation-and-setup.md` (the Mermaid dev-setup block: `npm install` command + the "resolves mmdc from `node_modules/.bin/` first" sentence + the "pinned in `package.json` / `package-lock.json`" sentence).
- `scripts/lint-mermaid-fences.md` (the `./node_modules/.bin/mmdc` resolution sentence, the "pins `@mermaid-js/mermaid-cli` in `package.json`" sentence, and the `## Edit-in-sync` `package.json` entry → `mermaid-lint/package.json`).
- `docs/linting.md` (the Mermaid CLI row's "install `@mermaid-js/mermaid-cli`" note and the relevant-checks `npm ci` example).
- `skills/shared/mermaid-safe-content.md` ("Keep the version pinned exactly in `package.json`" → `mermaid-lint/package.json`).

Do NOT touch `scripts/test-mermaid-fragments.sh` (a Mermaid lint test, not an `/upgrade-larch` test — it self-resolves via the lint script and tolerates a missing toolchain).

### Part 4 — remove `/upgrade-larch` tests (add none)

**4a.** Delete the harness files:

```bash
git rm skills/upgrade-larch/scripts/test-upgrade-larch.sh
git rm skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh
git rm skills/upgrade-larch/scripts/test-upgrade-larch-prune.md
```

(There is no `test-upgrade-larch.md`; that harness's contract lives in `upgrade-larch.md`.)

**4b.** `Makefile` — remove every occurrence of `test-upgrade-larch` and `test-upgrade-larch-prune`: from the umbrella `.PHONY` list, the standalone `.PHONY: test-upgrade-larch` line, the `test-harnesses-11` shard dependency list (`test-upgrade-larch`), the `test-harnesses-12` shard dependency list (`test-upgrade-larch-prune`), and both recipe definitions (`test-upgrade-larch:` and `test-upgrade-larch-prune:` with their `bash scripts/harness-timer.sh ...` recipe lines). Verify: `git grep -n 'test-upgrade-larch' Makefile` returns nothing.

**4c.** `skills/upgrade-larch/SKILL.md` — delete the `Validation: run ...test-upgrade-larch.sh and ...test-upgrade-larch-prune.sh ...` line and the `Install-stamp prune harness contract: ...test-upgrade-larch-prune.md.` line.

**4d.** `skills/upgrade-larch/scripts/upgrade-larch.md` — remove the two `## Edit-in-sync` bullets pointing at `test-upgrade-larch.sh` and `test-upgrade-larch-prune.sh`.

**4e.** `docs/linting.md` — delete the `| `make test-upgrade-larch` | ... |` table row.

**4f.** Confirm no other reference survives: `git grep -n 'test-upgrade-larch'` returns nothing repo-wide.

### Part 5 — `docs/installation-and-setup.md` Upgrade section

Add one paragraph to `#### Upgrade`: `/upgrade-larch` now installs via a sparse checkout that excludes the committed `larch-logs/` run logs and the dev-only `mermaid-lint/` toolchain (so the install carries no run logs and triggers no `npm install`), and refreshes the marketplace in place with `claude plugin marketplace update` instead of removing and re-cloning it; the first upgrade after this change does a one-time `remove` + sparse re-add, and every later upgrade uses the fast in-place update. Do not alter the idempotency/prune paragraphs (the Mermaid dev-setup repoint is Part 3e).

### Breaking changes & migration

- **One-time migration:** users with an existing FULL marketplace clone get a single `remove` + `add --sparse` on their next actual upgrade (the `else` branch fires because `larch-logs/` is present); afterward every upgrade uses in-place `marketplace update`. Self-healing.
- **Idempotent fast path unchanged:** the "Already at latest stable release" early-exit performs no marketplace mutation, so always-up-to-date users migrate only when an actual upgrade next occurs. Intended.
- **No consumer-visible behavior change:** every runtime directory still ships (only `larch-logs/` and the dev-only `mermaid-lint/` are excluded). `/implement` Step 8's `.claude/skills/bump-version` still ships (`.claude` is in `LARCH_SPARSE_DIRS`).
- **Dev/CI workflow change:** Mermaid lint deps now live in `mermaid-lint/`; local devs run `(cd mermaid-lint && npm ci)` (or `npm install`); CI is repointed (Part 3d). `make lint-mermaid` and the `lint-mermaid` CI job behave identically otherwise.
- **Test removal is intentional:** the `/upgrade-larch` harnesses are deleted by request; `make lint` (including `test-harness-shards-coverage`) must stay green with no dangling references.

## Acceptance

- `make lint` passes with no new failures — covers `shellcheck` (every `$LARCH_SPARSE_DIRS` expansion carries `# shellcheck disable=SC2086`), `actionlint` (the `ci.yaml` edits), and `test-harness-shards-coverage` (confirms the removed targets leave no dangling shard/`.PHONY` references). No new test target is added.
- `git grep -n 'test-upgrade-larch'` returns nothing (Part 4 complete).
- Static, in `upgrade-larch.sh`: `LARCH_SPARSE_DIRS=".claude .claude-plugin .gemini .github agents docs hooks scripts skills tests"` defined once; `claude plugin marketplace update larch-local` present; `--sparse $LARCH_SPARSE_DIRS` present; the steady-state path has no unconditional `marketplace remove`+`add` (those appear only in the `else` branch and the update-failure fallback).
- Static: repo root has no `package.json` or `package-lock.json`; `mermaid-lint/package.json` and `mermaid-lint/package-lock.json` exist; `git grep -n 'node_modules/.bin/mmdc'` resolves only to `mermaid-lint/node_modules/.bin/mmdc`; no tracked file outside `mermaid-lint/` references root `package.json`/`package-lock.json` for the mermaid toolchain.
- Mermaid lint still works via the existing path: after `(cd mermaid-lint && npm ci)`, `scripts/lint-mermaid-fences.sh <a-changed.md>` runs (exit 0 on valid fences) — this exercises the existing lint, not a new test.
- `claude plugin marketplace add --help` lists `--sparse` (side-effect-free probe satisfying `.claude/rules/verify-external-tool-invocations.md`).
- Operator-verified manually on a real install (cannot run in CI — mutates marketplace state; note in the PR per the verify-external-tool-invocations rule): after one `/upgrade-larch`, the installed `~/.claude/plugins/cache/larch-local/larch/<version>/` contains no `larch-logs/`, no `node_modules/`, and no `package.json`; `~/.claude/plugins/marketplaces/larch-local/larch-logs` is absent; a second `/upgrade-larch` prints "Refreshing larch marketplace in place".

## Test plan
(no test plan section in plan-file)
