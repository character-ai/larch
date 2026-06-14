# Review Round 1

- Mode: `diff`
- 18 accepted, 10 rejected (4 neutral)

## Accepted Findings

### FINDING_11: correctness: python/agents.py:3369-3384
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] _validate_codex_add_dir resolves output.parent with strict=True before any parent directory is created. Direct CLI use with a new --output path can crash with FileNotFoundError instead of a clean validation exit. Ensure output parent exists or handle FileNotFoundError and return exit 2 with a clear error.
- **Suggested revision**: Address the concern above.


### FINDING_14: correctness: python/agents.py:2928-2933
- **Reviewer**: codex-specialist-edge-cases-output.txt
- **Concern**: [important] _review_render_specialist_prompt ignores renderer failures and returns stdout anyway. A missing or invalid --agent-file launches a reviewer with an empty prompt and can produce plausible but meaningless output. Check result.returncode, surface stderr/stdout diagnostics, and fail prompt resolution before launching.
- **Suggested revision**: Address the concern above.


### FINDING_15: risk-integration: python/agents.py:2710-2730
- **Reviewer**: codex-specialist-edge-cases-output.txt
- **Concern**: [important] Cursor review usage is not appended to the active vendor token ledger. After a Cursor reviewer consumes tokens, LARCH_TOKEN_BUDGET_CAP_REVIEW can undercount usage and launch later reviewers past the cap. Call python/cli.py token record-vendor cursor with parsed usage and raw=cursor_review, while keeping the token-record sidecar.
- **Suggested revision**: Address the concern above.


### FINDING_17: correctness: python/agents.py:3540-3572
- **Reviewer**: codex-specialist-edge-cases-output.txt
- **Concern**: [latent] Cursor post-processing rewrites output directly instead of atomically replacing it. An interruption or write failure during extraction can leave collectors with truncated or empty output despite valid raw JSON. Write to a temp file in the output directory and replace output atomically after successful write.
- **Suggested revision**: Address the concern above.


### FINDING_19: risk-integration: scripts/test-collect-agent-retry.sh:733-739
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] collect-agent-results.sh rejects retired shell OUTER_LAUNCHER paths but the retry harness has no fixture for that branch. A refactor could remove or break retired-path fail-closed behavior without any harness failure. Add a case that builds the retired launcher path from components and asserts Retry metadata invalid: retired review OUTER_LAUNCHER metadata is no longer accepted.
- **Suggested revision**: Address the concern above.


### FINDING_20: risk-integration: python/test_plan_quality.py
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] plan_quality.py default launchers now use python cli.py agent launch-review but tests never assert that default argv shape. A bad default prefix change could break Gate B revise-waterfall in production while all tests still pass via LARCH_TEST_LAUNCH overrides. Add revise-waterfall tests without env overrides that assert the recorded argv uses sys.executable cli.py agent launch-review --tool codex or cursor.
- **Suggested revision**: Address the concern above.


### FINDING_21: risk-integration: python/test_plan_scout.py
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] plan_scout.py defaults to multi-token Python launch-review argv but tests only cover SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_REVIEW_SH overrides. Default argv regressions such as reverting to a shell script path would not be caught. Add a default-path test that records subprocess argv and confirms cli.py agent launch-review is used not a single-path shell executable.
- **Suggested revision**: Address the concern above.


### FINDING_25: correctness: python/agents.py:2928-2984
- **Reviewer**: codex-specialist-testing-output.txt
- **Concern**: [important] _review_render_specialist_prompt ignores render specialist failures and _review_resolve_prompt treats --agent-file rendering as successful. A missing or invalid agent file can launch Codex or Cursor with an empty prompt instead of failing closed, wasting vendor calls and producing unusable reviewer output. Return rc and stdout from the render helper, check result.returncode, surface diagnostics, and add a failing render specialist pytest.
- **Suggested revision**: Address the concern above.


### FINDING_27: risk-integration: python/agents.py:3387-3395
- **Reviewer**: codex-specialist-testing-output.txt
- **Concern**: [important] Preflight bundles omit OUTER_LAUNCHER=agent launch-review and return before outer metadata is appended. Codex auth/model and Cursor auth/model preflight failures lack canonical retry metadata, contradicting acceptance and preventing collector outer retry validation through the new token. Append outer metadata in _review_write_preflight_bundle or at each preflight call site, including the prompt sidecar when available.
- **Suggested revision**: Address the concern above.


### FINDING_28: correctness: python/agents.py:3540-3572
- **Reviewer**: codex-specialist-testing-output.txt
- **Concern**: [important] Cursor JSON result extraction writes directly to output instead of using an atomic temp-and-replace. An interrupted or partial write can leave collectors with corrupt reviewer output, regressing the explicit atomic extraction contract. Write extracted or degraded content to a temp file in the output directory, then atomically replace output, and add a Cursor post-processing pytest.
- **Suggested revision**: Address the concern above.


### FINDING_29: **correctness** `python/agents.py:3655-3656` — Successful Cursor review launches no longer write the `cursor-status: ok (no stderr emitted during agent run)` sidecar line. Bash always pre-created `${OUTPUT}.sidecar` before launch (`: > "$SIDECAR"`), then appended the marker on `EXIT_CODE == 0`. Python uses `capture_stdout_only=True`, routes stderr to `.diag`, and only appends the marker when `.sidecar` already exists, so the marker is skipped on the common path. **Suggested fix:** Mirror bash by creating/touching `${output}.sidecar` before the retry loop (or appending the ok line to a guaranteed sidecar path) so successful Cursor runs preserve the same sidecar contract collectors and diagnostics expect.
- **Reviewer**: dyn-launcher-parity-output.txt
- **Concern**: - **correctness** `python/agents.py:3655-3656` — Successful Cursor review launches no longer write the `cursor-status: ok (no stderr emitted during agent run)` sidecar line. Bash always pre-created `${OUTPUT}.sidecar` before launch (`: > "$SIDECAR"`), then appended the marker on `EXIT_CODE == 0`. Python uses `capture_stdout_only=True`, routes stderr to `.diag`, and only appends the marker when `.sidecar` already exists, so the marker is skipped on the common path. **Suggested fix:** Mirror bash by creating/touching `${output}.sidecar` before the retry loop (or appending the ok line to a guaranteed sidecar path) so successful Cursor runs preserve the same sidecar contract collectors and diagnostics expect.
- **Suggested revision**: Address the concern above.


### FINDING_31: **security** `python/agents.py:3577-3591` — Cursor empty-result `.diag` writes skip the bash redaction pipeline. The shell launcher piped diag text through `python/cli.py redact tmpdir-paths` and `redact secrets` before writing `${OUTPUT}.diag`; Python writes fields directly from Cursor JSON. Error payloads can carry session paths or secret-like tokens into `.diag`, which then flows into `append-failure` / execution-issues surfaces. **Suggested fix:** Build the diag text into a temp file, run the same `redact tmpdir-paths` and `redact secrets` helpers used elsewhere, then write the redacted output to `${output}.diag`.
- **Reviewer**: dyn-launcher-parity-output.txt
- **Concern**: - **security** `python/agents.py:3577-3591` — Cursor empty-result `.diag` writes skip the bash redaction pipeline. The shell launcher piped diag text through `python/cli.py redact tmpdir-paths` and `redact secrets` before writing `${OUTPUT}.diag`; Python writes fields directly from Cursor JSON. Error payloads can carry session paths or secret-like tokens into `.diag`, which then flows into `append-failure` / execution-issues surfaces. **Suggested fix:** Build the diag text into a temp file, run the same `redact tmpdir-paths` and `redact secrets` helpers used elsewhere, then write the redacted output to `${output}.diag`.
- **Suggested revision**: Address the concern above.


### FINDING_36: **risk-integration** `scripts/collect-agent-results.sh:995-1106` — Review launches now record both `OUTER_LAUNCHER=agent launch-review` and a raw vendor `CMD_JSON`. If a tampered `.meta` strips the three outer fields but keeps `CMD_JSON`, the collector replays through `agent run-external-agent` instead of `agent launch-review`. That bypasses launcher-owned post-processing: Cursor baseline dirty-tree capture/emission, JSON post-processing, sentinel replay, and refreshed outer metadata. The plan called this out as a failure mode; this cutover does not close it for review-shaped retries. **Suggested fix:** after cutover, fail closed on `CMD_JSON` retry when the stored argv is review-shaped (`cursor agent … --mode ask` / `codex exec --sandbox read-only …`) unless `OUTER_LAUNCHER=agent launch-review` is also present, or require outer replay whenever `OUTER_LAUNCHER_PROMPT_FILE=${orig}.prompt` exists.
- **Reviewer**: dyn-retry-cutover-output.txt
- **Concern**: - **risk-integration** `scripts/collect-agent-results.sh:995-1106` — Review launches now record both `OUTER_LAUNCHER=agent launch-review` and a raw vendor `CMD_JSON`. If a tampered `.meta` strips the three outer fields but keeps `CMD_JSON`, the collector replays through `agent run-external-agent` instead of `agent launch-review`. That bypasses launcher-owned post-processing: Cursor baseline dirty-tree capture/emission, JSON post-processing, sentinel replay, and refreshed outer metadata. The plan called this out as a failure mode; this cutover does not close it for review-shaped retries. **Suggested fix:** after cutover, fail closed on `CMD_JSON` retry when the stored argv is review-shaped (`cursor agent … --mode ask` / `codex exec --sandbox read-only …`) unless `OUTER_LAUNCHER=agent launch-review` is also present, or require outer replay whenever `OUTER_LAUNCHER_PROMPT_FILE=${orig}.prompt` exists.
- **Suggested revision**: Address the concern above.


### FINDING_37: **risk-integration** `scripts/collect-agent-results.sh:719-721` — Retired shell launcher metadata is rejected via a `launch-review.sh` case arm, but `scripts/test-collect-agent-retry.sh` does not exercise it. The plan required programmatically constructed retired-path fixtures; the harness only covers `..` traversal (`725`, `821`) and non-canonical executables (`739`), not a composed `scripts` + `launch-review.sh` path. A regex or quoting regression in the retired-path arm could ship without harness signal. **Suggested fix:** add a fail-closed case that builds the retired launcher path from components (as the plan specifies), asserts the exact `retired review OUTER_LAUNCHER metadata is no longer accepted` message, and confirms no retry child is spawned.
- **Reviewer**: dyn-retry-cutover-output.txt
- **Concern**: - **risk-integration** `scripts/collect-agent-results.sh:719-721` — Retired shell launcher metadata is rejected via a `launch-review.sh` case arm, but `scripts/test-collect-agent-retry.sh` does not exercise it. The plan required programmatically constructed retired-path fixtures; the harness only covers `..` traversal (`725`, `821`) and non-canonical executables (`739`), not a composed `scripts` + `launch-review.sh` path. A regex or quoting regression in the retired-path arm could ship without harness signal. **Suggested fix:** add a fail-closed case that builds the retired launcher path from components (as the plan specifies), asserts the exact `retired review OUTER_LAUNCHER metadata is no longer accepted` message, and confirms no retry child is spawned.
- **Suggested revision**: Address the concern above.


### FINDING_38: **risk-integration** `SECURITY.md:221` — The doc says invalid outer metadata fails closed “instead of falling back to `CMD_JSON`.” That is only true when partial outer fields trigger `launch_outer_retry_or_mark` and validation fails. If all `OUTER_LAUNCHER*` fields are removed, the collector still uses the `CMD_JSON` branch (`1003-1106`). The security story overstates protection after the Python cutover. **Suggested fix:** narrow the claim to “partial/invalid outer metadata does not fall back to `CMD_JSON`,” and document that complete removal of outer fields can still reach the inner retry path unless review-shaped `CMD_JSON` is also blocked.
- **Reviewer**: dyn-retry-cutover-output.txt
- **Concern**: - **risk-integration** `SECURITY.md:221` — The doc says invalid outer metadata fails closed “instead of falling back to `CMD_JSON`.” That is only true when partial outer fields trigger `launch_outer_retry_or_mark` and validation fails. If all `OUTER_LAUNCHER*` fields are removed, the collector still uses the `CMD_JSON` branch (`1003-1106`). The security story overstates protection after the Python cutover. **Suggested fix:** narrow the claim to “partial/invalid outer metadata does not fall back to `CMD_JSON`,” and document that complete removal of outer fields can still reach the inner retry path unless review-shaped `CMD_JSON` is also blocked.
- **Suggested revision**: Address the concern above.


### FINDING_7: correctness: python/agents.py:2928-2933
- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: [important] Specialist prompt rendering failures are ignored. --agent-file with an empty or invalid mode can make render specialist fail, but launch-review proceeds with an empty prompt and still starts the external reviewer. Return rc plus prompt from the render helper, check returncode, surface diagnostics, and stop before sidecar or vendor launch on non-zero.
- **Suggested revision**: Address the concern above.


### FINDING_8: correctness: python/agents.py:3387-3395
- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: [important] Preflight bundles publish .done before dirty-tree sidecars. A polling collector can see .done after a Cursor preflight failure and read a missing or stale .dirty-tree before the caller writes the unknown sidecar. Move .done publication out of the shared preflight bundle or write dirty-tree before .done in each preflight caller.
- **Suggested revision**: Address the concern above.


### FINDING_9: correctness: python/agents.py:3643-3656
- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: [important] Cursor review no longer guarantees the .sidecar contract. A successful Cursor launch with no existing sidecar leaves no output.sidecar, breaking consumers and diagnostics that expect the stable sidecar artifact. Create the Cursor sidecar before launch and append wrapper status there while keeping child stderr in .diag.
- **Suggested revision**: Address the concern above.


