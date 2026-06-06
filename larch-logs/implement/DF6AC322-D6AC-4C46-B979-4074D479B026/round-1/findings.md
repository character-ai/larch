### FINDING_1: code-quality: scripts/test-larch-log.sh:150-155
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Explicit dynamic Codex allow clause is not unit-pinned; only integration-tested via write-round harness. Removing scripts/larch-log.sh:89-92 leaves all new tests green because broad *-output* patterns still allow the same files, so the documented contract can silently disappear. Add assert_round_artifact_included cases for representative dynamic Codex include/exclude filenames at the function level.
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: scripts/larch-log.sh:91
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Eight-pattern explicit allow duplicates broad allow semantics at line 100, creating dual-edit maintenance surface. A future sidecar type added only to the broad arm would leave the explicit clause and docs stale even while tests still pass. Add a maintainer comment cross-linking larch-log.md, or narrow the explicit arm to .txt basenames only if sidecars remain covered by the broad arm.
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] architecture: scripts/lib-design-round-artifacts.sh:8-9
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Design vs implement round allowlists treat dyn-* outputs oppositely (deny vs retain). Editors comparing the two files may apply implement retention rules to design staging or vice versa. Document the cross-skill asymmetry in both contract docs when either file is next touched.
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] code-quality: scripts/test-larch-log-write-round.sh:71-99
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Unphased dynamic Codex meta/json lack CMD_JSON and .result stripping assertions that phased fixtures now have. Regression in unphased sidecar redaction would not be caught while phased paths stay covered. Add assert_not_grep/assert_json_result_stripped for unphased dyn-api-contract-codex-output fixtures.
- **Suggested revision**: Address the concern above.

### FINDING_5: **Clause placement** — The explicit dynamic-Codex allow in `round_artifact_included()` sits after all deny clauses (prompt/telemetry, static specialist, vote-prompt, zero-byte placeholders) and before the broad `*-output.txt` allow.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - **Clause placement** — The explicit dynamic-Codex allow in `round_artifact_included()` sits after all deny clauses (prompt/telemetry, static specialist, vote-prompt, zero-byte placeholders) and before the broad `*-output.txt` allow.
- **Suggested revision**: Address the concern above.

### FINDING_6: **Patterns** — Allows only `dyn-*-codex-output.txt`, `dyn-*-codex-output-phase*.txt`, and their `.meta` / `.json` / `.cap-hit` sidecars; no catch-all `dyn-*-codex-output-*.txt`.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - **Patterns** — Allows only `dyn-*-codex-output.txt`, `dyn-*-codex-output-phase*.txt`, and their `.meta` / `.json` / `.cap-hit` sidecars; no catch-all `dyn-*-codex-output-*.txt`.
- **Suggested revision**: Address the concern above.

### FINDING_7: **Exclusions preserved** — `.prompt`, `*-vote-prompt.txt`, and `.events.jsonl` remain excluded via earlier deny arms (case order is correct).
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - **Exclusions preserved** — `.prompt`, `*-vote-prompt.txt`, and `.events.jsonl` remain excluded via earlier deny arms (case order is correct).
- **Suggested revision**: Address the concern above.

### FINDING_8: **Behavior-preserving** — On `main`, these artifacts were already included via `*-output.txt` / `*-output-*.txt`; the new clause documents intent without changing outcomes.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - **Behavior-preserving** — On `main`, these artifacts were already included via `*-output.txt` / `*-output-*.txt`; the new clause documents intent without changing outcomes.
- **Suggested revision**: Address the concern above.

### FINDING_9: **Tests/docs** — `test-larch-log-write-round.sh` adds the planned positive/negative fixtures; companion docs align with the matcher.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - **Tests/docs** — `test-larch-log-write-round.sh` adds the planned positive/negative fixtures; companion docs align with the matcher. Glob semantics were checked for static-vs-dynamic boundaries (`codex-specialist-security-output.txt` denied, `codex-specialist-security-output-phase2.txt` included) and vote-prompt regression (`dyn-api-contract-codex-output-vote-prompt.txt` excluded via `*-vote-prompt.txt` deny before the explicit allow). Omitting retry-suffixed patterns from the explicit clause is correct: no `dyn-*-codex-output-retry*` artifacts exist in the runtime, and any future retry-shaped names would still be covered by the broad `*-output-*.txt` allow.
- **Suggested revision**: Address the concern above.

### FINDING_10: risk-integration: scripts/test-larch-log.sh:150-155
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] test-larch-log.sh direct round_artifact_included probes omit the new dynamic-Codex allow/deny boundary pinned by this change If a contributor removes or misorders the explicit dynamic-Codex clause in round_artifact_included() while leaving broad *-output*.txt allows intact, test-larch-log.sh would still pass its existing scout/events pins and only test-larch-log-write-round.sh would catch the regression Add assert_round_artifact_included probes for dyn-*-codex-output.txt (included), codex-specialist-*-output.txt (excluded), dyn-*-codex-output-vote-prompt.txt (excluded), and dyn-*-codex-output.txt.events.jsonl (excluded) next to the existing round-artifact pins
- **Suggested revision**: Address the concern above.

### FINDING_11: `.meta` sidecars still go through `larch_redact_strip_meta_cmd_json` (CMD_JSON stripped) before commit.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `.meta` sidecars still go through `larch_redact_strip_meta_cmd_json` (CMD_JSON stripped) before commit.
- **Suggested revision**: Address the concern above.

### FINDING_12: `.json` sidecars still go through `larch_redact_strip_json_result` (`.result` stripped).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `.json` sidecars still go through `larch_redact_strip_json_result` (`.result` stripped).
- **Suggested revision**: Address the concern above.

### FINDING_13: All staged artifacts still pass `larch_log_redact_file` (tmpdir + secret scrubbing via `redact-tmpdir-paths.sh` / `redact-secrets.sh`).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - All staged artifacts still pass `larch_log_redact_file` (tmpdir + secret scrubbing via `redact-tmpdir-paths.sh` / `redact-secrets.sh`).
- **Suggested revision**: Address the concern above.

### FINDING_14: New negative harness coverage blocks regressions that would leak `.prompt`, `*-vote-prompt.txt`, or unphased `.events.jsonl` telemetry.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - New negative harness coverage blocks regressions that would leak `.prompt`, `*-vote-prompt.txt`, or unphased `.events.jsonl` telemetry. The bundled Python Step 8 cutover changes are net neutral-to-positive for security: `finalize-state` writes now shell-quote values (`python/finalize.py`), keys are validated on read/write, `quiet_init` / journal append are gated on `_tmpdir_under_allowed_root`, and `emit_result` redacts outbound JSON fields. `gh.pr_create` continues argv-list invocation (no shell interpolation). No injection paths, auth gaps, secret literals, path-traversal regressions, or unsafe deserialization were introduced or amplified by this branch diff.
- **Suggested revision**: Address the concern above.

### FINDING_15: architecture: scripts/larch-log.sh:89-92
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] The explicit dynamic-Codex allow arm is not test-isolated from the broad *-output*.txt allow at line 100. Deleting lines 89-92 leaves all new write-round assertions passing; a future narrow refactor of the broad arm could drop dynamic Codex retention without CI catching loss of the explicit contract anchor. Add assert_round_artifact_included cases in scripts/test-larch-log.sh for dynamic Codex positive basenames and negative prompt/vote-prompt/events shapes.
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: scripts/test-larch-log-write-round.sh:188-192
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Phased dynamic/static Codex sidecar redaction is asserted but unphased dynamic Codex .meta/.json stripping is not. A regression breaking CMD_JSON or .result trimming only on unphased dyn-*-codex-output.txt sidecars would not fail this harness. Add assert_not_grep for dyn-api-contract-codex-output.txt.meta and assert_json_result_stripped for dyn-api-contract-codex-output.txt.json.
- **Suggested revision**: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] architecture: scripts/larch-log.sh:100
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Retry-suffixed dynamic Codex outputs are not in the explicit allow clause or larch-log.md enumeration. Retry shapes rely solely on broad *-output-*.txt patterns; narrowing that arm could drop retry forensics. Intentional per plan since no retry producers exist yet. Revisit when dispatch emits dyn-*-codex-output-retry*.txt; add explicit patterns and fixtures then.
- **Suggested revision**: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] risk-integration: scripts/test-larch-log.sh:150-155
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] No unit-level assert_round_artifact_included pins for dynamic Codex basenames. Integration-only coverage predates this branch; not removed by this diff. Extend assert_round_artifact_included when adding contract pins (see in-scope latent finding).
- **Suggested revision**: Address the concern above.

### FINDING_19: **risk-integration** `python/ship.py:716-723` — `emit_result()` writes the orchestrator contract JSON via `contract_stream()`, then calls `stream.flush()` outside any exception guard. Only `_close_contract_stream()` is wrapped in `suppress(Exception)`; a `BrokenPipeError` or `OSError` from `print()`/`flush()` (common when the Bash-tool stdout pipe closes early) propagates out of `emit_result()` and out of `main()` at line 898, which is not inside the `run_ship` `try/except`. The caller can receive a non-mapped process exit code and a traceback on stderr even when the ship logic already chose a terminal `ShipResult`, breaking the Step 8+ contract of “exit code + single JSON object on stdout.” **Suggested fix:** Treat contract emission as fail-soft: wrap the `print`/`flush` pair in `suppress(BrokenPipeError, OSError)` (or a broad `except Exception` confined to that block), and always return normally so `main()` can still map `config.OUTCOME_EXIT_MAP[result.outcome]`.
- **Reviewer**: dyn-quiet-fds-output.txt
- **Concern**: - **risk-integration** `python/ship.py:716-723` — `emit_result()` writes the orchestrator contract JSON via `contract_stream()`, then calls `stream.flush()` outside any exception guard. Only `_close_contract_stream()` is wrapped in `suppress(Exception)`; a `BrokenPipeError` or `OSError` from `print()`/`flush()` (common when the Bash-tool stdout pipe closes early) propagates out of `emit_result()` and out of `main()` at line 898, which is not inside the `run_ship` `try/except`. The caller can receive a non-mapped process exit code and a traceback on stderr even when the ship logic already chose a terminal `ShipResult`, breaking the Step 8+ contract of “exit code + single JSON object on stdout.” **Suggested fix:** Treat contract emission as fail-soft: wrap the `print`/`flush` pair in `suppress(BrokenPipeError, OSError)` (or a broad `except Exception` confined to that block), and always return normally so `main()` can still map `config.OUTCOME_EXIT_MAP[result.outcome]`.
- **Suggested revision**: Address the concern above.

### FINDING_20: **risk-integration** `python/ship.py:888-891` — The top-level `run_ship` exception handler routes the full traceback through `BreadcrumbWriter().emit()` with default quiet semantics. After `quiet_init()` (lines 884–886), `_quiet_active()` is true, so that traceback is redirected to the quiet log and fd 4 instead of the orchestrator-visible stderr stream. Step 8+ still gets the JSON `INTERNAL_ERROR` envelope, but operators debugging a Python-path failure from Bash tool output will no longer see the traceback that prior tests assert on the non-quiet path (`test_main_emits_json_stdout_on_unexpected_exception`). **Suggested fix:** Emit internal-error tracebacks on the operator diagnostic path explicitly (e.g. `BreadcrumbWriter().emit(..., quiet=False)` for that one site, or `os.write(4, ...)` after quiet init), and add a `main()` integration test that runs with real `quiet_init()` to pin JSON-on-contract-stream plus fd-4 traceback behavior.
- **Reviewer**: dyn-quiet-fds-output.txt
- **Concern**: - **risk-integration** `python/ship.py:888-891` — The top-level `run_ship` exception handler routes the full traceback through `BreadcrumbWriter().emit()` with default quiet semantics. After `quiet_init()` (lines 884–886), `_quiet_active()` is true, so that traceback is redirected to the quiet log and fd 4 instead of the orchestrator-visible stderr stream. Step 8+ still gets the JSON `INTERNAL_ERROR` envelope, but operators debugging a Python-path failure from Bash tool output will no longer see the traceback that prior tests assert on the non-quiet path (`test_main_emits_json_stdout_on_unexpected_exception`). **Suggested fix:** Emit internal-error tracebacks on the operator diagnostic path explicitly (e.g. `BreadcrumbWriter().emit(..., quiet=False)` for that one site, or `os.write(4, ...)` after quiet init), and add a `main()` integration test that runs with real `quiet_init()` to pin JSON-on-contract-stream plus fd-4 traceback behavior.
- **Suggested revision**: Address the concern above.

### FINDING_21: **risk-integration** `python/test_ship.py:573-631` — Every `main()`-level contract test stubs out `quiet_init`, while production always calls it when `--tmpdir` passes `_tmpdir_under_allowed_root()`. That leaves the highest-risk integration surface—the combination of fd 3 JSON delivery, fd 1/2 redirection, and fd 4 diagnostics—untested on the actual `main()` entry path that `/implement` Step 8+ invokes. A regression in inherited `LARCH_QUIET_*` handling or contract-stream selection would pass CI but break orchestration invisibly. **Suggested fix:** Add at least one subprocess-based `main()` test (mirroring `test_quiet_init_routes_contract_and_breadcrumb_fds`) that does not mock `quiet_init`, asserts exactly one JSON line on captured stdout, and asserts traceback/breadcrumb text lands on fd 4 or the quiet log.
- **Reviewer**: dyn-quiet-fds-output.txt
- **Concern**: - **risk-integration** `python/test_ship.py:573-631` — Every `main()`-level contract test stubs out `quiet_init`, while production always calls it when `--tmpdir` passes `_tmpdir_under_allowed_root()`. That leaves the highest-risk integration surface—the combination of fd 3 JSON delivery, fd 1/2 redirection, and fd 4 diagnostics—untested on the actual `main()` entry path that `/implement` Step 8+ invokes. A regression in inherited `LARCH_QUIET_*` handling or contract-stream selection would pass CI but break orchestration invisibly. **Suggested fix:** Add at least one subprocess-based `main()` test (mirroring `test_quiet_init_routes_contract_and_breadcrumb_fds`) that does not mock `quiet_init`, asserts exactly one JSON line on captured stdout, and asserts traceback/breadcrumb text lands on fd 4 or the quiet log.
- **Suggested revision**: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] The dynamic Codex log changes in `scripts/larch-log.sh` and `scripts/test-larch-log-write-round.sh` match the plan: explicit allow is ordered after prompt/telemetry/static-Codex denies and before the broad `*-output.txt` allow; negative fixtures guard `.prompt`, vote-prompt-shaped names, and `.events.jsonl`. No new risk-integration defect identified there—the clause documents behavior already provided by the broad allow.
- **Reviewer**: dyn-quiet-fds-output.txt
- **Concern**: - The dynamic Codex log changes in `scripts/larch-log.sh` and `scripts/test-larch-log-write-round.sh` match the plan: explicit allow is ordered after prompt/telemetry/static-Codex denies and before the broad `*-output.txt` allow; negative fixtures guard `.prompt`, vote-prompt-shaped names, and `.events.jsonl`. No new risk-integration defect identified there—the clause documents behavior already provided by the broad allow.
- **Suggested revision**: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] `python/conftest.py`’s autouse `LARCH_QUIET_DISABLE=1` plus `reset_quiet_state()` correctly fixes pytest runs launched under `run-relevant-checks-captured.sh` (which calls `larch_quiet_init` at line 10); that is a positive integration fix, not a regression.
- **Reviewer**: dyn-quiet-fds-output.txt
- **Concern**: - `python/conftest.py`’s autouse `LARCH_QUIET_DISABLE=1` plus `reset_quiet_state()` correctly fixes pytest runs launched under `run-relevant-checks-captured.sh` (which calls `larch_quiet_init` at line 10); that is a positive integration fix, not a regression.
- **Suggested revision**: Address the concern above.

### FINDING_24: [OUT_OF_SCOPE] `scripts/restore-finalize-state.sh` preserving prewritten `STALL_TRACKING=true` closes a real Python-path stall downgrade risk during Step 18 teardown; also positive, not a finding.
- **Reviewer**: dyn-quiet-fds-output.txt
- **Concern**: - `scripts/restore-finalize-state.sh` preserving prewritten `STALL_TRACKING=true` closes a real Python-path stall downgrade risk during Step 18 teardown; also positive, not a finding.
- **Suggested revision**: Address the concern above.

### FINDING_25: [OUT_OF_SCOPE] `python/ship.py:884-886` now unconditionally assigns `IMPLEMENT_TMPDIR` after the allowlist gate (replacing `setdefault`), addressing the stale-env quiet-log path concern from earlier review rounds.
- **Reviewer**: dyn-quiet-fds-output.txt
- **Concern**: - `python/ship.py:884-886` now unconditionally assigns `IMPLEMENT_TMPDIR` after the allowlist gate (replacing `setdefault`), addressing the stale-env quiet-log path concern from earlier review rounds.
- **Suggested revision**: Address the concern above.

### FINDING_26: **correctness** `python/finalize.py:322-439` — `write_finalize_state()` and `write_finalize_state_merged()` now emit shell-single-quoted values (e.g. `STALL_TRACKING='true'`, `PR_TITLE='…'`), but `scripts/implement-finalize.sh:153-189` still reads values with awk and validates booleans with an exact `true|false` match. After a Python-path stall, `read_state STALL_TRACKING` returns the literal `'true'`, so `require_bool_state` rejects the file and teardown can fail even though stall metadata was written. **Suggested fix:** Keep bash-compatible unquoted scalars for booleans (and optionally all finalize keys), or add a shared unquoting/`truthy` reader in bash and cover Python-shaped `finalize-state.sh` in `scripts/test-restore-finalize-state.sh` / `scripts/test-implement-finalize.sh`.
- **Reviewer**: dyn-finalize-state-output.txt
- **Concern**: - **correctness** `python/finalize.py:322-439` — `write_finalize_state()` and `write_finalize_state_merged()` now emit shell-single-quoted values (e.g. `STALL_TRACKING='true'`, `PR_TITLE='…'`), but `scripts/implement-finalize.sh:153-189` still reads values with awk and validates booleans with an exact `true|false` match. After a Python-path stall, `read_state STALL_TRACKING` returns the literal `'true'`, so `require_bool_state` rejects the file and teardown can fail even though stall metadata was written. **Suggested fix:** Keep bash-compatible unquoted scalars for booleans (and optionally all finalize keys), or add a shared unquoting/`truthy` reader in bash and cover Python-shaped `finalize-state.sh` in `scripts/test-restore-finalize-state.sh` / `scripts/test-implement-finalize.sh`.
- **Suggested revision**: Address the concern above.

### FINDING_27: **correctness** `scripts/restore-finalize-state.sh:79-94` — Stall preservation uses `[ "$existing_stall_tracking" = true ]`, which does not match Python-written `'true'`. When `ship-pr-state.sh` still has `STALL_TRACKING=false` or omits the key, restore can overwrite Python’s stall flags instead of preserving them, defeating the new preservation logic added in this branch. **Suggested fix:** Normalize stall reads with the same truthy rules as `skills/implement/scripts/stall-recovery-report.sh:61-65` (strip optional single quotes before compare), and add a harness case seeding `finalize-state.sh` with `STALL_TRACKING='true'` / `STALL_STEP='gap-fill'`.
- **Reviewer**: dyn-finalize-state-output.txt
- **Concern**: - **correctness** `scripts/restore-finalize-state.sh:79-94` — Stall preservation uses `[ "$existing_stall_tracking" = true ]`, which does not match Python-written `'true'`. When `ship-pr-state.sh` still has `STALL_TRACKING=false` or omits the key, restore can overwrite Python’s stall flags instead of preserving them, defeating the new preservation logic added in this branch. **Suggested fix:** Normalize stall reads with the same truthy rules as `skills/implement/scripts/stall-recovery-report.sh:61-65` (strip optional single quotes before compare), and add a harness case seeding `finalize-state.sh` with `STALL_TRACKING='true'` / `STALL_STEP='gap-fill'`.
- **Suggested revision**: Address the concern above.

### FINDING_28: **correctness** `python/ship.py:382-422` — `_write_ship_state()` atomically rewrites `ship-pr-state.sh` without `STALL_TRACKING` or `STALL_STEP`, so after Python stalls the ship checkpoint drops stall fields that bash `ship-pr.sh` always maintains. `restore-finalize-state.sh` then treats missing ship-pr stall keys as empty/false and gap-fills from `finalize-state.sh`, amplifying the quoting mismatch above and making stall recovery depend on finalize alone. **Suggested fix:** Include `STALL_TRACKING` and `STALL_STEP` in `_write_ship_state()` (set in `_write_terminal_state()` and `_persist_stall_metadata_if_needed()`), mirroring bash `state_set_many STALL_TRACKING true STALL_STEP …`.
- **Reviewer**: dyn-finalize-state-output.txt
- **Concern**: - **correctness** `python/ship.py:382-422` — `_write_ship_state()` atomically rewrites `ship-pr-state.sh` without `STALL_TRACKING` or `STALL_STEP`, so after Python stalls the ship checkpoint drops stall fields that bash `ship-pr.sh` always maintains. `restore-finalize-state.sh` then treats missing ship-pr stall keys as empty/false and gap-fills from `finalize-state.sh`, amplifying the quoting mismatch above and making stall recovery depend on finalize alone. **Suggested fix:** Include `STALL_TRACKING` and `STALL_STEP` in `_write_ship_state()` (set in `_write_terminal_state()` and `_persist_stall_metadata_if_needed()`), mirroring bash `state_set_many STALL_TRACKING true STALL_STEP …`.
- **Suggested revision**: Address the concern above.

### FINDING_29: **architecture** `skills/implement/SKILL.md:1081` — Exit 4 tells the orchestrator to read `RESUME_PHASE` and `CALLER_KIND` from `ship-pr-state.sh` on **both** bash and Python paths and to run the `ship_pr_pre_push` conflict-resolution handoff when those tokens match, but `python/ship.py:382-418` always writes empty `RESUME_PHASE` / `CALLER_KIND`, and `PrePushConflictHandoff` from `python/rebase.py:232-236` is collapsed to a generic `Outcome.STALLED` in `python/ship.py:1011-1017` / `683-684` with no `CONFLICT_FILES` emission or handoff state persistence. `python/README.md:67-69` still documents that Phase 7 driver wiring for this handoff is deferred, so the updated SKILL prose and the Python driver are architecturally inconsistent and the orchestrator cannot mechanically trigger pre-push conflict resolution on the Python path. **Suggested fix:** Either narrow `SKILL.md` Exit 4 so `ship_pr_pre_push` is bash-only until Phase 7, or teach `ship.py` to catch `PrePushConflictHandoff`, persist `RESUME_PHASE` / `CALLER_KIND` / conflict metadata to `ship-pr-state.sh`, emit bash-shaped `CONFLICT_FILES` on the contract stream, and add regression tests; update `python/README.md` to match whichever contract you choose.
- **Reviewer**: dyn-ship-protocol-output.txt
- **Concern**: - **architecture** `skills/implement/SKILL.md:1081` — Exit 4 tells the orchestrator to read `RESUME_PHASE` and `CALLER_KIND` from `ship-pr-state.sh` on **both** bash and Python paths and to run the `ship_pr_pre_push` conflict-resolution handoff when those tokens match, but `python/ship.py:382-418` always writes empty `RESUME_PHASE` / `CALLER_KIND`, and `PrePushConflictHandoff` from `python/rebase.py:232-236` is collapsed to a generic `Outcome.STALLED` in `python/ship.py:1011-1017` / `683-684` with no `CONFLICT_FILES` emission or handoff state persistence. `python/README.md:67-69` still documents that Phase 7 driver wiring for this handoff is deferred, so the updated SKILL prose and the Python driver are architecturally inconsistent and the orchestrator cannot mechanically trigger pre-push conflict resolution on the Python path. **Suggested fix:** Either narrow `SKILL.md` Exit 4 so `ship_pr_pre_push` is bash-only until Phase 7, or teach `ship.py` to catch `PrePushConflictHandoff`, persist `RESUME_PHASE` / `CALLER_KIND` / conflict metadata to `ship-pr-state.sh`, emit bash-shaped `CONFLICT_FILES` on the contract stream, and add regression tests; update `python/README.md` to match whichever contract you choose.
- **Suggested revision**: Address the concern above.

### FINDING_30: **architecture** `skills/implement/SKILL.md:1082` — Exit 6 now instructs the orchestrator, on the Python path, to set `STALL_TRACKING=true` via a key-based rewrite of `finalize-state.sh` after transient retries are exhausted, but `skills/implement/SKILL.md:52` (NEVER #11) forbids prompt-side orchestrator writes to `finalize-state.sh` and names only `scripts/restore-finalize-state.sh` as the sanctioned pre-teardown writer besides the driver itself. That creates two incompatible stall-persistence contracts for the same Python-path failure mode. **Suggested fix:** Move transient-exhaustion stall persistence into `ship.py` (for example by having the driver emit a terminal `STALLED` JSON outcome with enough metadata for `_persist_stall_metadata_if_needed` at `python/ship.py:803-828`), or add a small sanctioned helper script the orchestrator may call for stall-key rewrites, and revise Exit 6 / NEVER #11 so they reference the same writer.
- **Reviewer**: dyn-ship-protocol-output.txt
- **Concern**: - **architecture** `skills/implement/SKILL.md:1082` — Exit 6 now instructs the orchestrator, on the Python path, to set `STALL_TRACKING=true` via a key-based rewrite of `finalize-state.sh` after transient retries are exhausted, but `skills/implement/SKILL.md:52` (NEVER #11) forbids prompt-side orchestrator writes to `finalize-state.sh` and names only `scripts/restore-finalize-state.sh` as the sanctioned pre-teardown writer besides the driver itself. That creates two incompatible stall-persistence contracts for the same Python-path failure mode. **Suggested fix:** Move transient-exhaustion stall persistence into `ship.py` (for example by having the driver emit a terminal `STALLED` JSON outcome with enough metadata for `_persist_stall_metadata_if_needed` at `python/ship.py:803-828`), or add a small sanctioned helper script the orchestrator may call for stall-key rewrites, and revise Exit 6 / NEVER #11 so they reference the same writer.
- **Suggested revision**: Address the concern above.

### FINDING_31: **architecture** `skills/implement/SKILL.md:1066` — Exit 0 still ends with “Otherwise continue by re-invoking `ship-pr.sh` … so the persisted `PHASE` main loop continues,” without a Python-path exception, even though `python/ship.py:476-505` always restarts at `phase="checks"` and never reads persisted `PHASE` from `ship-pr-state.sh` on startup (only partially clarified later at `skills/implement/SKILL.md:1082`). The same “persisted `PHASE` resumes the main loop” wording appears in the Exit 6 re-invoke bullet, so orchestrator docs imply bash-style phase resume on a stateless Python driver that performs a full checks→pr-prep→pr-create→CI pipeline on every invocation. **Suggested fix:** Split the Exit 0/Exit 6 continuation bullets explicitly: bash resumes via persisted `PHASE` in `ship-pr-state.sh`; Python re-invokes the full `ship.py` fence and relies on idempotent phases plus stdout JSON / scoped state keys, not `PHASE` consumption inside the driver.
- **Reviewer**: dyn-ship-protocol-output.txt
- **Concern**: - **architecture** `skills/implement/SKILL.md:1066` — Exit 0 still ends with “Otherwise continue by re-invoking `ship-pr.sh` … so the persisted `PHASE` main loop continues,” without a Python-path exception, even though `python/ship.py:476-505` always restarts at `phase="checks"` and never reads persisted `PHASE` from `ship-pr-state.sh` on startup (only partially clarified later at `skills/implement/SKILL.md:1082`). The same “persisted `PHASE` resumes the main loop” wording appears in the Exit 6 re-invoke bullet, so orchestrator docs imply bash-style phase resume on a stateless Python driver that performs a full checks→pr-prep→pr-create→CI pipeline on every invocation. **Suggested fix:** Split the Exit 0/Exit 6 continuation bullets explicitly: bash resumes via persisted `PHASE` in `ship-pr-state.sh`; Python re-invokes the full `ship.py` fence and relies on idempotent phases plus stdout JSON / scoped state keys, not `PHASE` consumption inside the driver.
- **Suggested revision**: Address the concern above.

### FINDING_32: [OUT_OF_SCOPE] architecture
- **Reviewer**: dyn-ship-protocol-output.txt
- **Concern**: - **architecture** `python/ship.py:763-769` — `_state_file_kv()` reads `ship-pr-state.sh` through `finalize.read_finalize_state()`, which is named and validated for finalize-state semantics; it works today only because both files share `KEY=value` lines, but the cross-file reuse is easy to misread when debugging the new dual-state Python contract (`finalize-state.sh` for stall/PR continuation vs `ship-pr-state.sh` for orchestrator gates). A dedicated ship-state reader would reduce future contract drift.
- **Suggested revision**: Address the concern above.

### FINDING_33: [OUT_OF_SCOPE] architecture
- **Reviewer**: dyn-ship-protocol-output.txt
- **Concern**: - **architecture** `scripts/larch-log.sh:69-88` — The new explicit dynamic-Codex allow clause matches the plan ordering (denies first, narrow allow, then broad `*-output.txt` allow) and deliberately omits retry-suffixed shapes; this is documentation/regression hardening rather than a ship-protocol defect, and the added harness coverage in `scripts/test-larch-log-write-round.sh` looks aligned with the stated contract.
- **Suggested revision**: Address the concern above.

