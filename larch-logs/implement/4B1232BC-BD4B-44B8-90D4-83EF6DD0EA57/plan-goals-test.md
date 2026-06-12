## Goal
Implement issue #3673: [IMPLEMENTING] sh-to-py B4: external-agent launcher framework\n\nPart of the sh-to-py bash-to-Python migration (umbrella tracking issue links all parts)..

## Implementation Plan
## Plan

## Plan

## Approach

- Treat `approach-synthesis.txt` as `NO_SKETCHES_CLASSIFIED_SIMPLE`.
- Use direct repo inspection only.
- Do not claim sketch agreement.
- Apply the **partial-retire pattern** from discussion round 1:
  - Retire executable B4 scripts and executable-specific `.md` and harness siblings.
  - Keep sourced-only libs in bash for surviving C-phase consumers.
  - Keep `scripts/external-tool-registry.sh` as a sourced compatibility artifact because live bash consumers still source it.
  - Keep `scripts/external-tool-registry.sh`, its `.md` sibling, and its sourced-contract harness out of `python/migrated-scripts.tsv` until source consumers are cut over.
  - Remove retired executable path literals from retained sourced artifacts and retained harnesses.
  - Add Python equivalents in `python/agents.py`, but do not add sourced-only lib files to `python/migrated-scripts.tsv`.
- Resolve monitoring with `subprocess.Popen` plus `wait(timeout=poll_interval)` loops.
  - Preserve progress messages, timeout kills, sentinel writes, and stderr-tail capture.
  - Preserve existing Cursor CI stall-monitor behavior.
  - No async framework is needed.
- Port the Darwin per-tool external serial lock into Python.
  - Preserve `external_serial_lock_acquire` and `external_serial_lock_release` semantics.
  - Preserve `LARCH_EXTERNAL_SERIAL_LOCK_*` behavior.
  - Wrap Codex CI, Cursor CI, and Codex-exec child spawn attempts with the same Darwin-only startup mutex.
- Port Claude subprocess context rendering protections exactly.
  - Preserve XML-escaped path attributes.
  - Preserve the untrusted-data preamble.
  - Preserve secret redaction before context is rendered.
  - Preserve body escaping so context bytes cannot become trusted prompt structure.
  - Prove no unredacted secret leaks into rendered context.
- Add `agent` CLI verbs. Use direct calls only:
  - `agent model-args`
  - `agent read-claude-model`
  - `agent cursor-auth-preflight`
  - `agent cursor-wrap-prompt`
  - `agent external-tool-registry`
  - `agent degraded-tools-gate`
  - `agent parse-codex-usage <events-jsonl>`
  - `agent run-external-agent`
  - `agent launch-codex-ci`
  - `agent launch-codex-exec`
  - `agent launch-cursor-ci`
  - `agent launch-claude-ci`
  - `agent launch-claude-review`
  - `agent launch-claude-subprocess`
- Preserve machine contracts:
  - fd-3 quiet output.
  - `LAUNCHER_EXIT`, `LAUNCHER_FAILURE_CLASS`, and `.done` sidecars after validation succeeds and trap setup is safe.
  - Side-effect-free failures for invalid argv, unsafe output paths, unsafe stderr sinks, invalid timeouts, and invalid inner sentinels.
  - Missing child executables are post-validation launch failures, not side-effect-free validation failures.
  - `.meta` keys and `CMD_JSON` shape.
  - `STDERR_SINK` metadata when `--stderr-sink` is set.
  - Codex-exec outer retry metadata shape.
  - Codex-exec public `.done` promotion ordering.
  - `INPUT`, `CACHED_INPUT`, `OUTPUT`, `TOTAL` usage KVs.
  - `DEGRADED_*` explanation block sentinels.
  - line-token argv output from model args.
  - Cursor wrap prompt has no trailing newline.
- Preserve launcher-specific contracts:
  - Cursor CI private `CURSOR_CONFIG_DIR` setup, cleanup, sidecar emission, diagnostics, stall detection, and child-first kill behavior.
  - Claude scoped read-only mode with `--read-tools` and `--read-tools-add-dir`.
  - Claude subprocess context redaction and escaping protections.
  - Codex-exec auth and model-args preflight wrapper-exit behavior.
  - Codex-exec `--trusted-instructions-file` behavior, including validation and temporary `CODEX_HOME` config merge.
  - run-external-agent launch-time health gate behavior and opt-out semantics.
  - run-external-agent failure carrier before `.done` ordering.
- Call B2 and B3 Python functions directly for timing, token usage, and vendor failure diagnostics.
- Update every direct bash, Python, skill, test, harness, retained sibling doc, and operator-facing doc caller that invokes a retired executable.
- Update retained tests and fixtures that stub or assert retired launcher scripts.
- Keep sourced bash function names stable for surviving C-phase consumers.
- Add minimal internal substitutions in retained sourced libs when they call retired helper executables.
- Add collector retry compatibility for the new Python launcher entrypoints.
- Extend codex-exec auth lint so Python call sites are scanned fail-closed.
- Sweep all tracked files scanned by `lint-retired-scripts`, including `.claude/`, docs, rules, comments, contract prose, tests, retained harness docs, CI, and Makefile.
- Post C-phase issue comments for #3676, #3677, #3678, #3680, #3682, and #3684 that each phase owns sourced-lib retirement for its final consumers, including `external-tool-registry.sh`.

## Files to modify/create

### UPDATED: python/agents.py

- Extend the existing launcher module rather than adding a new module.
- Add dataclasses for launcher inputs and outputs:
  - model arg result.
  - auth verdict.
  - run-external-agent result.
  - usage totals.
  - degraded-tools result.
  - launch result.
  - serial-lock state.
- Port executable behavior:
  - model arg resolution and validation.
  - Claude model env fallback.
  - external tool registry helpers.
  - Cursor auth preflight, env normalization, Darwin keychain pre-read.
  - Cursor max-mode prompt wrapper.
  - degraded-tools gate classifier and explanation composer.
  - Codex JSONL usage parsing with stdlib `json`; require the positional events JSONL path.
  - failed stderr-tail selection, redaction, byte cap, and carrier composition hooks.
  - run-external-agent monitored wrapper.
  - run-external-agent `--stderr-sink` parsing, validation, and `STDERR_SINK` metadata.
  - run-external-agent launch-time health gate.
  - run-external-agent trap-equivalent failure ordering.
  - run-external-agent success ordering.
  - Codex, Cursor, and Claude CI launchers.
  - Darwin-only external serial lock around Codex and Cursor spawn attempts.
  - Cursor CI private config-dir isolation, cleanup, stall diagnostics, sidecar emission, and child-first kill.
  - Codex exec launcher.
  - Codex-exec `--trusted-instructions-file` validation and temporary `CODEX_HOME` config merge.
  - Codex-exec trusted-instructions prepending and stripping existing top-level `instructions` from copied `config.toml`.
  - Codex-exec post-child sequence: keep public `.done` absent during retries and post-processing; record timing and usage; append outer metadata; promote `.inner.done` to `.done`; emit `LAUNCHER_EXIT`; then emit `OUTPUT`.
  - Claude review and Claude subprocess launchers.
  - Claude subprocess scoped read-only `--read-tools` and `--read-tools-add-dir`.
  - Claude subprocess context rendering protections: XML-escaped path attributes, untrusted-data preamble, secret redaction, escaped body text, and no unredacted secret leakage.
- Keep existing failure classification and waterfall helpers.
- Replace current `build_launch_argv` shell-script argv output with Python CLI argv output for internal B4 callers.
- Keep compatibility behavior for sourced bash libs by not changing their exported function names here.
- Validate argv, output path, stderr sink, timeout, and inner sentinel before artifact cleanup, trap setup, `.meta`, `.diag`, `.failure-diag`, or `.done` writes.
- Treat missing child executables in `agent run-external-agent` as post-validation launch failures:
  - catch `FileNotFoundError`.
  - emit launch failure diagnostics.
  - write `.meta`, `.diag`, `.failure-diag`, and `.done` in the established order.
  - use the existing shell-compatible launch-failure rc, likely 127.
  - do not spawn retryable children after the failed `Popen`.
- Keep command-path preflights only where the current shell launcher already preflights them.
- Port health gate behavior:
  - unhealthy Codex exits 7.
  - unhealthy Cursor exits 8.
  - unhealthy tools do not spawn child commands.
  - diagnostics include health-probe text.
  - `.done` records the health-gate rc.
  - timeout opt-out `0` disables the gate.
  - unparseable probe output fails open.
- Preserve Codex-exec preflight behavior:
  - auth-prep and model-args preflight failures make the wrapper process exit 0.
  - fd-3 emits `LAUNCHER_EXIT` from the failed helper.
  - stdout emits `OUTPUT`.
  - output file, `.diag`, `.meta`, and `.done` are written.
  - `.diag` includes `STATUS=FAILED` and helper rc.
  - `.meta` uses `CMD_JSON=[]` for preflight failures.
  - preserve prompt sidecar ordering from the current shell path.
- For `agent launch-codex-exec`, append the same outer retry block with these post-cutover values:
  - `OUTER_LAUNCHER=agent launch-codex-exec`
  - `OUTER_LAUNCHER_PROMPT_FILE=${output}.prompt`
  - `OUTER_LAUNCHER_WORKDIR=<workdir>`
  - `OUTER_LAUNCHER_KIND=codex-exec`
  - `OUTER_LAUNCHER_SANDBOX=<full-auto|read-only>`
  - `OUTER_LAUNCHER_WITH_EFFORT=<true|false>`
  - `OUTER_LAUNCHER_USAGE_LABEL=<label>`
  - `OUTER_LAUNCHER_TIMING_KIND=<kind>`
  - `OUTER_LAUNCHER_ADD_DIRS_JSON=<compact JSON array>`
- Keep `OUTER_LAUNCHER_PROMPT_FILE=${output}.prompt`.
- Serialize `OUTER_LAUNCHER_ADD_DIRS_JSON` compactly with stdlib JSON.

### UPDATED: python/cli.py

- Register the `agent` domain verbs listed above.
- Register `agent parse-codex-usage` with a required positional events JSONL path.
- Keep lazy import behavior.
- Do not import `agents` at module import time.

### UPDATED: python/checks.py

- Replace retired launcher executable references with direct `agent` CLI verbs or imported `python.agents` functions.
- Repoint dispatch paths to:
  - `agent run-external-agent`
  - `agent launch-codex-exec`
  - `agent cursor-wrap-prompt`
- Drop executable-bit guards for deleted launcher scripts.
- Preserve existing env override seams and status labels.

### UPDATED: python/ci_monitor.py

- Replace CI launcher shell paths with `agent launch-*-ci` calls.
- Preserve waterfall status, retry, timeout, stall, and failure-log behavior.
- Keep timing and failure-log contracts unchanged.

### UPDATED: python/rebase.py

- Replace rebase helper invocations of retired launchers with matching `agent` CLI verbs.
- Preserve conflict metadata, env overrides, and failure classification behavior.

### UPDATED: python/voting.py

- Replace voting retry and launch paths that point at retired shell launchers.
- Route Claude review through `agent launch-claude-review`.
- Route Codex execution through `agent launch-codex-exec`.
- Preserve voter output grammar and retry metadata.

### UPDATED: python/lint_codex_exec_auth.py

- Extend scanning to Python launcher call sites as well as shell and markdown surfaces.
- Allowlist only the wired `python/agents.py` Codex-exec launch surface plus intentional tests.
- Refresh allowlists for the post-cutover Python surface.
- Replace guidance that recommends deleted shell launchers with `python3 python/cli.py agent launch-codex-exec` or surviving wired wrapper entrypoints.
- Keep raw `codex exec` violations fail-closed outside allowlisted wired launch surfaces.

### UPDATED: python/test_agents.py

- Expand pytest coverage to replace retired harnesses.
- Build retired path strings programmatically when a test needs a path-like fixture.
- Cover:
  - model defaults, plugin-option fallback, blank and control-character rejection.
  - Codex effort fallback warning.
  - Cursor auth env trimming and unset behavior.
  - Darwin keychain pre-read through injected runner hooks.
  - Darwin external serial lock acquisition and release sequencing through injected hooks for Codex CI, Cursor CI, and Codex-exec.
  - Cursor wrap prompt byte shape.
  - degraded-tools valid states and empty-presence diagnostics.
  - parse-codex-usage required events-file argument, nested usage, zero usage, malformed JSON, and cached greater than input fail-closed.
  - run-external-agent `.meta`, `.done`, timeout, stdout capture modes, stdin `/dev/null` for Codex, tool label sanitization, stale artifact cleanup, and stderr-tail carrier behavior.
  - run-external-agent `--stderr-sink` acceptance, unsafe-sink rejection before side effects, and `STDERR_SINK` metadata.
  - run-external-agent failure carrier ordering.
  - run-external-agent success cleanup ordering for stale `.failure-diag`.
  - run-external-agent health gate matrix.
  - side-effect-free validation failures.
  - missing child executable behavior after valid output path, trap setup, `.meta`, `.diag`, `.failure-diag`, and `.done`.
  - launcher argv construction, prompt sidecars, auth retries, timing record calls, usage capture, and failure classification.
  - Codex-exec `--trusted-instructions-file` validation, trusted-instruction prepending, temporary config merge, and stripping copied top-level config instructions.
  - Codex-exec auth-prep and model-args preflight failures with process rc 0, fd-3 `LAUNCHER_EXIT`, stdout `OUTPUT`, output file, `.diag`, `.meta CMD_JSON=[]`, `.done`, and prompt sidecar ordering.
  - Codex-exec post-child ordering.
  - Codex-exec outer metadata fields, compact `OUTER_LAUNCHER_ADD_DIRS_JSON`, and `${output}.prompt` sidecar.
  - Cursor CI private config-dir setup, cleanup, stall monitor diagnostics, child-first kill, and sidecar emission.
  - Claude subprocess path canonicalization, symlink rejection, context caps, model token validation, JSON envelope promotion, dirty-tree sidecar shape, `--read-tools`, `--read-tools-add-dir`, session-root validation, and `CMD_JSON` allowlist behavior.
  - Claude subprocess context rendering: XML-escaped path attributes, untrusted-data preamble, secret redaction, body escaping, and no unredacted secret leakage.
  - waterfall compatibility after direct Python launcher calls.

### UPDATED: python/test_checks.py

- Add or update coverage for Python check dispatch paths.
- Assert no deleted launcher path is required for preflight, retry, or argv construction.
- Preserve existing check result contracts.

### UPDATED: python/test_ci_monitor.py

- Add or update coverage for CI waterfall launcher selection.
- Assert CI roles call `agent launch-*-ci` or direct Python equivalents.
- Preserve retry, stall, and failure-log assertions.

### UPDATED: python/test_rebase.py

- Add or update coverage for rebase conflict launcher calls.
- Assert no retired executable path is required.

### UPDATED: python/test_voting.py

- Add or update coverage for voting launch and retry call construction.
- Assert Claude and Codex retries use new `agent` CLI entrypoints.

### UPDATED: python/test_lint_codex_exec_auth.py

- Update fixtures and expected errors for the Python `agent launch-codex-exec` surface.
- Add Python source fixtures with raw `codex exec` calls and assert the lint fails closed unless the call is the wired `python/agents.py` surface or intentional test fixture.
- Build deleted launcher path strings programmatically only when testing stale-reference detection.
- Keep coverage for raw unwired `codex exec` failures.

### UPDATED: python/migrated-scripts.tsv

- Add retired executable scripts and sibling docs/harnesses with the B4 issue id.
- Include executable B4 scripts:
  - `scripts/cursor-auth-flags.sh`
  - `scripts/cursor-wrap-prompt.sh`
  - `scripts/agent-model-args.sh`
  - `scripts/read-claude-model.sh`
  - `scripts/launch-codex-ci.sh`
  - `scripts/launch-codex-exec.sh`
  - `scripts/launch-cursor-ci.sh`
  - `scripts/launch-claude-ci.sh`
  - `scripts/launch-claude-review.sh`
  - `scripts/launch-claude-subprocess.sh`
  - `scripts/run-external-agent.sh`
  - `scripts/parse-codex-usage.sh`
  - `scripts/degraded-tools-gate.sh`
- Include matching deleted `.md` siblings and deleted executable-specific test harnesses.
- Do not add sourced-only libs:
  - `scripts/lib-external-launcher-common.sh`
  - `scripts/lib-codex-launcher-common.sh`
  - `scripts/lib-cursor-launcher-common.sh`
  - `scripts/lib-cursor-auth.sh`
  - `scripts/lib-failed-agent-stderr-tail.sh`
  - `scripts/external-tool-registry.sh`
- Do not add `scripts/external-tool-registry.sh`, its `.md` sibling, or its sourced-contract harness until source consumers are retired or ported.

### UPDATED: scripts/lib-external-launcher-common.sh

- Keep exported function names unchanged.
- Replace internal `parse-codex-usage.sh` helper calls with the full Python parser invocation:
  - `usage_blob=$(python3 "$plugin_root/python/cli.py" agent parse-codex-usage "$events_file" 2>"$usage_err") || usage_blob=""`
- Preserve stderr capture and existing usage KV parsing.
- Preserve stdout, stderr, fd-3, and usage KV contracts.
- Preserve sourced behavior for current C-phase consumers.
- Keep retained sourced tests pointed at the Python parser path.

### UPDATED: scripts/lib-external-launcher-common.md

- Update sourced-lib contract prose to reference the Python parser with the required events JSONL path.
- Reference the Python codex-exec retry entrypoint.
- Document retained sourced compatibility status.
- Remove live invocation guidance for deleted executable paths.

### UPDATED: scripts/test-lib-external-launcher-common.sh

- Replace stubs and assertions for `scripts/parse-codex-usage.sh` with `python3 "$PLUGIN_ROOT/python/cli.py" agent parse-codex-usage "$events_file"`.
- Assert stderr capture through `2>"$usage_err"` and fallback to empty `usage_blob` on parser failure.
- Update fail-closed diagnostics expectations to match Python parser wording where observable.
- Update codex-exec outer metadata assertions for `OUTER_LAUNCHER=agent launch-codex-exec`.
- Keep sourced-contract coverage for retained bash functions.

### UPDATED: scripts/test-lib-external-launcher-common.md

- Update harness contract prose for the Python parser, required events path, stderr capture, and post-cutover codex-exec outer metadata.

### UPDATED: scripts/lib-cursor-launcher-common.sh

- Keep exported function names unchanged.
- Replace internal `agent-model-args.sh` helper calls exactly with `python3 "$plugin_root/python/cli.py" agent model-args --tool cursor --with-effort`.
- Derive a local plugin root from `PLUGIN_ROOT`, then `CLAUDE_PLUGIN_ROOT`, then the library location so sourced callers under `set -u` do not require predefining `PLUGIN_ROOT`.
- Preserve Cursor model arg output, effort fallback, and caller contracts.
- Preserve sourced behavior for current C-phase consumers.

### UPDATED: scripts/lib-cursor-auth.md

- Replace live `cursor-auth-flags.sh` references with `agent cursor-auth-preflight`.
- Preserve the no-argv auth contract and Darwin preflight semantics.

### UPDATED: scripts/test-lib-cursor-auth.sh

- Repoint retained cursor auth tests from `scripts/cursor-auth-flags.sh` to `python3 "$REPO_ROOT/python/cli.py" agent cursor-auth-preflight`.
- Preserve rc and stdout contracts.
- Keep Darwin pre-read and empty-key cases.

### UPDATED: scripts/test-lib-cursor-auth.md

- Update harness contract prose for `agent cursor-auth-preflight`.

### UPDATED: scripts/external-tool-registry.sh

- Keep the file sourced-only and keep exported compatibility functions stable.
- Replace retired script path values with Python agent CLI descriptors or importable registry values.
- Avoid deleted launcher path literals in live registry output.
- Keep current source consumers working.

### UPDATED: scripts/external-tool-registry.md

- Update retained registry contract prose to reference `python3 "$PLUGIN_ROOT/python/cli.py" agent external-tool-registry` and per-tool `agent` verbs.
- Remove live invocation examples for deleted launcher scripts.

### UPDATED: scripts/test-external-tool-registry.sh

- Exercise the new Python registry function or `python3 python/cli.py agent external-tool-registry`.
- Replace cases that executed retired helpers.
- Repoint the per-tool model-args probe from `scripts/agent-model-args.sh --tool "$tool"` to `python3 "$REPO_ROOT/python/cli.py" agent model-args --tool "$tool"`.
- Add `--with-effort` for Codex probe cases only when current parity requires it.
- Build any retired path fixture strings programmatically when testing stale-reference behavior.

### UPDATED: scripts/test-external-tool-registry.md

- Update harness contract prose for the retained sourced registry plus Python registry and model-args entrypoints.

### UPDATED: scripts/collect-agent-results.sh

- Keep the collector in bash for this phase.
- Replace retry execution through `run-external-agent.sh` with `python3 "$PLUGIN_ROOT/python/cli.py" agent run-external-agent`.
- Replay codex-exec outer retries through `python3 "$PLUGIN_ROOT/python/cli.py" agent launch-codex-exec`.
- For `OUTER_LAUNCHER_KIND=codex-exec`, accept post-cutover `OUTER_LAUNCHER=agent launch-codex-exec`.
- Accept and forward `STDERR_SINK` from `.meta` through the Python retry path.
- Accept legacy codex-exec metadata from old `.meta` fixtures without requiring the deleted shell launcher file to exist.
- Keep `launch-review.sh` review outer metadata on the existing canonical shape.
- Preserve validation for `.meta`, `CMD_JSON`, sidecars, empty-output retry recovery, prompt sidecars, workdir, sandbox, effort, usage label, timing kind, add-dir JSON, and stderr sink.
- Do not port the whole collector in B4.
- Keep `source scripts/external-tool-registry.sh` working because the registry remains retained.

### UPDATED: scripts/collect-agent-results.md

- Replace live retired launcher references with `python3 "$PLUGIN_ROOT/python/cli.py" agent run-external-agent` and `agent launch-codex-exec`.
- Document `OUTER_LAUNCHER=agent launch-codex-exec` as the post-cutover codex-exec retry shape.
- Preserve historical references only where clearly marked as legacy fixture compatibility.
- Document `STDERR_SINK` retry forwarding.

### UPDATED: scripts/test-collect-agent-results.sh

- Update codex-exec outer retry fixtures for `OUTER_LAUNCHER=agent launch-codex-exec`.
- Keep legacy fixture coverage where needed without requiring the deleted shell launcher to exist.
- Preserve empty-output retry assertions.

### UPDATED: scripts/test-collect-agent-retry.sh

- Update fail-closed and replay assertions for Python codex-exec metadata.
- Assert `OUTER_LAUNCHER_ADD_DIRS_JSON` round trips through the Python launcher replay path.
- Assert `STDERR_SINK` metadata round trips through the Python run-external-agent replay path.
- Preserve review outer retry coverage.

### UPDATED: scripts/launch-review.sh

- Replace direct calls to retired executables with `python3 "$PLUGIN_ROOT/python/cli.py" agent ...`.
- Use argv arrays for Python agent invocations rather than single executable-path variables.
- Preserve existing codex model-args preflight sidecar text, including `FAILURE_REASON=agent-model-args.sh failed (exit ...)`, unless `scripts/test-launch-review.sh` is updated to pin an intentional new diagnostic.
- Keep sourcing current bash libs.
- Preserve Codex and Cursor review posture exactly.
- Preserve retry, sentinel, empty response, and dirty-tree behavior.

### UPDATED: scripts/launch-review.md

- Replace live retired launcher references with Python `agent` CLI verbs.
- Preserve launch-review contract prose and reviewer posture semantics.
- Mark old script-path references as historical only if still needed for legacy fixture discussion.

### UPDATED: scripts/test-launch-review.sh

- Update stubs and assertions for the Python `agent` launch surface.
- Cover codex model-args preflight failure diagnostics and sidecar text.
- Preserve retry, sentinel, empty response, and dirty-tree assertions.
- Build deleted launcher path fixture strings programmatically only when testing stale-reference behavior.

### UPDATED: scripts/lint-fix-loop.sh

- Define or derive `PLUGIN_ROOT` before sourcing retained cursor launcher libs.
- Replace `run-external-agent.sh`, `launch-codex-exec.sh`, and `cursor-wrap-prompt.sh` references with `agent` CLI verbs.
- Replace any `[[ -x "$RUN_EXTERNAL_AGENT_SH" ]]` style guard with a `[[ -f "$PY_CLI" ]]` readability/existence check.
- Invoke run-external-agent, codex-exec, and cursor-wrap-prompt as Python argv arrays.
- Keep existing fallback and status labels.

### UPDATED: scripts/lint-fix-loop.md

- Replace live retired launcher references with Python `agent` CLI verbs.
- Preserve fallback, status-label, and repair-loop contract prose.

### UPDATED: scripts/test-lint-fix-loop.sh

- Update fixtures and grep assertions for the Python `agent` launch surface.
- Remove fixture copies of retired executable scripts.
- Preserve fallback, sidecar, and token diagnostics assertions.

### UPDATED: scripts/dispatch-plan-voters.sh

- Replace `launch-claude-review.sh` with `agent launch-claude-review`.
- Keep sentinel waiting and warning capture behavior.

### UPDATED: scripts/dispatch-plan-voters.md

- Replace live `launch-claude-review.sh` references with `python3 "$PLUGIN_ROOT/python/cli.py" agent launch-claude-review`.
- Preserve sentinel, warning capture, and voter-output contract prose.

### UPDATED: scripts/test-dispatch-plan-voters.sh

- Extend existing `python/cli.py` stubs to handle `agent launch-claude-review`.
- Update assertions from deleted launcher paths to the Python `agent` surface.
- Preserve sentinel, warning capture, and voter-output assertions.

### UPDATED: scripts/run-negotiation-round.sh

- Replace model args and cursor prompt wrapper calls with `agent` CLI verbs.
- Keep probe semantics with no effort unless current caller asks for effort.

### UPDATED: scripts/run-negotiation-round.md

- Replace live `agent-model-args.sh` and `cursor-wrap-prompt.sh` references with matching Python `agent` CLI verbs.
- Preserve negotiation-round probe and prompt-wrapper contract prose.

### UPDATED: scripts/dispatch-code-voters.sh

- Replace `launch-claude-review.sh` with `agent launch-claude-review`.
- Keep voter output and failure metadata contracts.

### UPDATED: scripts/dispatch-code-voters.md

- Replace live `launch-claude-review.sh` references with `python3 "$PLUGIN_ROOT/python/cli.py" agent launch-claude-review`.
- Preserve voter output and failure metadata contract prose.

### UPDATED: scripts/test-dispatch-code-voters.sh

- Extend existing `python/cli.py` stubs to handle `agent launch-claude-review`.
- Update assertions from deleted launcher paths to the Python `agent` surface.
- Preserve voter output and failure metadata assertions.

### UPDATED: scripts/launch-codex-drafter.sh

- Replace `launch-codex-exec.sh` with `agent launch-codex-exec`.
- Preserve `--trusted-instructions-file` forwarding.
- Preserve read-only sandbox and repo `--add-dir` behavior.

### UPDATED: scripts/launch-codex-drafter.md

- Update live invocation prose and env seams for `agent launch-codex-exec`.
- Document that `--trusted-instructions-file` remains supported by the Python launcher.
- Preserve wrapper contract details.

### UPDATED: scripts/ship-pr.sh

- Replace CI launcher invocations with `agent launch-*-ci`.
- Preserve resolve-conflict role, failure-log redaction, waterfall order, and conflict CSV validation.

### UPDATED: scripts/ship-pr.md

- Replace live CI launcher script references with Python `agent launch-*-ci` verbs.
- Preserve ship-pr waterfall and conflict-fixer contract prose.

### UPDATED: scripts/check-reviewers.sh

- Replace model args and cursor prompt wrapper calls with `agent` CLI verbs.
- Preserve binary-found and runtime-present keys consumed by session setup and degraded-tools gate.

### UPDATED: scripts/check-reviewers.md

- Replace live `agent-model-args.sh`, `cursor-wrap-prompt.sh`, and degraded gate references with matching Python `agent` CLI verbs.
- Preserve Step 0 availability and degraded posture contract prose.

### UPDATED: scripts/dispatch-with-waterfall.sh

- Replace `launch-claude-review.sh` with `agent launch-claude-review`.
- Keep sourced libs and waterfall control flow.

### UPDATED: scripts/dispatch-with-waterfall.md

- Replace live `launch-claude-review.sh` references with Python `agent launch-claude-review`.
- Preserve waterfall control-flow contract prose.

### UPDATED: scripts/launch-codex-implement.sh

- Make only minimal executable-path substitutions:
  - `agent-model-args.sh` to `agent model-args`.
  - `run-external-agent.sh` to `agent run-external-agent`.
  - `parse-codex-usage.sh` to `agent parse-codex-usage "$events_file"`.
- Invoke Python agent verbs as argv arrays.
- Preserve any stable diagnostic text that retained implementer harnesses intentionally pin, or update those harnesses to stable post-cutover tokens.
- Do not rewrite implementer manifest logic.

### UPDATED: scripts/launch-codex-implement.md

- Update token parsing prose to reference `agent parse-codex-usage <events-jsonl>`.
- Update model-args and run-external-agent prose to reference Python `agent` verbs.
- Preserve implementer manifest contract prose.

### UPDATED: scripts/launch-cursor-implement.sh

- Make only minimal executable-path substitutions:
  - `cursor-wrap-prompt.sh` to `agent cursor-wrap-prompt`.
  - `run-external-agent.sh` to `agent run-external-agent`.
- Invoke Python agent verbs as argv arrays.
- Preserve any stable diagnostic text that retained implementer harnesses intentionally pin, or update those harnesses to stable post-cutover tokens.
- Do not rewrite implementer manifest logic.

### UPDATED: scripts/scout-dynamic-archetypes.sh

- Replace `launch-claude-subprocess.sh` with `agent launch-claude-subprocess`.
- Preserve scout archetype output and failure metadata contracts.

### UPDATED: scripts/scout-dynamic-archetypes.md

- Replace live `launch-claude-subprocess.sh` references with Python `agent launch-claude-subprocess`.
- Preserve scout archetype output and failure metadata contract prose.
- Mention preserved context redaction and untrusted-data rendering protections where subprocess context is described.

### UPDATED: scripts/relevant-checks.sh

- Retarget changed-file mappings for retired B4 scripts and deleted harnesses to `python/test_agents.py` or retained sourced harnesses only.
- Drop routes that emit deleted executable-specific harness targets.
- Keep mappings for retained sourced-contract harnesses that still exist.
- Add mappings for retained dispatch, launch-review, scout, design, implementer, review-and-fix, and validate-plan-command harnesses that still need post-cutover assertions.
- Preserve pre-commit, pin verifier, and agent-lint behavior.

### UPDATED: scripts/relevant-checks.md

- Update routing contract prose for B4 retired launcher coverage.
- Document pytest replacement for deleted launcher harnesses.
- Document retained harness coverage that still runs after the cutover.

### UPDATED: scripts/test-relevant-checks.sh

- Update expected relevant targets for retired B4 launcher paths.
- Assert deleted harness targets are not emitted.
- Assert retained post-cutover harness targets are still emitted where appropriate.
- Preserve zero-phase, pre-commit, and agent-lint assertions.

### UPDATED: scripts/test-relevant-checks.md

- Update branch coverage prose for B4 mappings.

### UPDATED: scripts/test-token-vendor-scrapers.sh

- Repoint Codex usage parsing calls from `scripts/parse-codex-usage.sh` to `python3 "$REPO_ROOT/python/cli.py" agent parse-codex-usage "$events_file"`.
- Keep existing KV assertions for Codex usage, Cursor usage extraction, malformed JSON fallback, and total calculation.

### UPDATED: scripts/test-token-vendor-scrapers.md

- Update harness contract prose for the Python parser and required events JSONL argument.

### UPDATED: scripts/test-design-structure.sh

- Update contains pins that reference retired degraded gate or launcher paths.
- Point pins at Python `agent` CLI verbs or surviving wrappers.

### UPDATED: scripts/test-implement-structure.sh

- Update contains pins that reference retired degraded gate or launcher paths.
- Preserve Step 0 degraded gate assertions with the new Python CLI invocation.

### UPDATED: scripts/test-research-structure.sh

- Update Codex launcher pins to the new `agent launch-codex-exec` invocation.
- Preserve research lane structure assertions.

### UPDATED: skills/design/scripts/dispatch-plan-review-panel.sh

- Replace retired launcher paths with `agent` CLI verbs.
- Route Claude review through `agent launch-claude-review`.
- Route Codex execution through `agent launch-codex-exec`.
- Preserve panel output and sentinel contracts.

### UPDATED: skills/design/scripts/decompose-panel-dispatch.sh

- Replace retired launcher paths with `agent` CLI verbs.
- Preserve decomposition output grammar and retry behavior.

### UPDATED: skills/design/scripts/auto-fix-plan-commands.sh

- Replace retired launcher paths with `agent` CLI verbs.
- Preserve command-fix output grammar.

### UPDATED: skills/design/scripts/auto-fix-plan-commands.md

- Update launcher seam names and examples for `agent launch-codex-exec` and `agent run-external-agent`.
- Preserve offline harness contract prose.

### UPDATED: skills/design/scripts/revise-plan-with-waterfall.sh

- Replace retired launcher paths with `agent` CLI verbs.
- Preserve waterfall role order, failure metadata, and final plan grammar.

### UPDATED: skills/design/scripts/design-step0-degraded.sh

- Replace degraded gate shell references with `agent degraded-tools-gate`.
- Preserve explicit presence flags and degraded posture semantics.

### UPDATED: skills/design/scripts/test-validate-plan-commands.sh

- Update stubs, allowlists, help-probe logic, and expected diagnostics for the Python `agent` launcher surface.
- Repoint live launcher expectations to `agent` CLI verbs or surviving wrappers.
- Preserve validate-plan-command output grammar and regression expectations.

### UPDATED: skills/design/scripts/fixtures/validate-plan-commands/launch-context-plan.md

- Repoint fixture launcher references to post-B4 `agent` CLI verbs or surviving wrappers.
- Avoid deleted executable path literals except in explicitly non-live stale-reference test data.

### UPDATED: skills/design/references/dialectic-execution.md

- Replace dialectic runtime references to deleted launcher scripts with Python `agent` CLI verbs.
- Use `agent launch-codex-exec` for Codex judges.
- Use `agent run-external-agent` where the dialectic flow needs the monitored external-agent wrapper.
- Preserve HARD dialectic flow contracts and fallback semantics.

### UPDATED: skills/review-and-fix/scripts/review-and-fix.sh

- Replace `run-external-agent.sh`, `launch-codex-exec.sh`, `cursor-wrap-prompt.sh`, and `agent-model-args.sh` references with matching `agent` CLI verbs.
- Replace monolithic path variables with argv arrays:
  - `RUN_EXTERNAL_AGENT_CMD=(python3 "$PY_CLI" agent run-external-agent)`.
  - `CODEX_EXEC_CMD=(python3 "$PY_CLI" agent launch-codex-exec)`.
  - `CURSOR_WRAP_PROMPT_CMD=(python3 "$PY_CLI" agent cursor-wrap-prompt)`.
  - `CODEX_MODEL_ARGS_CMD=(python3 "$PY_CLI" agent model-args --tool codex --with-effort)`.
- Replace executable-bit preflights such as `[[ -x "$RUN_EXTERNAL_AGENT_SH" ]]` with `[[ -f "$PY_CLI" ]]`, matching the existing `WRITE_TALLY_CMD` style.
- Preserve review-and-fix role labels, fallback behavior, and output contracts.

### UPDATED: skills/review-and-fix/scripts/test-review-and-fix.sh

- Update stubs and grep expectations for the Python `agent` launch surface.
- Replace assertions that require `parse-codex-usage.sh`, `run-external-agent.sh`, `cursor-wrap-prompt.sh`, or `agent-model-args.sh` in wrapper logs or sidecars.
- Assert argv-array invocation and `PY_CLI` readability preflight behavior.
- Preserve review-and-fix fallback, output, tally, sidecar, and stderr-tail assertions.

### UPDATED: skills/implement/scripts/step-0-degraded-gate.sh

- Replace degraded gate shell references with `agent degraded-tools-gate`.
- Preserve explicit presence flags and Step 0 status output.

### UPDATED: skills/implement/scripts/step-0-degraded-gate.md

- Update contract prose for the Python degraded gate.

### UPDATED: skills/implement/scripts/generate-code-flow-diagram.sh

- Replace `launch-claude-subprocess.sh` with `agent launch-claude-subprocess`.
- Preserve diagram output and failure behavior.
- Preserve subprocess context redaction and untrusted-data rendering behavior.

### UPDATED: skills/implement/scripts/step2-implement.sh

- Keep current `source scripts/external-tool-registry.sh` behavior because the registry remains retained.
- Do not port Step 2 registry validation in B4.
- Avoid introducing deleted executable dependencies.

### UPDATED: skills/implement/scripts/test-codex-implementer.sh

- Update harness assertions for the post-cutover Codex implementer launcher.
- Replace grep pins for `parse-codex-usage.sh`, `agent-model-args.sh`, and `run-external-agent.sh` with Python `agent` CLI verbs or stable diagnostic tokens.
- Assert usage parser stubs receive the events JSONL path.
- Preserve sidecar, transcript, manifest, stderr-tail, and shard assertions.

### UPDATED: skills/implement/scripts/test-codex-implementer.md

- Update harness contract prose for the Python model-args, usage parser with events path, and run-external-agent surfaces.
- Preserve implementer manifest and diagnostic contract prose.

### UPDATED: skills/implement/scripts/test-cursor-implementer.sh

- Update harness assertions for the post-cutover Cursor implementer launcher.
- Replace grep pins for `cursor-wrap-prompt.sh` and `run-external-agent.sh` with Python `agent` CLI verbs or stable diagnostic tokens.
- Preserve sidecar, transcript, manifest, and shard assertions.

### UPDATED: skills/implement/scripts/test-cursor-implementer.md

- Update harness contract prose for the Python cursor-wrap-prompt and run-external-agent surfaces.
- Preserve implementer manifest and diagnostic contract prose.

### UPDATED: skills/status/scripts/status.sh

- Replace degraded gate shell references with `python3 "$PLUGIN_ROOT/python/cli.py" agent degraded-tools-gate`.
- Preserve explicit presence flags and status output grammar.
- Keep the live `/status` health classification behavior unchanged.

### UPDATED: skills/status/SKILL.md

- Update `/status` prose to reference `skills/status/scripts/status.sh` and the Python `agent degraded-tools-gate` classifier.
- Include this file in stale-reference sweeps.

### UPDATED: skills/shared/voting-protocol.md

- Replace retired script paths in runtime Bash examples with `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" agent ...`.
- Preserve prompt and output grammar.

### UPDATED: skills/shared/dialectic-protocol.md

- Replace retired script paths in judge/voter examples with `agent` CLI verbs.
- Keep bucket-skip semantics unchanged.

### UPDATED: skills/research/references/validation-phase.md

- Replace retired script paths in validation examples with `agent` CLI verbs.
- Keep validation diagnostics caveat unchanged.

### UPDATED: skills/research/references/research-phase.md

- Replace retired launcher examples with matching `agent` CLI verbs.
- Use `agent launch-codex-exec` for Codex execution examples.
- Preserve research lane semantics.

### UPDATED: skills/shared/external-reviewers.md

- Update shared external reviewer procedure references from retired scripts to `agent` CLI verbs.
- Keep degraded posture semantics unchanged.

### UPDATED: skills/design/SKILL.md

- Update live fenced examples that reference retired degraded gate or launcher scripts.
- Point examples at wrapper scripts only when wrappers now call `agent` CLI verbs.

### UPDATED: skills/implement/SKILL.md

- Update live fenced examples that reference retired degraded gate or launcher scripts.
- Preserve implement workflow semantics.

### UPDATED: skills/review/SKILL.md

- Route the degraded gate to `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" agent degraded-tools-gate`.
- Replace live launcher helper references with new CLI verbs or surviving wrapper surfaces.
- Preserve `/review --subagent` degraded behavior and panel waterfall semantics.

### UPDATED: skills/review-and-fix/SKILL.md

- Update live fenced examples that reference retired launcher scripts.
- Preserve review-and-fix output contracts.

### UPDATED: skills/research/SKILL.md

- Update live fenced examples that reference retired validation or launcher scripts.
- Preserve research workflow semantics.

### UPDATED: .claude/rules/external-tool-launcher-parity.md

- Replace live retired launcher references with Python `agent` CLI verbs or surviving integration surfaces.
- Preserve parity intent for launcher behavior and sourced compatibility.
- Add parity reminders for Claude subprocess context redaction and Python auth-lint scanning.
- Avoid deleted executable path literals except where explicitly marked as historical or generated stale-reference fixtures.

### UPDATED: docs/external-reviewers.md

- Update integration-surface docs for the Python launcher framework.
- Replace retired script references with CLI verbs where they are live invocation paths.
- Keep historical prose only where it is clearly historical and not scanned as a live invocation.

### UPDATED: docs/configuration-and-permissions.md

- Update model args, health gate, auth retry, Codex env-key, Cursor auth, timeout, and Step 2b references.
- Preserve operator-facing env var names and defaults.

### UPDATED: docs/run-logs.md

- Update vendor failure diagnostics and external implementer transcript references.
- Keep batch names and sidecar names unchanged.

### UPDATED: docs/run-log-cli.md

- Add or adjust any launcher-related `run-log` references caused by direct Python calls.

### UPDATED: docs/skills.md

- Update health and degraded-tools descriptions to reference `python3 .../cli.py agent degraded-tools-gate`.

### UPDATED: docs/linting.md

- Update `lint-codex-exec-auth` allowlist and guidance for the Python launcher framework.
- Document that the auth lint scans Python call sites fail-closed.
- Remove deleted harness target descriptions.
- Keep retained sourced-contract harness descriptions only for files that still exist.

### UPDATED: python/README.md

- Replace the Phase-7 deferral note with the B4 wiring outcome.
- Document `agents.py` as the external-agent launcher framework.
- Note that `external-tool-registry.sh` remains a sourced compatibility artifact until C-phase consumers are cut over.

### UPDATED: SECURITY.md

- Update security-relevant launcher references:
  - external tool delegation.
  - Codex env-key auth.
  - Cursor auth visibility.
  - run-external-agent metadata and `CMD_JSON`.
  - run-external-agent `STDERR_SINK`.
  - run-external-agent health gate.
  - run-external-agent failure carrier ordering.
  - Darwin serial lock for Codex and Cursor startup.
  - codex-exec outer retry metadata.
  - Codex-exec trusted-instructions handling.
  - Codex-exec auth and model-args preflight failure sidecars.
  - Cursor CI private config isolation and stall diagnostics.
  - Claude subprocess path validation, context redaction, escaped untrusted context rendering, and scoped read-tools mode.
  - vendor failure diagnostics.
- State that Python preserves the existing sidecar, redaction, and context-safety contracts.
- Remove stale claims that Cursor API keys are passed on argv if the live Python path uses env auth.

### UPDATED: Makefile

- Remove deleted harness targets for retired executable scripts.
- Keep any `external-tool-registry.sh` sourced-contract harness target until that sourced artifact is retired.
- Keep retained sourced-contract harness targets for libs that still exist.
- Keep retained dispatch, launch-review, scout, design, implementer, review-and-fix, and validate-plan-command harness targets when those harnesses still exist.
- Point retained launcher regression targets at pytest.
- Keep `make py-test`, `make py-lint`, `make lint-retired-scripts`, and `make lint` green.

### UPDATED: .github/workflows/ci.yaml

- Remove or update comments and steps that reference deleted executable harnesses.
- Keep retained sourced-contract and retained post-cutover harness references only for files that still exist.

### UPDATED: agent-lint.toml

- Remove exceptions for deleted harnesses.
- Keep any exception only when the referenced file still exists.

## Retired files

Delete the executable B4 scripts, their executable-specific `.md` siblings, and their retired executable-specific harnesses after call-site cutover.

Retire these executable scripts in B4:

- `scripts/cursor-auth-flags.sh`
- `scripts/cursor-wrap-prompt.sh`
- `scripts/agent-model-args.sh`
- `scripts/read-claude-model.sh`
- `scripts/launch-codex-ci.sh`
- `scripts/launch-codex-exec.sh`
- `scripts/launch-cursor-ci.sh`
- `scripts/launch-claude-ci.sh`
- `scripts/launch-claude-review.sh`
- `scripts/launch-claude-subprocess.sh`
- `scripts/run-external-agent.sh`
- `scripts/parse-codex-usage.sh`
- `scripts/degraded-tools-gate.sh`

Delete executable-specific harnesses only after their assertions are ported to pytest or retained integration harnesses:

- `scripts/test-run-external-agent.sh`
- `scripts/test-launch-codex-exec.sh`
- matching launcher-specific harnesses for retired executable scripts.

Do not delete sourced-only compatibility artifacts in B4:

- `scripts/lib-external-launcher-common.sh`
- `scripts/lib-codex-launcher-common.sh`
- `scripts/lib-cursor-launcher-common.sh`
- `scripts/lib-cursor-auth.sh`
- `scripts/lib-failed-agent-stderr-tail.sh`
- `scripts/external-tool-registry.sh`

Do not delete retained harnesses that still cover sourced compatibility or post-cutover wrapper behavior.

Do not delete `scripts/external-tool-registry.sh`, its `.md` sibling, or its sourced-contract harness until its source consumers are retired or ported.

## Edge cases

- **Output path validation**: preserve the narrow `[A-Za-z0-9._/-]` path alphabet for external-agent output paths.
- **Stderr sink validation**: support `--stderr-sink`; validate it with the same `[A-Za-z0-9._/-]` allowlist before side effects; write `STDERR_SINK` metadata only when set.
- **Validation side effects**: reject invalid argv, unsafe output paths, unsafe stderr sinks, invalid timeouts, and invalid inner sentinels before artifact cleanup, trap setup, `.meta`, `.diag`, `.failure-diag`, or `.done` writes.
- **Missing child executable**: preserve shell behavior by treating `Popen` `FileNotFoundError` as a post-validation launch failure with `.meta`, `.diag`, `.failure-diag`, and `.done`, not as an early side-effect-free validation failure.
- **Failure carrier ordering**: on nonzero post-validation exits, compose `${output}.failure-diag` before `.done`; visible `.done` implies the failure carrier exists when applicable.
- **Success carrier cleanup**: on success, clear stale `${output}.failure-diag` before `.done`.
- **Post-validation sentinels**: write `.done` on post-validation exit paths after a valid output path exists and trap setup is safe.
- **Tool labels**: sanitize `.meta TOOL=` by translation, not deletion, and use `sanitized-empty` for empty output.
- **Timeouts**: normalize leading-zero timeouts to decimal.
- **Inner sentinel**: preserve `.inner.done` support through `RUN_EXTERNAL_AGENT_INNER_SENTINEL_SUFFIX`.
- **Health gate**: preserve unhealthy Codex rc 7, unhealthy Cursor rc 8, child-not-spawned behavior, health diagnostics, timeout opt-out `0`, and fail-open unparseable probe output.
- **Darwin serial lock**: preserve per-tool startup lock semantics for Codex and Cursor launchers through `LARCH_EXTERNAL_SERIAL_LOCK_*`; acquire before spawn and release after the protected startup window or failure path.
- **Codex stdin**: redirect Codex child stdin from `/dev/null`.
- **Codex-exec trusted instructions**: preserve `--trusted-instructions-file`, validation, temp `CODEX_HOME`, trusted-instruction prepending, and copied-config instruction stripping.
- **Codex-exec preflights**: preserve process rc 0, fd-3 `LAUNCHER_EXIT`, `OUTPUT`, output file, `.diag`, `.meta CMD_JSON=[]`, `.done`, helper rc, and prompt sidecar behavior for auth and model-args failures.
- **Codex-exec public `.done` ordering**: keep public `.done` absent during child retries and post-processing; record timing and usage; append outer metadata; promote `.inner.done` to `.done`; emit `LAUNCHER_EXIT`; then emit `OUTPUT`.
- **Cursor auth**: trim `CURSOR_API_KEY`, export only non-empty values, and keep Darwin keychain pre-read best-effort.
- **Cursor CI**: preserve private `CURSOR_CONFIG_DIR` setup, cleanup, stall monitor diagnostics, sidecar emission, and child-first kill behavior.
- **Cursor sourced libs**: avoid `PLUGIN_ROOT` unbound-variable failures under `set -u`.
- **Cursor model args**: preserve `--tool cursor --with-effort` when replacing `agent-model-args.sh` in cursor launcher common code.
- **Codex auth**: keep env-key provider args non-secret and strip copied temp config secrets.
- **Usage parsing**: require an events JSONL path, pass it through all replacements, and fail closed when cached input exceeds input.
- **Codex-exec outer retry**: keep the nine-field metadata contract and replay through `agent launch-codex-exec`.
- **Claude subprocess**: reject symlinks, `..`, control characters, invalid roots, oversized context files, and malformed JSON envelopes.
- **Claude context rendering**: preserve XML-escaped path attributes, untrusted-data preamble, body escaping, secret redaction, and no unredacted secret leakage.
- **Claude read tools**: preserve `--read-tools` and `--read-tools-add-dir`, including session-root validation and `CMD_JSON` allowlist behavior.
- **Failure diagnostics**: keep stderr tails bounded and redacted before operator-visible emission.
- **Degraded gate**: preserve empty presence input as a distinct bug signal.
- **Sourced libs**: do not break `source` consumers before their C-phase rewrites.
- **Collector retries**: accept Python launcher metadata, forward `STDERR_SINK`, and replay retries through the new `agent` CLI entrypoints.
- **Auth lint**: scan Python call sites for raw `codex exec` and fail closed outside the wired launcher surface and intentional tests.
- **Live skill surfaces**: update `/status`, `/review`, `/design`, `/implement`, and `/research` prompt prose, not only root scripts.
- **Retained tests**: update stubs and assertions for retained dispatch, launch-review, scout, design, implementer, review-and-fix, and validate-plan-command harnesses.
- **Retained sibling docs**: update retained `.md` contract siblings that mention retired launchers so `lint-retired-scripts` and operator-facing docs do not point at deleted helpers.

## Failure modes

- `jq` removal can change parse-codex-usage behavior. Pin JSONL pytest cases from current shell behavior.
- Usage recording can silently regress if replacement call sites omit the events JSONL positional path. Pin parser argv at sourced-lib and implementer boundaries.
- Python subprocess monitoring can miss exact bash `SECONDS` timing. Compare observable sidecars, exit code, and progress cadence, not internal counters.
- Darwin Codex or Cursor launchers can regress if the per-tool serial lock is omitted. Pin lock acquire/release sequencing with injected hooks.
- Cursor CI can regress if private config-dir setup, cleanup, stall diagnostics, sidecars, or child-first kill behavior are not ported. Pin these contracts in pytest.
- Claude scoped read-only launches can regress if `--read-tools` and `--read-tools-add-dir` are dropped. Pin session-root validation and `CMD_JSON` allowlist behavior.
- Claude subprocess context can leak secrets or turn untrusted bytes into prompt structure if redaction or escaping is dropped. Pin escaped paths, escaped bodies, untrusted-data preamble, and no unredacted secret leakage.
- Codex-exec trusted instructions can regress if `--trusted-instructions-file` or config stripping is dropped. Pin the drafter-facing flag and temp config behavior.
- Codex-exec preflight failures can regress if the Python wrapper exits nonzero or skips sidecars. Pin auth and model-args failure bundles.
- Codex-exec retry metadata can race collectors if public `.done` is promoted before usage and outer metadata are appended. Pin the post-child ordering.
- run-external-agent can regress if `--stderr-sink` is rejected or dropped from `.meta`. Pin acceptance, rejection, and collector retry forwarding.
- run-external-agent can regress if `.done` is written before `.failure-diag` on failures. Pin carrier-before-sentinel ordering.
- run-external-agent can regress if the health gate spawns unhealthy children or loses opt-out behavior. Pin the health-gate matrix.
- run-external-agent can regress if missing child commands are prevalidated before artifacts. Preserve post-validation launch failure behavior.
- Direct CLI call strings can trip `lint-retired-scripts` if any old path remains in docs, skills, tests, Python, Makefile, CI, `.claude/`, retained harnesses, retained sibling docs, or comments.
- Raw `codex exec` can become invisible if auth lint does not scan Python. Extend lint coverage to Python launcher call sites.
- Keeping bash libs alive can leave duplicate logic temporarily. Treat Python as the new executable authority and bash libs as compatibility for remaining sourced consumers.
- Retained sourced libs can still break if their internal calls point at deleted helpers. Pin `lib-cursor-launcher-common.sh`, `lib-external-launcher-common.sh`, `lib-cursor-auth.sh`, and `external-tool-registry.sh` substitutions with retained harness checks.
- Cursor launches can lose effort flags if `lib-cursor-launcher-common.sh` drops `--with-effort`. Pin the exact Python model-args argv.
- Registry tests can fail if their per-tool model-args probe still executes `agent-model-args.sh`. Repoint that section separately from registry coverage.
- Retained harnesses can fail after script deletion if their stubs still assume deleted launcher scripts. Update dispatch, launch-review, scout, design, implementer, review-and-fix, and validate-plan-command harnesses before deleting executables.
- Cursor lint-fix can fail under `set -u` if a sourced lib assumes `PLUGIN_ROOT`. Fix root derivation before deleting helper scripts.
- lint-fix-loop and review-and-fix can exit early if `[[ -x "$RUN_EXTERNAL_AGENT_SH" ]]` remains after replacing the executable with Python argv arrays. Replace with `PY_CLI` file checks.
- Collector retry recovery can reject new metadata if outer-meta compatibility is incomplete. Add focused coverage before deleting `run-external-agent.sh` or `launch-codex-exec.sh`.
- Codex-exec retry can fail if the collector still enforces a regular executable shell path. Relax that gate for `OUTER_LAUNCHER_KIND=codex-exec`.
- `/status` can keep calling a retired gate if only root scripts are updated. Update `skills/status/scripts/status.sh` and `skills/status/SKILL.md`.
- Dialectic flows can keep stale retired launcher references. Update both shared dialectic protocol and design dialectic execution references.
- Retained sibling docs can keep stale live invocation paths even after scripts are deleted. Update each retained `.md` contract sibling listed in this plan.
- `external-tool-registry.sh` must remain until every source consumer is ported. Deleting it can break `collect-agent-results.sh` and `skills/implement/scripts/step2-implement.sh` at source time.
- `gh issue comment` may fail in offline or unauthenticated environments. If so, report the exact comments that still need posting.

## Downstream consumers

- `/design`: plan voters, dialectic judges, research validation, Step 2b Codex drafter, review panels, plan revision waterfall, degraded gate, validate-plan commands, and collector retries.
- `/implement`: implementer launchers, CI fix waterfall, lint-fix loop, conflict resolution, vendor diagnostics, Step 0 degraded gate, Step 2 registry validation, diagram generation, and implementer harnesses.
- `/review`: external reviewer waterfall, degraded gate, Claude fallback, review-and-fix, review-and-fix harnesses, and collector retries.
- `/research`: validation lanes and research lanes.
- `/status`: health probe classification and degraded-tools summary.
- `ship-pr`: CI fixers and conflict fixers.
- `check-reviewers`: Step 0 availability probes and degraded posture.
- Python orchestration: checks, CI monitor, rebase, voting retry paths, codex-exec-auth lint, and Python launcher call-site scanning.
- `.claude` rules and retained harness docs: parity reminders, launcher contracts, and stale-reference lint inputs.
- Retained sibling docs under `scripts/`: check-reviewers, run-negotiation-round, lint-fix-loop, ship-pr, dispatch-with-waterfall, dispatch-plan-voters, dispatch-code-voters, collect-agent-results, launch-review, and scout-dynamic-archetypes.

## Testing strategy

- Run focused tests first:
  - `python3 -m pytest python/test_agents.py`
  - `python3 -m pytest python/test_checks.py python/test_ci_monitor.py python/test_rebase.py python/test_voting.py`
  - `python3 -m pytest python/test_lint_codex_exec_auth.py`
  - `make py-test`
  - `make py-lint`
  - `make lint-retired-scripts`
- Run retained sourced-contract and integration checks:
  - retained `external-tool-registry` harness.
  - retained `lib-cursor-auth` harness.
  - retained `lib-external-launcher-common` harness.
  - retained token vendor scraper harness.
  - retained dispatch voters harnesses.
  - retained launch-review harness.
  - retained review-and-fix harness.
  - retained codex implementer harness.
  - retained cursor implementer harness.
  - retained validate-plan-commands harness.
  - `bash scripts/relevant-checks.sh`
  - `make lint`
- Before deleting each executable-specific bash harness, run it once against the new CLI if practical, then port its assertions into pytest or retained integration harnesses.
- Keep retained sourced-contract harnesses for `external-tool-registry.sh` until that file is retired.
- Confirm no retired executable path literals remain in live call paths:
  - `make lint-retired-scripts`
  - targeted grep over `scripts/`, `skills/`, `python/`, `docs/`, `.github/`, `.claude/`, `Makefile`, tests, retained harness docs, retained sibling docs, and comments.
- Confirm parser replacement calls include the events JSONL path.
- Confirm retained sourced parser calls preserve stderr capture and empty fallback on parser failure.
- Confirm collector retry behavior with old and new metadata fixtures.
- Confirm collector retry forwards `STDERR_SINK`.
- Confirm codex-exec outer retry metadata includes the nine expected fields and compact add-dir JSON.
- Confirm codex-exec public `.done` appears only after usage and outer metadata are complete.
- Confirm Codex-exec auth and model-args preflight failures preserve wrapper rc 0, fd-3 `LAUNCHER_EXIT`, output and sidecars.
- Confirm Codex-exec `--trusted-instructions-file` behavior with temporary config merging and instruction stripping.
- Confirm run-external-agent health gate behavior for unhealthy, opt-out, and unparseable probe cases.
- Confirm run-external-agent `--stderr-sink` behavior and validation.
- Confirm run-external-agent failure carrier exists before `.done`.
- Confirm missing child executable behavior writes post-validation sidecars.
- Confirm Darwin serial lock acquisition and release for Codex CI, Cursor CI, and Codex-exec.
- Confirm Cursor CI stall and private config-dir behavior.
- Confirm Claude read-tools scoped mode and add-dir validation.
- Confirm Claude subprocess context rendering preserves XML escaping, untrusted-data framing, body escaping, secret redaction, and no unredacted secret leakage.
- Confirm validation failures remain side-effect free for invalid argv, output path, stderr sink, timeout, and inner sentinel cases.
- Confirm review-and-fix and lint-fix-loop use Python argv arrays and `PY_CLI` file checks instead of executable-bit checks for deleted scripts.
- Confirm implementer harness diagnostics no longer require deleted script basenames unless the launcher intentionally preserves stable legacy wording.
- Confirm auth lint catches raw `codex exec` in Python files outside the wired launcher surface and intentional tests.
- Confirm docs and generated references:
  - `python3 python/cli.py generate check`
- Confirm no security-regression wording remains by grepping for retired launcher paths in `SECURITY.md`, docs, skills, Makefile, CI, `.claude/`, retained harnesses, retained sibling docs, and comments.

diff_added: 4835
diff_deleted: 4525
mechanical_churn: true
diff_lines: 9360

## Acceptance

- [ ] All 14 executable B4 bash scripts deleted and listed in `python/migrated-scripts.tsv`
- [ ] Sourced-only bash libs kept alive (NOT in `migrated-scripts.tsv`)
- [ ] `python/agents.py` extended with all ported launcher functions
- [ ] `python/cli.py` has `agent` domain with 14 CLI verbs registered
- [ ] `python/test_agents.py` has pytest coverage replacing retired harnesses
- [ ] All surviving bash callers updated to `python3 cli.py agent ...` (minimal executable-path substitutions)
- [ ] `make py-test` passes
- [ ] `make py-lint` passes
- [ ] `make lint-retired-scripts` passes (no surviving references to retired executables)
- [ ] `make lint` passes
- [ ] Comments posted on C-phase issues #3676, #3677, #3678, #3680, #3682, #3684 documenting sourced-lib retirement responsibility
- [ ] `python3 python/cli.py generate check` passes (no generated-artifact drift)
- [ ] `SECURITY.md` updated for security-relevant launcher references

diff_lines: 9360

## Test plan
(no test plan section in plan-file)
