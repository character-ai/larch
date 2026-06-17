# Phantom untracked probe

**Consumer**: `/implement` orchestrator.
**Contract**: advisory untracked-file probe entrypoints, registry, and stdout KV parsing.
**When to load**: **MANDATORY — READ ENTIRE FILE** before parsing `PHANTOM_*` keys or changing phantom-probe call sites.

At selected `/implement` boundaries, detect non-ignored untracked files that appeared after the Step 0 tracking adoption session baseline. This is advisory only: phantoms are logged to Execution Issues, never cleaned automatically.

**Thin implementation** — shared logic lives in `${CLAUDE_PLUGIN_ROOT}/scripts/lib-phantom-probe.sh` (`phantom_probe_with_warn`; see `scripts/lib-phantom-probe.md`). Runtime entrypoints:

- **Combined (4 sites)** — post-rebase probe is bundled into `${CLAUDE_PLUGIN_ROOT}/scripts/rebase-checkpoint-probe.sh` for Steps **1.r**, **4.r**, **7.r**, and **7a.r** (uniform `<step-prefix>-post-rebase` tokens such as `1.r-post-rebase`; see `scripts/rebase-checkpoint-probe.md`). **Do not** duplicate `${CLAUDE_PLUGIN_ROOT}/scripts/check-phantom-dirty.sh` / `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" run-log append-entry` call blocks after those checkpoints — that would double-invoke the probe.
- **Bundled standalone tokens (2 sites)** — Step 2 post-dispatch uses `skills/implement/scripts/step-2-post-dispatch.sh`, which bundles the probe token `2-post-dispatch` with branch and optional SHA reads. Step 8+ pre-ship uses `skills/implement/scripts/step-8-ship.sh`, which bundles `phantom-probe-with-warn.sh --step 8-pre-ship` before the ship driver and redirects probe stdout away from driver JSON stdout.

**6 sites total** per run: four combined post-rebase probes (including the uniform `1.r-post-rebase` site) plus the two bundled standalone tokens above.

**Orchestrator parsing** — token-scan the probe tail for `PHANTOM_STATUS`, optional `PHANTOM_REASON`, `PHANTOM_COUNT`, `PHANTOM_PATHS_FILE`, and optional `PHANTOM_APPEND_WARN_ERROR` (warn-append failure already logged by the wrapper — treat as advisory telemetry). Do **not** `eval`/`source` captured lines.

**Probe locations (registry)**:
- After Step 2 dispatch returns on the external-implementer `STATUS=complete` path only: `skills/implement/scripts/step-2-post-dispatch.sh` bundles the `2-post-dispatch` probe with branch and optional SHA reads. The orchestrator always consumes `PHANTOM_*` before exit-code routing; branch comparison stays in SKILL.md. Do not probe when `STATUS=claude_fallback`; Claude-fallback implementation files are uncommitted until Step 4.
- After Step 1.r / 4.r / 7.r / 7a.r `rebase-checkpoint-probe.sh` returns on the success path: phantom handling is **inside** the wrapper (`1.r-post-rebase`, `4.r-post-rebase`, `7.r-post-rebase`, `7a.r-post-rebase`).
- Immediately before the active Step 8+ driver: `--step 8-pre-ship` inside `skills/implement/scripts/step-8-ship.sh`.

There is intentionally no post-Step-6 probe. When `FILES_CHANGED=true`,
review-created files are legitimately untracked until Step 7 commits them; a
post-Step-6 probe would false-positive. The post-Step-7.r probe covers the
committed review-fix state.
