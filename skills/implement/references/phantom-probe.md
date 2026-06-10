# Phantom untracked probe

**Consumer**: `/implement` orchestrator.
**Contract**: advisory untracked-file probe entrypoints, registry, and stdout KV parsing.
**When to load**: **MANDATORY — READ ENTIRE FILE** before parsing `PHANTOM_*` keys or changing phantom-probe call sites.

At selected `/implement` boundaries, detect non-ignored untracked files that appeared after the Step 0 tracking adoption session baseline. This is advisory only: phantoms are logged to Execution Issues, never cleaned automatically.

**Thin implementation** — shared logic lives in `${CLAUDE_PLUGIN_ROOT}/scripts/lib-phantom-probe.sh` (`phantom_probe_with_warn`; see `scripts/lib-phantom-probe.md`). Runtime entrypoints:

- **Combined (4 sites)** — post-rebase probe is bundled into `${CLAUDE_PLUGIN_ROOT}/scripts/rebase-checkpoint-probe.sh` for Steps **1.r**, **4.r**, **7.r**, and **7a.r** (uniform `<step-prefix>-post-rebase` tokens such as `1.r-post-rebase`; see `scripts/rebase-checkpoint-probe.md`). **Do not** duplicate `${CLAUDE_PLUGIN_ROOT}/scripts/check-phantom-dirty.sh` / `${CLAUDE_PLUGIN_ROOT}/scripts/append-execution-issue.sh` call blocks after those checkpoints — that would double-invoke the probe.
- **Standalone (2 sites)** — `phantom-probe-with-warn.sh --step <token>` (path: `${CLAUDE_PLUGIN_ROOT}/scripts/phantom-probe-with-warn.sh`) for **Step 2 post-dispatch** (`2-post-dispatch`) and **Step 8+ pre-ship** (`8-pre-ship`) only (`scripts/phantom-probe-with-warn.md`).

**6 sites total** per run: four combined post-rebase probes (including the uniform `1.r-post-rebase` site) plus the two standalone invocations above.

**Orchestrator parsing** — token-scan the probe tail for `PHANTOM_STATUS`, optional `PHANTOM_REASON`, `PHANTOM_COUNT`, `PHANTOM_PATHS_FILE`, and optional `PHANTOM_APPEND_WARN_ERROR` (warn-append failure already logged by the wrapper — treat as advisory telemetry). Do **not** `eval`/`source` captured lines.

**Probe locations (registry)**:
- After Step 2 dispatch returns on the external-implementer `STATUS=complete` path only: `--step 2-post-dispatch` via `phantom-probe-with-warn.sh`. Do not probe when `STATUS=claude_fallback`; Claude-fallback implementation files are uncommitted until Step 4. On the same `STATUS=complete` path, after this probe, the orchestrator runs the Section 2.2 post-dispatch branch assertion (`git-current-branch.sh` vs Step 1 `BRANCH_NAME`) before Step 3.
- After Step 1.r / 4.r / 7.r / 7a.r `rebase-checkpoint-probe.sh` returns on the success path: phantom handling is **inside** the wrapper (`1.r-post-rebase`, `4.r-post-rebase`, `7.r-post-rebase`, `7a.r-post-rebase`).
- Immediately before the active Step 8+ driver unless `LARCH_SHIP_PR_IMPL=bash` (then before `ship-pr.sh` first invocation): `--step 8-pre-ship` via `phantom-probe-with-warn.sh`.

There is intentionally no post-Step-6 probe. When `FILES_CHANGED=true`,
review-created files are legitimately untracked until Step 7 commits them; a
post-Step-6 probe would false-positive. The post-Step-7.r probe covers the
committed review-fix state.
