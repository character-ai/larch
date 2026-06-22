## Plan

Introduce a frozen `Ctx` in `python/ctx.py` and adopt it incrementally at pinned hotspot `_main` / `*_core` boundaries in `agents.py`, `design_lifecycle.py`, and `plan_quality.py`.

**Core rules**

- **One snapshot per CLI invocation.** Build `ctx` exactly once at the innermost owning boundary: `*_core` when `*_main` only forwards, otherwise `*_main` when no core exists. Outer `*_main` must not call `_rehydrate_*` or build `ctx` when it only delegates to core.
- **Rehydrate before `quiet_init` before `ctx`.** On wrapper/validator entrypoints: call `_rehydrate_wrapper_env` / `_rehydrate_validator_env` first; validate and normalize `design_tmpdir` (or equivalent) into live `os.environ` when the boundary owns that step; then call `logging_util.quiet_init`; then build `ctx` from the **full** process environment with rehydrated and normalized overrides applied. Do **not** call `quiet_init` before rehydrate/normalized `DESIGN_TMPDIR` is visible — current mains set `DESIGN_TMPDIR` before `quiet_init` so logs route to the design run directory, not `TMPDIR` or `/tmp`.
- **Normalized values win in merge.** After validate/resolve, build `ctx` with merge order where normalized fields unconditionally beat stale rehydrate snapshots — for example `{**env, **os.environ, **normalized_overrides}` where `normalized_overrides` always includes `{"DESIGN_TMPDIR": str(design_tmpdir), ...}` (or omit spreading stale `env` keys that normalization replaces). Never let pre-resolve `env` from `_rehydrate_wrapper_env` overwrite live `os.environ` or the resolved path.
- **`from_mapping` copies input.** `Ctx.from_mapping` must store an independent `raw_env` snapshot (`dict(env)` or `types.MappingProxyType` over a copied dict). Never retain the caller's mutable mapping reference — post-build in-place edits must not mutate an existing `Ctx` despite `frozen=True`.
- **After normalization.** When a core path normalizes `design_tmpdir` (or similar), merge the normalized value into the mapping before `Ctx.from_mapping`, not from a pre-normalization snapshot.
- **`step5c_core` / `step_final_summary_core` / `validator_autofix_main` ctx anchor.** Build `ctx` only after rehydrate (where applicable), plugin-root validation (where applicable), normalized `design_tmpdir` is reflected in `os.environ` and in `normalized_overrides`, and `quiet_init` has run. Immediately before the first helper that reads via `ctx`. Do not snapshot immediately after `_rehydrate_*` while plugin-root validation or tmpdir normalization still mutates live env.
- **Argv-first precedence.** For mains that resolve values from argparse before env (for example `validate_plan_main` with `--design-tmpdir`, `degraded_tools_gate_main` with `--codex-present`, `render_final_summary_main` with `--design-tmpdir`), build or resolve from explicit CLI values first; merge argv overrides into the mapping before `Ctx.from_mapping` or use argv-wins resolution at the call site. Typed fields and `str_value`/`bool_value`/etc. must reflect argv wins. Do not build `ctx` at entry and later ignore CLI overrides in favor of stale `ctx.design_tmpdir`. Keys with no argv surface continue to come from env/rehydrate only.
- **Per-main ctx merge recipes (do not share one blanket recipe).**
  - `validator_autofix_main`: `_rehydrate_validator_env(parsed)` → validate/resolve `design_tmpdir` → write resolved path to `os.environ` → `normalized_overrides` → `quiet_init` (if not already ordered elsewhere on this path) → `ctx = Ctx.from_mapping({**os.environ, **rehydrate_merged, **normalized_overrides})` once → converted helpers including `_validator_pause_save`.
  - `validate_plan_main` / `check_plan_size_main`: **no** `_rehydrate_validator_env` (standalone CLI/harness entrypoints; validator allowlist would change `DESIGN_TMPDIR`, `SITE`, and validator-status precedence). Parse argv → validate/resolve `design_tmpdir` when the main owns that step → `ctx = Ctx.from_mapping({**os.environ, **argv_overrides})` where `argv_overrides` maps flag dest names (for example `design_tmpdir` from `--design-tmpdir`) into `config.ENV_*` keys.
  - `degraded_tools_gate_main`: parse argv → merge `vars(args)` presence/binary-found/skill fields into the mapping (parser defaults bind from ambient env at definition time; explicit `--codex-present` etc. must win) → `ctx = Ctx.from_mapping({**os.environ, **argv_overrides_from_vars(args)})`.
- **`ctx=None` fallback.** Every converted helper accepts optional `ctx: Ctx | None = None`. When `ctx is None`, read `os.environ` exactly as today. When `ctx` is set, read only from `ctx` (typed fields or narrow helpers), not ambient env.
- **Key membership for precedence.** `resolve_model_args` uses `key in os.environ` before plugin-name fallback. Converted paths must use `ctx.contains(key)` (snapshot membership) plus `ctx.str_value`, not live `os.environ` membership and not `str_value(..., default="")` alone — absent vs present-but-empty must match today's precedence.
- **Quiet state stays live.** Do **not** route `_core_quiet_mirrors_to_fd4` or `_capture_main` quiet-disable handling through `ctx`. Keep both on live `os.environ` / `logging_util` quiet helpers because `quiet_init` and autofix capture mutate quiet PID/active/disable state during execution. Do **not** add `quiet_*` typed fields to `Ctx`.
- **`quiet_init` single owner per core.** Relocate `quiet_init` to each owning core **after** rehydrate and normalized tmpdir setup, **before** `ctx` build. Thin `*_main` delegates must **not** call `quiet_init`. Remove any existing `quiet_init` call from `step_final_summary_main` when adding it to `step_final_summary_core` — never both. Extend lifecycle tests that invoke cores directly to assert the same quiet routing as CLI for both `step5c_core` and `step_final_summary_core`.
- **IPC removal is paired with callee conversion.** Dropping an `os.environ` write requires every in-process callee on that path to receive the value via parameter or `ctx`. Until converted, keep a documented legacy-compat env write.
- **Child env.** Use `ctx.subprocess_env()` from the full merged snapshot. Pass explicit per-call overrides for temporary values (for example inner sentinel suffix) instead of mutating process env when the converted path would otherwise read a stale `ctx`.
- **Secrets.** `raw_env` uses `field(repr=False)` or a redacted `__repr__`; `subprocess_env()` behavior unchanged. Forbid direct `raw_env` reads outside `ctx.py`; use typed fields or narrow helpers only.

Keep `.sh` env-file wire format unchanged. Keep `config.py` name-only (no parsing logic). Preserve `old_environ = os.environ.copy()` restore blocks in `*_core`.

## Files to modify/create

### NEW: `python/ctx.py`

Define frozen `Ctx`:

- `@dataclass(frozen=True)`
- `raw_env: Mapping[str, str]` with `field(repr=False)` (or custom redacted `__repr__`); always a **copy** of the input mapping at construction time
- Typed fields (use `config.ENV_*` where defined), including:
  - `design_tmpdir: str`
  - `implement_tmpdir: str`
  - `claude_plugin_root: str`
  - `repo: str`
  - `issue_number: str`
  - `session_id: str`
  - `session_tmpdir: str`
  - `larch_run_id: str`
  - `summary_outcome: str`
  - `final_summary_path: str`
  - `claude_pid: str`
  - `codex_binary_found: str`
  - `cursor_binary_found: str`
  - `codex_present: str`
  - `cursor_present: str`
  - `tmpdir: str`
  - `home: str`
  - `path: str`
  - `user: str`

**Exclude** `quiet_disable`, `quiet_active`, and `quiet_pid` from typed fields (quiet stays on live env only).

Helpers:

- `from_env(env: Mapping[str, str] | None = None) -> Ctx` — full-process snapshot; default `os.environ`; copies into independent `raw_env`
- `from_mapping(env: Mapping[str, str]) -> Ctx` — copies `env` into independent `raw_env` before field extraction (tests or explicit merged dicts)
- `contains(key: str) -> bool` — snapshot key membership over `raw_env` (used for `LARCH_*` → `CLAUDE_PLUGIN_OPTION_*` precedence; distinguishes absent from present-but-empty)
- `str_value(key: str, default: str = "") -> str` — discouraged general string accessor keyed by `config.ENV_*` constants; use for rehydrate-only / validator keys without typed fields (`SITE`, `MODE`, `VALIDATE_*`, `LARCH_TEST_*`, `LARCH_DESIGN_DRIFT_MULTIPLE`, presence keys when not using typed fields)
- `bool_value(key: str, default: bool = False) -> bool`
- `int_value(key: str, default: int | None = None) -> int | None`
- `float_value(key: str, default: float | None = None) -> float | None`
- `subprocess_env(overrides: Mapping[str, str] | None = None, remove: Iterable[str] = ()) -> dict[str, str]`

Keep broad undifferentiated `ctx.get()` discouraged; no public encourage-new-use API beyond narrow helpers.

### UPDATED: `python/config.py`

Add missing `ENV_*` name constants only where converted code needs them. Additions for this tranche:

- `ENV_CLAUDE_PLUGIN_ROOT`
- `ENV_REPO`
- `ENV_ISSUE_NUMBER`
- `ENV_SESSION_ID`
- `ENV_SESSION_TMPDIR`
- `ENV_CLAUDE_PID`
- `ENV_CODEX_BINARY_FOUND`
- `ENV_CURSOR_BINARY_FOUND`
- `ENV_CODEX_PRESENT`
- `ENV_CURSOR_PRESENT`
- `ENV_SUMMARY_OUTCOME`
- `ENV_FINAL_SUMMARY_PATH`
- `ENV_LARCH_DESIGN_DRIFT_MULTIPLE`
- `ENV_LARCH_CURSOR_MODEL`
- `ENV_LARCH_CODEX_MODEL`
- `ENV_LARCH_CODEX_EFFORT`
- `ENV_CLAUDE_PLUGIN_OPTION_CURSOR_MODEL`
- `ENV_CLAUDE_PLUGIN_OPTION_CODEX_MODEL`
- `ENV_CLAUDE_PLUGIN_OPTION_CODEX_EFFORT`
- `ENV_RUN_EXTERNAL_AGENT_INNER_SENTINEL_SUFFIX`
- `ENV_RUN_EXTERNAL_AGENT_POLL_INTERVAL`
- `ENV_LARCH_EXTERNAL_STARTUP_LOCK_FORCE_UNAME`
- `ENV_LARCH_EXTERNAL_STARTUP_LOCK_TTL`
- `ENV_LARCH_EXTERNAL_STARTUP_LOCK_TRIES`
- Validator status `ENV_*` constants actually read via `ctx` after conversion in `validator_autofix_main` (add only keys that remain env-sourced post-conversion)
- `ENV_TMPDIR`
- `ENV_HOME`
- `ENV_PATH`
- `ENV_USER`
- `ENV_LOGNAME`

No `ENV_*` additions for quiet keys unless a non-quiet converted read needs them. No parsing logic.

### UPDATED: `python/agents.py`

Import `Ctx`.

**Pinned `_main` ctx owners (this PR only).** Build `ctx` once in exactly these entrypoints; defer all other `launch_*_main` / implement-launch `_main` surfaces unless a future IPC removal mechanically requires them:

| `_main` | Build timing |
|---------|----------------|
| `model_args_main` | After argparse; merge argv overrides into mapping before `Ctx.from_mapping` |
| `degraded_tools_gate_main` | After argparse; merge `vars(args)` into mapping (`codex_binary_found`, `codex_present`, `cursor_binary_found`, `cursor_present`, `skill`) before `Ctx.from_mapping`; read presence/binary via typed fields or `str_value` |
| `run_external_agent_main` | After boundary-local hydration visible to converted reads |

**Deferred this PR:** `launch_review_main`, `_review_run_wrapper_attempt`, and other review/implement launch `_main` functions keep today's `os.environ` reads. Do not expand agents conversion beyond the three owners above plus helpers they call on those paths.

Converted helpers (all with `ctx: Ctx | None = None` fallback; converted only when called from a pinned owner with non-None `ctx`):

- `resolve_model_args` — from `model_args_main`; when `ctx` is set, use `ctx.contains(env_name)` / `ctx.contains(plugin_name)` with `ctx.str_value` for the `LARCH_*` → `CLAUDE_PLUGIN_OPTION_*` → default chain (preserve absent-vs-empty semantics); route model/effort reads through `config.ENV_*` constants
- `degraded_tools_gate_main` body/helpers — presence and binary-found reads via `ctx` built from `vars(args)` merge, not raw ambient `os.environ` alone after conversion
- `run_external_agent_main` — accept explicit per-call overrides for temporary env such as `RUN_EXTERNAL_AGENT_INNER_SENTINEL_SUFFIX`; route startup-lock and poll-interval reads through `ctx.str_value` / `ctx.int_value` with new `ENV_*` constants; do not rely on a stale boundary `ctx` for values set immediately before the call
- `external_startup_lock_acquire` — when on `run_external_agent_main` path

Subprocesses on converted paths: replace `dict(os.environ)` with `ctx.subprocess_env()` when caller has `ctx`.

Preserve auth/temporary vendor home mutations (`CURSOR_API_KEY`, `CURSOR_CONFIG_DIR`, `CODEX_HOME`) unless trivial `env=` pass-through without semantic change.

### UPDATED: `python/design_lifecycle.py`

**Ownership**

- `step5c_main`: thin delegate — early argv parse-error handling only, then `step5c_core(argv)`; no rehydrate, no `quiet_init`, no `ctx` in main.
- `step5c_core`: `_rehydrate_wrapper_env` → plugin-root validation → normalized `design_tmpdir` in live env → `quiet_init` → `ctx = Ctx.from_mapping({**env, **os.environ, **normalized_overrides})` once at anchor (normalized `DESIGN_TMPDIR` in `normalized_overrides` wins over stale `env`) → converted helper calls.
- `step_final_summary_main`: **not** a pure argv forwarder. Retain:
  - early argv parse-error handling (return `2`)
  - resolved `design_tmpdir` for the post-core `.completed/step-final-summary` sentinel probe (validate from rehydrate env before core call, same as today)
  - post-core exit mapping: return core rc unchanged when `rc in {2, 3}`; otherwise return `0` when `.completed/step-final-summary` exists, else return core rc
  - delegate rehydrate, `quiet_init`, and `ctx` to `step_final_summary_core`
  - **no** `quiet_init` in main (removed; core-only owner)
- `step_final_summary_core`: `_rehydrate_wrapper_env` → validate/normalize `design_tmpdir` → `quiet_init` → `ctx` build with same normalized-wins merge → converted work (mirror `step5c_core` ordering).

Converted helpers (`ctx: Ctx | None = None` unless noted):

- `_design_tmpdir(ctx)` — when `ctx` set, use `ctx.design_tmpdir`; else current env read
- `_call_pause_save(design_tmpdir, ctx)`
- `_maybe_timing_mark(label, ctx)`
- `_shared_step2b_postplan_body(parsed: WrapperArgs, *, design_tmpdir: Path, ctx: Ctx | None = None) -> PostplanResult` — **required** resolved `design_tmpdir` (and `ctx` when built); **stop calling `_design_tmpdir()` internally**; all callers pass the entry-validated resolved path
- `_step5c_render_final_summary(design_tmpdir, env, outcome, *, final_summary_path: str, plan_write_ok: str = "")` — **required** `final_summary_path`; remove all `os.environ["FINAL_SUMMARY_PATH"]` reads inside (including the pre-render summary-delete block); use the parameter only
- `_emit_final_summary_marked_from_disk(design_tmpdir, final_summary_path: str)` — **required** `final_summary_path`; remove env fallback
- `_step5c_write_status` callers as needed

**`_shared_step2b_postplan_body` caller inventory** (all must pass resolved `design_tmpdir`; pass `ctx` when built at boundary):

| Caller | Threading |
|--------|-----------|
| `step2b_postplan_main` | Entry-validated resolved `Path` (and `ctx` after normalization) |
| `step2b_drafter_main` (~3419) | Same entry-validated resolved `Path` used for sentinel/pause/timing/vendor `--design-tmpdir` args |
| Direct test invocations (e.g. `test_step2b_postplan_rc_11_raises_system_exit`) | Explicit resolved `Path` argument, not ambient `DESIGN_TMPDIR` alone |

**`step2b_drafter_main` entry validation (parity with postplan).** Immediately after `_rehydrate_wrapper_env`, run the same `validate_design_tmpdir` + `Path(...).resolve()` sequence as `step2b_postplan_main`. Assign the resolved `Path` once and thread it through the entire drafter flow (sentinel checks, pause, timing, prompt IO, vendor subprocess `--design-tmpdir` args) and into `_shared_step2b_postplan_body(..., design_tmpdir=resolved, ctx=ctx)` alongside `WrapperArgs`. Do not defer validate/resolve to immediately before the shared postplan body only.

**`final_summary_path` call-site inventory** (all must pass explicit path once env IPC is removed):

| Call site | Path argument |
|-----------|---------------|
| `step5c_core` failed-publish-tail branch (before `result_env` exists) | `str(design_tmpdir / "final-summary.md")` |
| `step5c_core` post-publish happy/failed-plan-write branch | `final_summary_path` from `result_env`, or `str(design_tmpdir / "final-summary.md")` when empty |
| `step_final_summary_core` emit after successful render | `str(design_tmpdir / "final-summary.md")`, or `ctx.final_summary_path` when non-empty after ctx build |

**Not converted:** `_core_quiet_mirrors_to_fd4` — keep on live `os.environ` / quiet helpers.

**IPC removal (paired with parameters)**

- `step0_clarify_hard_halt_main`: remove final `SUMMARY_OUTCOME` env write when no in-process reader remains
- `step2b_postplan_main` / `step2b_drafter_main`: keep normalized `design_tmpdir` local; thread into `_shared_step2b_postplan_body`; drop normalize write at postplan boundary unless a legacy callee still needs it (document if kept)
- `step5c_core`: do not write `CLAUDE_PID` to process env; use `ctx.claude_pid` or `parsed.claude_pid` with inherited-env fallback for marker text and publish `--claude-pid`
- `step5c_core`: carry `final_summary_path` as local variable; pass to `_step5c_render_final_summary` and `_emit_final_summary_marked_from_disk` at every call site (no env IPC)
- `step5c_core`: do not write `FINAL_SUMMARY_PATH` to process env once all emit/render call sites use the parameter

Preserve: `*_core` save/restore, child-process env setup, wrapper env-file parsing, legacy-compat writes only where callee lacks parameter path (short comment).

### UPDATED: `python/design_summary.py`

Add CLI parameters so `render_final_summary_main` no longer depends on ambient env for converted callers:

- `--design-tmpdir <path>` — explicit argv wins over `DESIGN_TMPDIR` env when provided
- `--issue-number` / `--session-id` — optional; explicit argv wins over env when provided; env fallback only for legacy callers

**Argv-first precedence inside `render_final_summary_main`:** parse the new flags alongside existing `--outcome` / `--mode` / `--repo`; resolve `design_tmpdir`, `issue_number`, and `session_id` from explicit args when non-empty, else fall back to `os.environ` (same pattern as `plan_quality` argv-first mains). Do not read env when explicit args are present — stale env must not override IPC-threaded values from `step_final_summary_core` / `_step5c_render_final_summary`.

`step_final_summary_core` and `_step5c_render_final_summary` pass `--design-tmpdir`, `--issue-number`, and `--session-id` from merged rehydrate env (or `ctx`) in `render_args`. Legacy CLI/subprocess callers without new flags continue env fallback. Do not change summary content.

### UPDATED: `python/plan_quality.py`

**Three distinct ctx recipes (do not unify under one rehydrate merge):**

| Main | Rehydrate | Ctx build |
|------|-----------|-----------|
| `validate_plan_main` | **None** (standalone CLI) | Parse argv → optional `design_tmpdir` validate/resolve → `ctx = Ctx.from_mapping({**os.environ, **argv_overrides})` |
| `check_plan_size_main` | **None** (standalone CLI) | Parse argv → validate/resolve required `--design-tmpdir` → `ctx = Ctx.from_mapping({**os.environ, **argv_overrides})` |
| `validator_autofix_main` | `_rehydrate_validator_env(parsed)` | Rehydrate → validate/resolve `design_tmpdir` → `os.environ["DESIGN_TMPDIR"] = str(resolved)` → `normalized_overrides` → `quiet_init` → `ctx = Ctx.from_mapping({**os.environ, **rehydrate_merged, **normalized_overrides})` **once**, immediately before first `ctx` read (including `_validator_pause_save` / `_validator_operator_cancel_audit`) |

**Deferred this PR:** `revise_plan_with_waterfall_main` — keep today's `os.environ` reads (deep `LARCH_TEST_*` launcher overrides inside nested closures); do not build a dead `ctx` snapshot at entry until a follow-up names which reads convert.

`validator_autofix_main`: do **not** build `ctx` immediately after `_rehydrate_validator_env` before `validate_design_tmpdir` and `Path(...).resolve()`; mirror `step5c_core` normalized-wins anchor ordering.

Convert boundary reads including:

- `DESIGN_TMPDIR`, `TMPDIR`, `CLAUDE_PLUGIN_ROOT` (respect argv `--design-tmpdir` precedence on `validate_plan_main` / `check_plan_size_main`)
- `LARCH_DESIGN_DRIFT_MULTIPLE` via `ctx.str_value(config.ENV_LARCH_DESIGN_DRIFT_MULTIPLE, "2")` then **preserve today's explicit fallback**: `multiple = int(multiple_text) if multiple_text.isdigit() and int(multiple_text) > 0 else 2` — do not replace with bare `ctx.int_value` alone
- `LARCH_TEST_*` launcher overrides via `str_value`
- validator status keys in `validator_autofix_main` via `str_value` + new `ENV_*` constants
- **`SUMMARY_OUTCOME`, `ISSUE_NUMBER`, `REPO`** (rehydrate-only on validator path)

Pass `ctx` into `_validator_pause_save`, `_validator_operator_cancel_audit`, and other boundary-adjacent helpers on the validator path only.

**`_capture_main` exception:** keep live `LARCH_QUIET_DISABLE` save/set/reset/restore on `os.environ` unchanged. Do not route quiet-disable handling through `ctx`; only thread `ctx` into actual env reads on the validator path around the capture.

Keep deep validation logic unchanged.

### NEW: `python/test_ctx.py`

Cover:

- defaults with empty env
- bool parsing (`1`, `true`, `yes`, `on`, empty, invalid)
- int/float invalid values
- `str_value` for rehydrate-only keys
- `contains()` membership (absent vs present-but-empty)
- config constant-backed fields
- `subprocess_env()` override/removal
- snapshot immutability after `os.environ` mutation
- **`from_mapping` input independence:** mutate caller dict after build; assert `ctx` fields unchanged
- **`repr(ctx)` does not expose secret env values** (for example API keys)
- no `quiet_*` typed fields on `Ctx`
- `codex_present` / `cursor_present` preserve empty-string semantics

### UPDATED: `python/test_agents.py`

Focused tests for the three pinned `_main` owners and `ctx=None` fallback.

- `model_args_main`, `degraded_tools_gate_main`, `run_external_agent_main` build `ctx` once and pass to converted helpers
- `resolve_model_args` with `ctx`: `contains` + `str_value` preserves `LARCH_*` → `CLAUDE_PLUGIN_OPTION_*` precedence when primary key absent vs empty
- `degraded_tools_gate_main`: explicit `--codex-present` / `--cursor-present` argv values appear in `ctx` and drive `degraded_tools_result` inputs; not shadowed by stale ambient env
- `run_external_agent_main`: explicit override for inner sentinel suffix (not stale early `ctx`); startup-lock/poll reads via `ctx`
- Existing monkeypatch env tests still pass via `Ctx.from_env()` at public boundaries
- No tests requiring `launch_review_main` ctx adoption (deferred)

### UPDATED: `python/test_design_lifecycle.py`

- `_shared_step2b_postplan_body` receives resolved `design_tmpdir`/`ctx` from postplan and drafter mains (no reliance on ambient env after write removal)
- Update `test_step2b_postplan_rc_11_raises_system_exit` (and any similar direct shared-body invocations) to pass explicit resolved `Path`, not `DESIGN_TMPDIR` ambient env alone
- `step2b_drafter_main` validates/resolves at **main entry** (same sequence as postplan); single resolved path through sentinel/pause/timing/vendor args and `_shared_step2b_postplan_body(..., design_tmpdir=resolved)`
- `test_step5c_core_rc1_uses_stdout_over_stale_primary_and_binds_final_summary_path`: assert explicit `final_summary_path` parameter at all render/emit call sites, not `os.environ["FINAL_SUMMARY_PATH"]`
- Regression: `step5c_core` does not leak `FINAL_SUMMARY_PATH` or `SUMMARY_OUTCOME` after return
- `step5c_core` failed-publish-tail branch passes default `final-summary.md` path to render/emit
- `step_final_summary_core` passes explicit path to `_emit_final_summary_marked_from_disk`; parallel regression test to step5c binding tests
- `step_final_summary_core` passes `--design-tmpdir` / `--issue-number` / `--session-id` to `render_final_summary_main`
- Direct `step5c_core` **and** `step_final_summary_core` invocation: quiet routing matches CLI; assert `step_final_summary_main` does **not** call `quiet_init`
- **Migrate every direct `step5c_core` / `step_final_summary_core` contract assertion off `capsys` stdout** (for example `test_step5c_core_assembles_publish_argv_and_cleans_bg_marker`, `test_step_final_summary_core_emits_markers_and_cleans_bg_marker`, and similar) **to fd-3 contract capture** via `capture_contract_stream_to_paths` / inherited-quiet pipe pattern from `test_step5c_main_machine_rows_visible_under_inherited_quiet` — contract KVs and `LARCH_FINAL_SUMMARY_*` markers route to `logging_util.contract_stream()`, not stdout, after `quiet_init` moves into cores
- `step_final_summary_main` post-core exit mapping preserved (`rc in {2,3}` passthrough; sentinel probe returns `0`)
- Wrapper child env test: `ctx.subprocess_env()` retains `PATH`/`HOME` plus wrapper overrides after normalized-wins merge build
- Regression: symlinked `DESIGN_TMPDIR` in session env resolves identically in `ctx.design_tmpdir` and publish `--design-tmpdir` argv (normalized merge wins over stale rehydrate)
- `step5c_core` / `step_final_summary_core` / `validator_autofix_main`: `ctx` built after rehydrate, normalized tmpdir, and `quiet_init`; not before rehydrate or pre-resolve
- `claude_pid` used for publish/marker when env write removed
- Keep `*_core` restore tests

### UPDATED: `python/test_plan_quality.py`

- Argv `--design-tmpdir` wins over env when building `ctx` in `validate_plan_main` / `check_plan_size_main` (no validator rehydrate on those paths)
- `validate_plan_main` / `check_plan_size_main` do **not** call `_rehydrate_validator_env`; standalone invocations preserve today's `DESIGN_TMPDIR` / `SITE` precedence
- `check_plan_size_main` drift multiple: invalid/non-positive `LARCH_DESIGN_DRIFT_MULTIPLE` falls back to `2` (same `isdigit` + `> 0` logic as today); lock with regression test
- `validator_autofix_main` builds `ctx` only after validate/resolve; `ctx.design_tmpdir` matches resolved path used by `_validator_pause_save`
- `validator_autofix_main` reads `SUMMARY_OUTCOME` / `ISSUE_NUMBER` / `REPO` through `ctx` from rehydrate merge
- `_validator_operator_cancel_audit` / `_validator_pause_save` receive post-resolve `ctx`
- `_capture_main` still mutates live `LARCH_QUIET_DISABLE` (autofix stdout capture regression)
- `ctx=None` fallback preserves legacy env reads
- No `revise_plan_with_waterfall_main` ctx adoption tests (deferred)

### UPDATED: `python/test_design_summary.py`

- `render_final_summary_main`: explicit `--design-tmpdir` / `--issue-number` / `--session-id` win over stale ambient env
- Legacy callers without new flags still use env fallback
- Converted-core subprocess args from lifecycle tests exercise argv-wins path

## Edge cases

- Empty env values keep current defaults.
- Invalid numeric env values do not crash converted flows unless the old path already crashed.
- `Ctx` snapshots at build time; later process-env mutations do not affect an existing `ctx` (except helpers intentionally reading live env: quiet mirrors, `_capture_main` quiet-disable).
- Caller dict mutation after `from_mapping` does not mutate frozen `Ctx`.
- Rehydrated allowlist alone must never back `subprocess_env()`.
- Normalized `design_tmpdir` must be in the `ctx` mapping before postplan/shared-body use; drafter validates at main entry, not only pre-shared-body; stale `env` from rehydrate must not overwrite resolved path in merge.
- In-process legacy callees may still read `os.environ`; keep temporary writes with comment until converted.
- `ctx is None` must preserve today's `os.environ` behavior at unconverted call sites (including deferred `launch_review_main` and `revise_plan_with_waterfall_main`).
- `CLAUDE_PID`: typed `ctx.claude_pid` with parse/inherit fallback when env write is removed.
- `codex_present` / `cursor_present`: empty string is valid; do not coerce through `bool_value`.
- `resolve_model_args`: `ctx.contains` distinguishes absent primary key (fall through to plugin key) from present-but-empty (reject blank).
- Failed-publish-tail render/emit runs before `result_env` parse; must use explicit default path, never ambient `FINAL_SUMMARY_PATH`.
- Argv CLI overrides must not be shadowed by early `ctx` built before argparse or before `vars(args)` merge.
- `render_final_summary_main` argv-wins: explicit `--design-tmpdir` must not lose to stale `DESIGN_TMPDIR` env when cores pass IPC-threaded values.
- `validate_plan_main` / `check_plan_size_main` must not inherit validator rehydrate allowlist side effects.
- `validator_autofix_main` pause path must see resolved `ctx.design_tmpdir`, not pre-resolve rehydrate snapshot.
- After `quiet_init` in cores, contract output is on fd 3; direct-core tests must not assert contract strings on stdout.

## Failure modes

- Stale `ctx` after intentional mid-flow env mutations → snapshot after hydration or explicit override parameters; defer broad launch-path conversion this PR.
- `from_mapping` retaining caller dict reference → silent mutation of frozen ctx.
- Stale `env` overwriting normalized `DESIGN_TMPDIR` in merge → divergent `ctx.design_tmpdir` vs publish argv on symlink paths.
- Removing env write without threading into `_shared_step2b_postplan_body` → stale/unresolved `DESIGN_TMPDIR` in postplan.
- Drafter deferring validate/resolve or omitting `design_tmpdir=` at shared-body call → unvalidated tmpdir in sentinel/pause/vendor paths.
- Building `ctx` before rehydrate/normalized tmpdir/`quiet_init` → wrong log routing or stale paths.
- `validator_autofix_main` building `ctx` before validate/resolve → `_validator_pause_save` sees wrong tmpdir on symlink/validation fixes.
- Applying `_rehydrate_validator_env` to standalone `validate_plan_main` / `check_plan_size_main` → changed `DESIGN_TMPDIR` / `SITE` precedence on harness calls.
- `degraded_tools_gate_main` building `ctx` from `os.environ` without `vars(args)` → explicit `--codex-present` ignored.
- Calling `quiet_init` in both `step_final_summary_main` and core → double init or missing fd4 routing on direct core calls.
- Partial rehydrate dict as `raw_env` → child subprocess missing `PATH`/auth vars.
- Double `ctx` build in `*_main` and `*_core` → divergent snapshots.
- Argv-first main building `ctx` before argparse → CLI tmpdir override ignored.
- `ctx.int_value` replacing drift-multiple `isdigit`/else-2 logic → altered plan-size gate thresholds.
- Converting `resolve_model_args` without `contains` → broken model-selection precedence.
- Missing `str_value` → ad hoc `raw_env` reads or string literals for rehydrate keys.
- Routing `_capture_main` quiet-disable through `ctx` → `AUTOFIX_STATUS` escapes StringIO capture.
- `repr(ctx)` leaking secrets → redact `raw_env` in repr.
- Unbounded agents `_main` conversion → scope creep beyond incremental hotspot goal.
- Dead `ctx` in `revise_plan_with_waterfall_main` → snapshot without threaded reads.
- Omitting `step_final_summary_main` exit mapping → wrong rc on re-entry/resume.
- Removing `FINAL_SUMMARY_PATH` env IPC without updating all three emit/render call-site families → broken final-summary emission.
- `render_final_summary_main` env-only reads after IPC removal → wrong tmpdir/issue metadata when explicit args passed.
- Leaving direct-core tests on `capsys` after quiet_init move → false failures on contract KVs/markers.

Mitigation: pinned agents owners, per-main ctx merge recipes, normalized-wins merge order, `vars(args)` for degraded-tools gate, `contains` for model precedence, single core quiet owner with rehydrate-first ordering, independent `raw_env` copy, argv-after-parse ctx merge, explicit drift fallback, `str_value` for rehydrate keys, drafter entry validate/resolve with full caller inventory, explicit `final_summary_path` inventory, fd-3 contract test migration, `_capture_main` quiet exception, argv-first `render_final_summary_main`, explicit `ctx=None` fallback, defer waterfall main, targeted regression tests.

## Testing strategy

Run:

```bash
make py-lint
make py-test
make lint
```

Targeted:

python3 -m pytest python/test_ctx.py python/test_agents.py python/test_design_lifecycle.py python/test_plan_quality.py python/test_design_summary.py

Also run narrower failures from the first full pass.

Migrate every direct `step5c_core` / `step_final_summary_core` contract assertion (`PUBLISH_RC=`, `LARCH_FINAL_SUMMARY_*` markers, machine rows) off `capsys` stdout to fd-3 contract capture (`capture_contract_stream_to_paths` or the inherited-quiet pipe pattern in `test_step5c_main_machine_rows_visible_under_inherited_quiet`), not only add new quiet-routing smoke tests.

## Acceptance

- `python/ctx.py` defines a frozen `Ctx` with `from_env` / `from_mapping`, typed fields backed by `config.ENV_*`, and `str_value` / `bool_value` / `int_value` / `contains` / `subprocess_env` helpers. `raw_env` is an independent copy; `repr` does not leak secrets.
- `Ctx` is built once at the pinned hotspot boundaries: `model_args_main`, `degraded_tools_gate_main`, `run_external_agent_main` (`agents.py`); `step5c_core`, `step_final_summary_core` (`design_lifecycle.py`); `validate_plan_main`, `check_plan_size_main`, `validator_autofix_main` (`plan_quality.py`).
- Converted helpers read env via `ctx` (typed fields or narrow helpers), not raw `os.environ`; every converted helper keeps a `ctx=None` legacy fallback that preserves today's behavior at unconverted call sites.
- In-process IPC env writes in `design_lifecycle.py` (`SUMMARY_OUTCOME`, `FINAL_SUMMARY_PATH`, normalized `DESIGN_TMPDIR`) are replaced by explicit parameter / return passing; subprocess-config env setup and `*_core` `os.environ` save/restore are preserved.
- `.sh` env-file wire format is unchanged; `config.py` stays name-only (no parsing logic).
- `make py-lint`, `make py-test`, and `make lint` pass; `python/test_ctx.py` covers Ctx parsing, snapshot immutability, `from_mapping` input-copy, secret redaction, and `contains` absent-vs-empty membership.

review_status: complete
rounds_completed: 5
diff_added: 640
diff_deleted: 160
mechanical_churn: false
diff_lines: 800
