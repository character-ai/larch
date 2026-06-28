## Goal
Implement issue #5797: [IMPLEMENTING] [BUG] Cursor lanes pop up a Cursor.app GUI window during /implement (NO_OPEN_BROWSER).

## Implementation Plan
## Summary

During `/implement` (and other Cursor lanes), the Cursor desktop app's **"Composer 2.5" GUI window repeatedly pops up** while larch runs its Cursor agent. The window is launched by the `cursor-agent` CLI via macOS `open <deeplink>`, which focuses/launches `Cursor.app`. larch invokes `cursor agent -p …` in every Cursor lane but sets **no** environment variable to suppress the CLI's external-URL/deeplink opener. The fix is to export `NO_OPEN_BROWSER=1` (primary lever) into the `cursor-agent` child environment across all larch Cursor lanes. This is a UX/integration hardening change in larch's own launchers, not a security report.

## Original report

In the last several runs of `/implement`, Cursor started to pop up a Composer 2.5 CLI UI window (it did not do it before — specifically it was not happening yesterday; it just started today, 2026-06-28). This is unacceptable: the pop-up window keeps reappearing on each Cursor invocation, creating a poor user experience.

Operator observations during investigation:
- Quitting `Cursor.app` (CMD-Q, which prompted "OK to close all windows?", answered yes) **initially** stopped new windows. This confirms the pop-up is a **`Cursor.app` GUI window**, not an in-terminal TUI.
- However, a later invocation **reopened the window anyway, with `Cursor.app` quit** — so quitting the app does **not** durably suppress it. The deeplink open relaunches the quit app (see Root cause).

## Reproduction scenario

1. macOS host with `Cursor.app` **running** and the Cursor CLI installed (desktop app v3.7.36; `cursor-agent` v2026.06.26).
2. Run `/implement` on an issue so a Cursor implement/review lane spawns (`cursor agent -p …`).
3. Observe a `Cursor.app` "Composer 2.5" window pop up / gain focus during the Cursor lane, repeating on each invocation.

Notes:
- Not reliably reproducible offline: the trigger appears partly server-gated (see Root cause), so it may not fire on every account/day.
- Quitting `Cursor.app` does **not** durably help: the window reopened (with the app quit) on a later invocation, because `open cursor://…` relaunches the app.

## Expected behavior

larch's Cursor lanes run fully headless. No `Cursor.app` GUI window should open, gain focus, or pop up during `/implement`, `/review`, `/research`, negotiation, or CI lanes. Cursor's CLI is invoked with `-p` (print / non-interactive) precisely so it stays headless.

## Observed behavior

A `Cursor.app` "Composer 2.5" GUI window pops up repeatedly during Cursor lanes, despite `-p`. The window reappears on each Cursor invocation. It stops only when `Cursor.app` is quit entirely.

## Root cause analysis

**Verified:**
- larch invokes the agent as `["cursor", "agent", "-p", …]` in every Cursor lane (see Affected files).
- With `Cursor.app` installed, `cursor` resolves to `/usr/local/bin/cursor` (the Cursor.app editor CLI shim) because `/usr/local/bin` precedes `~/.local/bin` on `PATH`. On the `agent` subcommand the shim runs a version probe, may run `cursor-agent update`, exports `CURSOR_CLI_COMPAT=1` (a no-op — the `cursor-agent` bundle never reads it), then execs `~/.local/bin/cursor-agent`.
- The `cursor-agent` CLI bundle contains an "open external URL" helper that runs macOS `open <url>`. Decompiled shape:
  ```js
  function a(e){
    if (process.env.NO_OPEN_BROWSER) return false;   // suppressor #1
    if (lf()) return false;                            // suppressor #2 (SSH/headless detector)
    if (!l(e)) return false;
    try { return o(e), true } catch { return false }
  }
  function o(e){
    const { cmd, args } = findActualExecutable("open", [e]);  // macOS `open <url>`
    if (cmd === "open") throw new Error("Can't find a way to open browser");
    return { cmd, args };
  }
  ```
  Running `open` on a `cursor://` deeplink launches/focuses `Cursor.app` — the pop-up window. The operator confirmed quitting `Cursor.app` does **not** durably stop it: the window reopened on a later invocation with the app quit, because `open cursor://…` **relaunches** the quit app. This rules out "an already-running app surfacing CLI sessions" as the sole cause and confirms the CLI-initiated `open` is the trigger — which is exactly what `NO_OPEN_BROWSER=1` gates.
- The opener is suppressed when **either** `process.env.NO_OPEN_BROWSER` is set **or** `lf()` returns true. `lf()` is the SSH/headless detector, keyed off `CURSOR_AGENT_CLI_ASSUME_SSH` / `CURSOR_AGENT_ASSUME_SSH` / `CURSOR_CLI_ASSUME_SSH` / `CURSOR_ASSUME_SSH` / `CURSOR_AGENT_CLI_FORCE_SSH` / `CURSOR_AGENT_FORCE_SSH` / `CURSOR_CLI_FORCE_SSH` / `CURSOR_FORCE_SSH`.
- The bundle carries **server-controlled** deeplink configuration: `deeplink_controls`, `allow_public_deeplinks`, `prompt_deeplink_controls`, `command_deeplink_controls`.
- larch currently sets **neither** `NO_OPEN_BROWSER` **nor** any `*_SSH` variable anywhere (`grep` over `python/ skills/ scripts/ docs/` returns nothing). The Cursor child env is set in `cursor_auth_export_env()` and via `_temporary_env(name="CURSOR_CONFIG_DIR", …)`.
- Nothing in the local Cursor install changed on the day the symptom began: newest `cursor-agent` version dir is `2026.06.26` (installed Jun 26); `Cursor.app` is `3.7.36` (Jun 13); the `/usr/local/bin/cursor` shim is dated Mar 9.

**Inferred (not certain):**
- Because no local file changed but the behavior started on a specific day, the most likely trigger is a **server-side rollout of a deeplink** (`deeplink_controls` / `allow_public_deeplinks` are server-pushed), causing the CLI to begin calling `open cursor://…` to surface the Composer session in the desktop app. A secondary possibility is that the Jun 26 `cursor-agent` update introduced the behavior and it was simply first exercised that day. The exact trigger is not confirmed; the suppression below is robust regardless.

## Evidence

- Cursor emission sites (all `["cursor", "agent", "-p", …]`):
  - `python/larch/agents/agents.py:977` — presence probe
  - `python/larch/agents/agents.py:3003` — `run-negotiation-round`
  - `python/larch/agents/agents.py:4152` — `launch-cursor-ci`
  - `python/larch/agents/agents.py:5733` — `launch-cursor-implement`
  - `python/larch/review/review_and_fix.py:1830` — review fixer
  - `skills/research/references/validation-phase.md:102` — research validation lane (markdown template)
- `cursor` resolves to the editor shim: `which -a cursor` → `/usr/local/bin/cursor` (symlink to `/Applications/Cursor.app/Contents/Resources/app/bin/cursor`) before `~/.local/bin/cursor`. The standalone headless CLI is `~/.local/bin/cursor-agent`.
- Editor shim (`/usr/local/bin/cursor`) on `agent`: version-probe + `cursor-agent update` + `export CURSOR_CLI_COMPAT=1` + `exec ~/.local/bin/cursor-agent "$@"`.
- `cursor-agent --help`: documents `-p, --print` as the non-interactive lever and lists subcommand `agent`; the `login` command help notes "Set NO_OPEN_BROWSER to disable browser opening."
- Bundle scans (`~/.local/share/cursor-agent/versions/2026.06.26-7079533/*.js`): the `open`-via-`findActualExecutable("open", …)` helper gated by `NO_OPEN_BROWSER` + `lf()`; the `*_SSH` env list used by `lf()`; `deeplink_controls` / `allow_public_deeplinks` protobuf fields; `CURSOR_CLI_COMPAT` has **no** match (shim flag is a no-op).
- `grep` confirms larch sets neither `NO_OPEN_BROWSER` nor any `*_SSH` var.
- Cursor docs (cli/headless, cli/using) confirm `-p`/`--print` is the headless mechanism; community reports note `agent` became the primary command in a Jan 2026 update.
- Repo state: branch `main`, HEAD `a188e47e8`, larch `52.1.10`.

## Affected files

- `python/larch/agents/agents.py` — Cursor lanes at lines 977, 3003, 4152, 5733; Cursor child-env setup `cursor_auth_export_env()` (~line 776) and `_temporary_env(name="CURSOR_CONFIG_DIR", …)`; `run_external_agent` stdin handling (~line 1984).
- `python/larch/review/review_and_fix.py` — Cursor review fixer at line 1830.
- `skills/research/references/validation-phase.md` — research validation lane template emitting `cursor agent` (line 102).
- `python/test_launch_review.py`, `python/test_implement_dispatch.py`, `python/test_review_and_fix.py` — launcher harnesses that should assert the new env is exported (per `.claude/rules/launcher-argv-test-coverage.md`).
- `docs/installation-and-setup.md`, `docs/configuration-and-permissions.md` — document the `NO_OPEN_BROWSER` behavior for Cursor lanes.

## Suggested fix(es)

1. **Primary:** export `NO_OPEN_BROWSER=1` into the environment inherited by every `cursor-agent` child across all larch Cursor lanes. This gates the exact `open <url>` helper above, so no `Cursor.app` window is launched. Safe for larch: auth is via `CURSOR_API_KEY` / keychain preflight, never interactive login, so disabling browser/deeplink opening cannot break auth. Cleanest home: set it alongside the existing Cursor child-env setup (next to `cursor_auth_export_env()` and wherever `CURSOR_CONFIG_DIR` is set), plus `review_and_fix.py` and the `validation-phase.md` template. Apply to **all** lanes per `.claude/rules/external-tool-launcher-parity.md`.
2. **Defense-in-depth (optional):** also export `CURSOR_AGENT_FORCE_SSH=1` (or `CURSOR_ASSUME_SSH=1`) so `lf()` returns true (second suppressor). Risk: forcing SSH mode may alter other agent behavior; prefer `NO_OPEN_BROWSER` as the main lever and treat `*_SSH` as optional.
3. **Immediate mitigation until the fix lands (no larch change):** export `NO_OPEN_BROWSER=1` in the shell environment from which `/implement` is launched — the larch Cursor child inherits it and the opener is gated off. Note: quitting `Cursor.app` does **not** work (operator-confirmed — `open cursor://…` relaunches it).
4. **Minor parity nit (not the cause):** `run_external_agent` passes `stdin=None` for Cursor but `subprocess.DEVNULL` for Codex (`agents.py` ~line 1984). Redirecting Cursor stdin to `DEVNULL` would force non-interactive and close a parity gap, but it does **not** fix the GUI pop-up (the window comes from the `open` helper, not from TTY detection). Consider as a separate cleanup.

Add a regression assertion (per `.claude/rules/launcher-argv-test-coverage.md`) that each Cursor lane exports `NO_OPEN_BROWSER=1`, and update the docs noted above.

## Open questions

- Should `NO_OPEN_BROWSER=1` be unconditional for all larch Cursor lanes, or gated behind an env/flag for operators who *want* the desktop app to surface sessions? (Recommendation: unconditional — larch lanes are headless by contract.)
- Is `CURSOR_AGENT_FORCE_SSH` / `CURSOR_ASSUME_SSH` worth adding as defense-in-depth given the possible behavioral side effects of SSH mode, or is `NO_OPEN_BROWSER` alone sufficient?
- Confirm the exact trigger (server-side deeplink rollout vs the Jun 26 `cursor-agent` update). Not required to land the fix, but useful to record.

## Test plan
(no test plan section in plan-file)
