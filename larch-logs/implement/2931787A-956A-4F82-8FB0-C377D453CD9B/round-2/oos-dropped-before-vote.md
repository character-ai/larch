### OOS_1: [OUT_OF_SCOPE] Q/A redispatch skips prelaunch baseline refresh
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Q/A redispatch skips prelaunch refresh when `answers_file` is set. Stale prelaunch across Q/A cycles on the external path may skew `recovery-paths` deltas.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Refresh or validate baseline on redispatch when tree may have changed.

### OOS_2: [OUT_OF_SCOPE] Post-dispatch emits hardcoded strings instead of `config.py` literals
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Post-dispatch emits hardcoded strings instead of `config.py` literals. Config and runtime strings can drift during future edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Import and emit POST_DISPATCH_* constants from config.py.

### OOS_3: [OUT_OF_SCOPE] `commit_route_main` success allow-list omits `noop`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `commit_route_main` return allow-list omits noop `CommitRouteOutcome`. A future refactor returning the noop string could incorrectly exit 1.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add noop to explicit success allow-list for clarity.

### OOS_4: [OUT_OF_SCOPE] `_capture_prelaunch_porcelain` partial-baseline idempotency (pre-existing)
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-dyn-dispatch-telemetry-output.txt, dyn-dyn-skill-wires-output.txt
- **Severity**: important
- **Concern**: `_capture_prelaunch_porcelain` treats a lone `step2-prelaunch-porcelain.nul` as complete and returns 0 without ensuring `step2-prelaunch-content-digests.txt` or `step2-prelaunch-index.env` exist. A crash between porcelain and digest capture can leave a partial baseline; `implement recovery-paths` may derive wrong or empty pathspecs on claude-fallback paths. Moving capture into the `run_dispatch_main` post-`claude_fallback` hook makes this partial-artifact path more likely.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Treat the baseline as complete only when porcelain, digests, and index env all exist and are readable; otherwise re-capture.

### OOS_5: [OUT_OF_SCOPE] `recovery-metadata.json` predicate mismatch (pre-existing)
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-dyn-dispatch-telemetry-output.txt
- **Severity**: latent
- **Concern**: `_run_step4_recovery_recompute` gates on `recovery-metadata.json.is_file()`, while `_run_step4_commit_leg` requires `_path_readable_nonempty`. A zero-byte or corrupt metadata file can skip recompute logic yet fall through to the ordinary implementation commit branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Use the same `_path_readable_nonempty` check in both sites.

### OOS_6: [OUT_OF_SCOPE] Recovery recompute failure missing `BAIL_REASON` wire token (pre-existing)
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-dyn-dispatch-telemetry-output.txt, dyn-dyn-skill-wires-output.txt
- **Severity**: important
- **Concern**: When `_run_step4_recovery_recompute` fails inside `_derive_pathspec_via_recovery_paths` (postlaunch capture or `recovery-paths` CLI failure, distinct from scope-check), the composite returns a bare non-zero exit with no `BAIL_REASON` or `NEXT_ACTION`. SKILL Step 3 routes that to invalid-envelope handling with `STALL_STEP=4`, misclassifying a Step 2 recovery failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Emit a wire token (for example `BAIL_REASON=recovery-paths-failed`) on recovery-paths/git failures, mirroring the scope-check path.

### OOS_7: [OUT_OF_SCOPE] `rebase-checkpoint-routing.md` missing unified routing table shape
- **Reviewer(s)**: dyn-dyn-skill-wires-output.txt
- **Severity**: nit
- **Concern**: The plan called for one unified routing table plus an explicit input-source note (`1.r` = Step 0 envelope; `4.r` = Step 3 composite stdout; etc.). The file still carries separate absorbed-`1.r` and folded-probe sections without the consolidated table/note the acceptance criteria describe. Behavior is documented, but the planned doc shape is incomplete.
- **Suggested revisions (informational for voters; coder decides)**:

---

**Merge notes (brief):**
- **FINDING_1** subsumes source **FINDING_18** (Cursor carve-out context) and **FINDING_27**.
- **FINDING_2** kept in-scope; OOS duplicates (**21**, **28**, **36**) → **FINDING_15** per OOS separation rule.
- **FINDING_3** in-scope; OOS duplicates (**23**, **29**, **35**) → **FINDING_17**.
- **FINDING_5** in-scope; OOS duplicates (**22**, **30**) → **FINDING_16**.
- **FINDING_10** subsumes **FINDING_13** and **FINDING_19** (telemetry / external-path token window).
- **FINDING_13** (aggregator ID) subsumes **FINDING_20**, **25**, **31**, **32** (`REPO_ROOT` cross-fence).
- Source **FINDING_12–17** from `cursor-specialist-edge-cases-output.txt` are coverage enumerations without stated defects; not promoted to findings.

