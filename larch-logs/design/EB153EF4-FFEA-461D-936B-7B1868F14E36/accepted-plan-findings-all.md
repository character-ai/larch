### FINDING_1: Continue-tail lacks non-interactive degraded-gate routing
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: important
- **Concern**: The absorbed degraded-tools gate does not specify how bootstrap distinguishes interactive from non-interactive runs. Both-down non-interactive runs may emit `DEGRADED_PROMPT_REQUIRED=true`, skip 1.r, and halt waiting for an operator prompt.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Wire the same non-interactive signal used elsewhere (`LARCH_SKILL_NON_INTERACTIVE` or a forwarded `bootstrap invoke` flag through `step-0-bootstrap.sh`). In bootstrap: both-down + non-interactive → log to `execution-issues.md`, write `.degraded-tools-gate-prompted`, run 1.r; both-down + interactive + no sentinel → `DEGRADED_PROMPT_REQUIRED=true` and skip 1.r. Retain the SKILL non-interactive rule for the prompt bounce path.
  - From Cursor-Innovation: Document and test LARCH_SKILL_NON_INTERACTIVE (or equivalent) in the continue-tail helper


### FINDING_2: Post-preflight directive still routes through standalone 1.r
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: The top-level anti-halt directive still tells the orchestrator to continue to Step 1.r after `ROUTE=continue`, conflicting with the intended direct Step 0 to Step 2 path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Update this directive in the plan so it routes from the Step 0 envelope: ROUTE=continue proceeds to Step 2, and only conflict bail malformed routes load the rebase reference.


### FINDING_3: Rebase macro harness still pins standalone 1.r
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-envelope-taxonomy, Cursor-dyn-deletion-reference-sweep, Codex-dyn-deletion-reference-sweep
- **Severity**: important
- **Concern**: The plan removes the standalone prompt-side 1.r rebase probe, but `scripts/test-implement-rebase-macro.sh` still requires that old SKILL.md launcher call. Required checks may fail after the SKILL edit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add scripts/test-implement-rebase-macro.sh to the plan; replace the 1.r SKILL-call assertions with absorbed-bootstrap assertions, while keeping direct-call assertions for 4.r, 7.r, and 7a.r.
  - From Cursor-Innovation: Add harness retarget to bootstrap-absorbed 1.r and list it in the testing strategy
  - From Codex-Pragmatic: Include `scripts/test-implement-rebase-macro.sh` and its .md contract in the plan; change the 1.r assertions to pin the absorbed `python/bootstrap.py` probe invocation while keeping the 4.r, 7.r, and 7a.r pins
  - From Cursor-Requirements: Add an explicit file section to update the harness so 1.r is asserted as bootstrap-internal (or zero SKILL launcher calls) while keeping 4.r/7.r pins
  - From Codex-Requirements: Update the harness to expect no SKILL.md 1.r launcher call, and assert python/bootstrap.py invokes rebase-checkpoint-probe.sh with 1.r plan materialization and --forked-target. Keep 4.r and 7.r assertions.
  - From Cursor-dyn-envelope-taxonomy: Add scripts/test-implement-rebase-macro.sh to the plan (drop the 1.r SKILL pin; assert 1.r is absorbed via bootstrap or reference the new Step 0 routing rows)
  - From Cursor-dyn-deletion-reference-sweep: Add `### UPDATED: scripts/test-implement-rebase-macro.sh` (and sibling `.md`): drop the SKILL.md 1.r launcher pin; assert absorbed 1.r via `python/bootstrap.py` (or envelope docs) instead
  - From Codex-dyn-deletion-reference-sweep: Update the harness to stop requiring the SKILL.md 1.r launcher call, assert the absorbed 1.r probe in python/bootstrap.py, and keep the existing 4.r and 7.r prompt-side assertions


### FINDING_8: Missing ROUTE handling conflicts with degraded prompt bounce
- **Reviewer(s)**: Cursor-dyn-envelope-taxonomy
- **Severity**: important
- **Concern**: The SKILL routing row treats missing or malformed `ROUTE` after the continue-tail as rebase failure. The interactive both-down path intentionally skips 1.r and emits `DEGRADED_PROMPT_REQUIRED=true`, so `ROUTE` may be absent on a valid prompt path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-envelope-taxonomy: Qualify row 3: only treat missing/malformed ROUTE as rebase failure when DEGRADED_PROMPT_REQUIRED is not true (or when the absorbed tail actually ran 1.r)


### FINDING_10: Structure harness still requires deleted degraded-gate wrapper files
- **Reviewer(s)**: Cursor-dyn-deletion-reference-sweep, Codex-dyn-deletion-reference-sweep
- **Severity**: important
- **Concern**: The plan deletes `step-0-degraded-gate.sh` and its `.md`, but `scripts/test-implement-structure.sh` still checks the wrapper sibling and executable list. The structure test may fail after the deletion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-deletion-reference-sweep: Extend the `### UPDATED: scripts/test-implement-structure.sh` step to remove `'step-0-degraded-gate'` from the `wrappers` list (line 127), not only the launcher registry (line 94) and `require()` pins (line 241)
  - From Codex-dyn-deletion-reference-sweep: Remove step-0-degraded-gate from the wrappers sibling/executable list while keeping the planned bootstrap.py replacement assertions


### FINDING_11: Fence-shape expected count is not updated
- **Reviewer(s)**: Cursor-dyn-deletion-reference-sweep
- **Severity**: important
- **Concern**: Removing the degraded-gate fence and standalone 1.r fence drops two new-shape fences, but `scripts/test-implement-fence-shape.sh` still hard-codes `EXPECTED_NEW=32`. The fence-shape harness may fail under required lint shards.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-deletion-reference-sweep: Add `### UPDATED: scripts/test-implement-fence-shape.sh` setting `EXPECTED_NEW` to 30 (and update sibling `.md` if it documents the count); add `make test-implement-fence-shape` to the testing strategy




### FINDING_1: Non-interactive degraded mode can block unattended runs
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: Continue-tail non-interactive detection relies on `LARCH_SKILL_NON_INTERACTIVE`, but `/implement` may not set it. Autonomous, `claude -p`, cron, eval, subagent, or loop runs can be treated as interactive and routed to `DEGRADED_PROMPT_REQUIRED=true`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Mirror skills/shared/external-reviewers.md:37 in bootstrap (or forward an explicit --non-interactive from step-0-bootstrap.sh when LARCH_SKILL_NON_INTERACTIVE=true). Do not rely on LARCH_SKILL_NON_INTERACTIVE alone unless the wrapper sets it for every non-interactive implement entrypoint.
  - From Cursor-Innovation: Forward the existing SKILL non-interactive predicate via step-0-bootstrap.sh/bootstrap invoke (env flag or explicit argv) and gate both-down prompt on it; add test for both-down non-interactive auto-proceed without DEGRADED_PROMPT_REQUIRED
  - From Cursor-Pragmatic: Both-down autonomous / claude -p / eval runs can be misclassified as interactive, bootstrap emits DEGRADED_PROMPT_REQUIRED=true, and Step 0 blocks on AskUserQuestion instead of logging and proceeding to 1.r Detect non-interactive mode with the same predicate as today (subagents, claude -p, cron, eval, autonomous runs, <<autonomous-loop>>); do not rely on LARCH_SKILL_NON_INTERACTIVE unless step-0-bootstrap.sh also starts exporting it


### FINDING_2: Degraded explanation block is lost or reconstructed incorrectly
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: important
- **Concern**: The absorbed degraded gate can strip the full `DEGRADED_EXPLANATION_BEGIN/END` block or replace it with short state tokens. Interactive prompts and non-interactive notices can lose required operator context.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Have bootstrap continue-tail relay the explanation block to stderr (or stdout outside ROUTING_KEYS) during degraded handling; keep envelope keys for routing only. Update SKILL degraded-prompt row to lift that block instead of reconstructing from states.
  - From Cursor-Innovation: Emit the explanation block on stderr (visible via step-0-bootstrap) or replay it in orchestrator-visible output for one-down and non-interactive paths; do not rely on stdout capture alone
  - From Cursor-Innovation: Forward the gate explanation block through stderr or a replay contract and present that verbatim before AskUserQuestion; use CODEX_STATE/CURSOR_STATE only as envelope metadata not as a substitute explanation


### FINDING_3: Malformed or missing BOTH_DOWN can be misclassified
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The continue-tail plan lacks the existing `BOTH_DOWN_SEEN` fail-closed guard. Empty or malformed gate output can be treated as one-down or as a non-interactive both-down auto-proceed case.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Port the BOTH_DOWN_SEEN semantics from skills/design/scripts/design-step0-degraded.sh: treat unseen/empty BOTH_DOWN as both-down for interactive prompt routing; restrict auto-proceed branches to exact false/true only.


### FINDING_4: Step 0 prose still describes prompt-side 1.r and degraded-gate work
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: `skills/implement/SKILL.md` can remain stale after fence removal. It may still tell the orchestrator to run 1.r as a prompt-side Bash probe, branch on process rc, or keep degraded-gate prose that should now route from the bootstrap envelope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Split macro routing: 1.r reads ROUTE/REBASE_RC/PHANTOM_* from bootstrap stdout; 4.r/7.r/7a.r keep direct probe fences. Drop the universal one-foreground-Bash-per-row claim for 1.r.
  - From Cursor-Innovation: Update the macro to carve out 1.r: envelope ROUTE/REBASE_RC from bootstrap stdout not probe process rc; load rebase-checkpoint-routing.md from envelope keys; keep foreground Bash wording for 4.r 7.r 7a.r only
  - From Cursor-Requirements: Replace the degraded-gate block with envelope-only routing keyed on DEGRADED_PROMPT_REQUIRED / CODEX_STATE / CURSOR_STATE; delete the entire pre-implementation 1.r subsection (header, macro paragraph, and fence); route happy path solely via ROUTE=continue in the Step 0 routing table.


### FINDING_5: Bootstrap filtering can drop continue-tail routing and PHANTOM telemetry
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-dyn-envelope-schema-drift
- **Severity**: important
- **Concern**: `invoke_main`, `_emit_final`, and `_filtered_envelope` can emit only hardcoded routing keys. New continue-tail fields or stdout-only `PHANTOM_*` telemetry can be lost before the orchestrator sees them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Run continue-tail after _phase_coder (with resume coder restore first), populate BootstrapState fields, extend _emit_final to emit the new keys, then keep PHANTOM_* stdout-only via a separate advisory allowlist.
  - From Cursor-Innovation: After building the routing envelope append parsed PHANTOM_* lines from the raw capture to sys.stdout (or add an advisory stdout allowlist pass-through); keep PHANTOM_* out of ROUTING_KEYS and bootstrap-routing.env
  - From Cursor-dyn-envelope-schema-drift: Change bootstrap invoke to write filtered keys to bootstrap-routing.env only and emit routing KVs plus trailing PHANTOM_* (and any other advisory tail) on stdout; add an explicit _invoke_main step in the plan


### FINDING_6: Continue-tail can run before resume coder restoration
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: If the absorbed tail runs inside `run_bootstrap` before resume routing is restored, `--mode resume` can see an empty coder and skip degraded gate plus 1.r on dirty-tree resume.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Implement the absorbed tail in invoke_main immediately after _preserve_resume_routing (and before _filtered_envelope or merge tail KVs into the envelope after restore); add a regression test that resume with prior coder runs gate and 1.r without rerunning _phase_coder


### FINDING_7: New absorbed-tail tests can be skipped by make target filters
- **Reviewer(s)**: Codex-Pragmatic, Codex-Requirements, Cursor-dyn-test-calibration
- **Severity**: important
- **Concern**: Planned degraded-gate and 1.r bootstrap tests may not match existing `pytest -k` selectors in the make targets. Acceptance checks can pass without exercising the new absorbed paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Update the test-implement-bootstrap or test-implement-bootstrap-invoke filters to include the new degraded/rebase/absorbed-tail test names, or require those tests to match existing selected substrings
  - From Codex-Requirements: Update the plan to either adjust the Makefile selectors for the new degraded/rebase tests or require test names that match the existing selectors.
  - From Cursor-dyn-test-calibration: Extend the Makefile -k patterns for the three bootstrap targets (or add a dedicated target) and name new tests to match, e.g. test_invoke_absorbed_degraded_gate_* / test_invoke_absorbed_1r_* / test_parse_routing_degraded_prompt_required.


### FINDING_8: REBASE_RC must be synthesized for absorbed 1.r routing
- **Reviewer(s)**: Codex-dyn-envelope-schema-drift
- **Severity**: important
- **Concern**: The plan lists `REBASE_RC` as a relayed routing KV, but the probe emits no such KV. Since bootstrap rc is forced to 0, conflict and bail routing can lose the old process-rc contract unless bootstrap synthesizes `REBASE_RC`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-envelope-schema-drift: State that bootstrap synthesizes REBASE_RC from the probe subprocess return code, then assert it for conflict/bail/unexpected-rc bootstrap tests.


### FINDING_9:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/scripts/step-0-degraded-gate.sh:1-46, skills/implement/scripts/step-0-degraded-gate.md:1-21
- **Concern**: [SCOPE-REDUCTION] Deleting the degraded-gate wrapper is unnecessary for the bootstrap absorption. Scenario: The feature only needs SKILL.md to stop calling this wrapper; removing a shipped runtime-surface script can break existing script-path consumers without improving the one-call Step 0 happy path
- **Proposed resolution**: Keep the files as an uncalled compatibility surface or leave them unchanged; remove only the SKILL.md call and related registry assertions needed for the new bootstrap route


### FINDING_10:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/step-0-degraded-gate.sh:1-46; skills/implement/scripts/step-0-degraded-gate.md:1-21
- **Concern**: [SCOPE-REDUCTION] Plan deletes the retired degraded-gate wrapper instead of only removing its prompt-side call. Scenario: The feature only needs the happy path to use one Step 0 Bash call. Deleting a shipped runtime-surface wrapper expands blast radius and can break manual or internal callers without improving the acceptance path.
- **Proposed resolution**: Keep the wrapper files as legacy compatibility surfaces or leave them untouched. Update SKILL.md and tests so Step 0 no longer invokes or requires the wrapper on the happy path.


### FINDING_11:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/scripts/step-0-degraded-gate.sh:1-46; skills/implement/scripts/step-0-degraded-gate.md:1-21
- **Concern**: [SCOPE-REDUCTION] Plan deletes the degraded-gate wrapper instead of only removing the prompt-side call. Scenario: The issue only requires one Step 0 Bash call on the /implement happy path; deleting a shipped runtime script can break direct callers while adding no correctness benefit
- **Proposed resolution**: Keep the sh/md as compatibility surface, remove only the SKILL.md call and registry pin, or defer deletion to a separate issue



