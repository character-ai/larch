### OOS_1: [OUT_OF_SCOPE] Advertised cache/plot paths use `redact_secrets_only()` and match plan/tests
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: Advertised cache/plot lines use `redact_secrets_only()` via `_print_advertised_artifact()`; tests assert concrete, non-`<TMPDIR>` paths on stdout. Implementation matches the approved plan: CLI try/finally with preserve-on-advertise, render fallback `atexit` cleanup, SessionStart `cleanup run` hook + harness, docs/skills updates, and intentional non-changes to `_plan_quality_commands.py` / `sweep-design-logs.sh`.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_2: [OUT_OF_SCOPE] Deliberate plan exclusions leave known `$TMPDIR` leak sites
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: The original #5923 report still cites leak sites that this PR deliberately leaves unchanged per the approved plan: `python/larch/design/_plan_quality_commands.py:887` (`mkstemp` fallback log leak), and `scripts/sweep-design-logs.sh:17` (scratch/quiet-log writes at `$TMPDIR` top level). Only automatic age-based cleanup via the new SessionStart hook mitigates growth for the latter. Repro scenarios 2 and 3 from the bug report may still leak at `$TMPDIR` top level until a follow-up lands.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_3: [OUT_OF_SCOPE] Nested plot scaffold may linger under preserved CLI temp root
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: latent
- **Concern**: `python/larch/report/report_tokens_plot.py:53` — When plot subprocess fails after creating `larch-report-tokens-plot.*` under the preserved CLI `temp_root`, that nested scaffold remains until the parent `larch-report-tokens.*` dir ages out. Pre-existing plot layout; parent preservation is intentional; nested dirs are removed with the parent during `cleanup run`.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_4: [OUT_OF_SCOPE] Render fallback `atexit` cleanup is unbounded in long-lived processes
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: `python/larch/report/report_tokens_render.py:220-227` — `render(..., temp_root=None)` relies on `atexit` for fallback cleanup, which only runs on normal interpreter shutdown. That matches the plan, but long-lived parent processes (REPL, embedded runners) can accumulate fallback roots until exit; only the CLI path is fully bounded by synchronous preserve/delete plus SessionStart age sweep.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_5: [OUT_OF_SCOPE] Preserve decision depends on fragile `Cache JSON:` trailer coupling
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: `python/larch/report/report_tokens_cli.py:160` — `preserve_holder[0]` depends on `f"Cache JSON: {cache_path}" in analysis` staying in sync with `render()`'s trailer format. It works today because both live in the same change set, but a future render refactor that drops or relocates that line could silently flip preserved runs back to synchronous delete while still printing cache output.
- **Suggested revisions (informational for voters; coder decides)**:

