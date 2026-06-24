## Plan

### Context

Scope stays limited to the rebase checkpoint probe, absorbed Step 1.r relay, `/implement` prompt routing text at all four cited call sites (~158, ~304, ~550, ~734, ~753), and regression coverage.

### Approach

- Emit `CHECKPOINT_NEXT` in the deterministic probe layer.
- Preserve existing `ROUTE=continue|conflict|bail`, `REBASE_*`, `CONFLICT_FILES`, `SKIPPED_*`, and `PHANTOM_*` KVs for compatibility.
- Treat `CHECKPOINT_NEXT=continue` as the only macro no-op predicate at all four call sites, including `7a.r`. Do not use wrapper or probe process exit code for macro skip at any site.
- Treat `CHECKPOINT_NEXT=load-routing`, missing, or malformed as the directive to load `skills/implement/references/rebase-checkpoint-routing.md`, except when `DEGRADED_PROMPT_REQUIRED=true` on the absorbed Step 1.r path (bootstrap skips the 1.r probe; absent `CHECKPOINT_NEXT` is not a rebase failure).
- Consume wrapper exit code, `ROUTE=`, and `REBASE_*` detail only inside `rebase-checkpoint-routing.md` after the macro has decided `CHECKPOINT_NEXT=load-routing` (or equivalent fail-closed load). Never pair `CHECKPOINT_NEXT` with process-rc skip derivation at the macro boundary.
- Keep conflict resolution LLM-side. Do not move conflict-resolution judgment into Python.
- Keep Step 7a's wrapper behavior. It should relay the probe stdout, including `CHECKPOINT_NEXT`, before its final KV tail. Wrapper return code may still reflect probe failure for Bash-fence semantics; orchestrator macro routing for `7a.r` must ignore it and key only on relayed `CHECKPOINT_NEXT=`.
- Step 0 routing-table precedence: evaluate `DEGRADED_PROMPT_REQUIRED=true` before any missing-or-malformed `CHECKPOINT_NEXT` row (mirror today's `ROUTE` carve-out).

### Files to modify/create

### UPDATED: python/push.py

- Add a small deterministic mapping near `_emit_rebase_checkpoint_keys`.
  - `exit_code == 0` emits `CHECKPOINT_NEXT=continue`.
  - `exit_code == 1`, `exit_code == 3`, and unexpected non-zero exits emit `CHECKPOINT_NEXT=load-routing`.
- Emit `CHECKPOINT_NEXT` alongside `ROUTE`.
- Do not emit it before argument parsing succeeds.
- Keep phantom probing only on the successful rebase path.

### UPDATED: python/bootstrap.py

- Add `CHECKPOINT_NEXT` to `ROUTING_KEYS` so absorbed Step 1.r relays it in the Step 0 stdout envelope when the probe runs.
- In `_run_1r_probe`, when malformed probe output is normalized to `ROUTE=bail`, also set `CHECKPOINT_NEXT=load-routing`.
- Do not classify `CHECKPOINT_NEXT` as advisory. It is routing state.
- No change to degraded-gate ordering: when `DEGRADED_PROMPT_REQUIRED=true`, bootstrap still stops before 1.r and does not emit `CHECKPOINT_NEXT` (orchestrator must not treat that absence as `load-routing`).

### UPDATED: python/test_push.py

- Extend existing checkpoint probe tests to assert `CHECKPOINT_NEXT`.
  - Success and skip paths include `CHECKPOINT_NEXT=continue`.
  - Conflict path includes `CHECKPOINT_NEXT=load-routing`.
  - Bail path includes `CHECKPOINT_NEXT=load-routing`.
- Add or extend one unexpected-return-code test if no existing assertion covers that branch.

### UPDATED: python/test_bootstrap.py

- Update `_probe_stdout()` to include `CHECKPOINT_NEXT=continue`.
- Assert `bootstrap.invoke_main()` relays `CHECKPOINT_NEXT=continue` on the absorbed Step 1.r continue path.
- Add or extend coverage for malformed Step 1.r probe output so the normalized envelope includes `CHECKPOINT_NEXT=load-routing`.
- Add or extend a degraded-one-down test asserting `DEGRADED_PROMPT_REQUIRED=true` with no `CHECKPOINT_NEXT` in the envelope (probe skipped); confirm bootstrap does not synthesize `CHECKPOINT_NEXT=load-routing` on that path.

### UPDATED: python/step_7a.py

- No behavior change should be needed if relay stays line-for-line and `push checkpoint-probe` emits `CHECKPOINT_NEXT`.
- Add a focused assertion only if tests reveal the final `REBASE_OUTCOME` tail obscures or drops the relayed `CHECKPOINT_NEXT`.
- Keep the current log-flush-after-probe ordering.
- Do not add orchestrator-facing prose or comments implying wrapper return code drives macro routing; relay stdout is the macro contract.

### UPDATED: skills/implement/SKILL.md

- Update the **Rebase Checkpoint Macro** to define the directive:
  - `CHECKPOINT_NEXT=continue`: continue without loading `rebase-checkpoint-routing.md`.
  - `CHECKPOINT_NEXT=load-routing`: read `rebase-checkpoint-routing.md` and apply conflict or bail routing.
  - Missing or malformed `CHECKPOINT_NEXT`: fail closed by loading `rebase-checkpoint-routing.md`.
  - Absorbed 1.r degraded carve-out: when `DEGRADED_PROMPT_REQUIRED=true`, absent or malformed `CHECKPOINT_NEXT` is not a rebase failure; follow the degraded-tools prompt path instead of loading `rebase-checkpoint-routing.md`.
  - State explicitly that macro skip is `CHECKPOINT_NEXT`-only at all four sites; process exit code is not a macro gate.
- Rewrite Conditional routing reference (~158): gate all four checkpoints on `CHECKPOINT_NEXT=continue|load-routing` (missing/malformed means `load-routing`); for absorbed `1.r`, branch on envelope `CHECKPOINT_NEXT=` and `REBASE_RC=`, not on `step-0-bootstrap.sh` wrapper process exit code; apply the `DEGRADED_PROMPT_REQUIRED` carve-out for absent `CHECKPOINT_NEXT`; drop `ROUTE=continue` skip language and process-rc-plus-`ROUTE` re-derivation prose.
- Update the Step 0 routing table: keep `DEGRADED_PROMPT_REQUIRED=true` row before any missing-or-malformed `CHECKPOINT_NEXT` row; add a row for missing/malformed `CHECKPOINT_NEXT` when `DEGRADED_PROMPT_REQUIRED` is not `true` and the continue-tail attempted 1.r; update the continue-to-Step-2 predicate to use `CHECKPOINT_NEXT=continue`.
- Rewrite Step 1.r routing (~304): orchestrators use `CHECKPOINT_NEXT=`, `ROUTE=`, `REBASE_RC=`, and advisory `PHANTOM_*` from the Step 0 bootstrap envelope; macro branching at 1.r keys on `CHECKPOINT_NEXT` (with the `DEGRADED_PROMPT_REQUIRED` carve-out).
- Collapse Step 4.r and Step 7.r call-site prose (~550, ~734) to "parse `CHECKPOINT_NEXT` from the captured stdout and apply the macro" (drop process-rc-plus-`ROUTE` wording).
- Rewrite Step 7a relay paragraph (~753): replace `ROUTE=continue` skip predicate and all exit-code-for-macro-routing language with `CHECKPOINT_NEXT=continue|load-routing`; state that `7a.r` macro skip is `CHECKPOINT_NEXT`-only; preserve `REBASE_OUTCOME` stream-ordering note only for diagram/status tail KVs.
- Do not add or remove Bash fences.

### UPDATED: skills/implement/references/rebase-checkpoint-routing.md

- Update the contract to include `CHECKPOINT_NEXT=continue|load-routing`.
- Make clear this reference is loaded only when the macro directive says `load-routing`, or when the directive is missing or malformed (subject to the absorbed-1.r degraded carve-out).
- Update Absorbed Step 1.r intro: load this reference when `CHECKPOINT_NEXT=load-routing`; do not treat missing or malformed `CHECKPOINT_NEXT` as rebase failure when `DEGRADED_PROMPT_REQUIRED=true`.
- Update absorbed-1.r orchestrator contract to mention `CHECKPOINT_NEXT=` alongside `ROUTE=` / `REBASE_RC=` for conflict/bail detail inside this file.
- Rewrite Orchestrator contract for direct probe fences (`4.r`, `7.r`, `7a.r`): remove macro-boundary language that tells the orchestrator to branch on wrapper process exit code before loading this reference; state callers reach this section only after `CHECKPOINT_NEXT=load-routing`; for `7a.r`, document that `python/cli.py implement step-7a` relays probe stdout (including `CHECKPOINT_NEXT`) before its diagram tail; drop "preserving the probe exit code for macro routing" language.
- Preserve detailed conflict and bail behavior, Step 1.r absorbed-envelope details, Step 7a wrapper-relay details, and the call-site registry.

### UPDATED: skills/implement/scripts/step-0-bootstrap.md

- Add `CHECKPOINT_NEXT` to the continue-tail routing keys relayed on stdout when present.

### UPDATED: skills/implement/scripts/test-step-7a.sh

- Update the embedded checkpoint-probe stub to emit `CHECKPOINT_NEXT=continue`, `CHECKPOINT_NEXT=load-routing` on conflict, and `CHECKPOINT_NEXT=load-routing` on failure.
- Assert the green path relays `CHECKPOINT_NEXT=continue`.
- Add assertions for conflict or failed modes that relayed `CHECKPOINT_NEXT=load-routing` survives the final KV tail.
- Add a structural assertion that `skills/implement/SKILL.md` Step 7a relay prose does not retain exit-code-for-macro-routing wording.

### UPDATED: scripts/test-implement-rebase-macro.sh

- Add structural checks that `python/push.py` emits `CHECKPOINT_NEXT`; `python/bootstrap.py` relays `CHECKPOINT_NEXT`; `skills/implement/SKILL.md` uses `CHECKPOINT_NEXT=continue|load-routing` in the macro; SKILL.md gates the four call sites on `CHECKPOINT_NEXT`; SKILL.md documents the `DEGRADED_PROMPT_REQUIRED` carve-out; SKILL.md Step 7a states `7a.r` macro skip is `CHECKPOINT_NEXT`-only; `skills/implement/references/rebase-checkpoint-routing.md` documents `CHECKPOINT_NEXT`.

### UPDATED: scripts/test-implement-structure.sh

- Mirror the lightweight structural checks for the broader lint harness if this file already pins the same rebase macro contract.
- Keep checks string-based and narrow.

### MAY_UPDATE: docs/linting.md

- Update only if test command descriptions mention the old ROUTE-only or exit-code macro-routing contract.

### Edge cases

- **Absorbed Step 1.r:** bootstrap must relay `CHECKPOINT_NEXT` when the probe runs; must not drop it as an unknown KV.
- **Degraded one-down:** when `DEGRADED_PROMPT_REQUIRED=true`, bootstrap skips 1.r; absent `CHECKPOINT_NEXT` must route to the degraded-tools prompt, not `load-routing`.
- **Malformed probe output:** normalize to fail-closed routing with `CHECKPOINT_NEXT=load-routing` (when the probe actually ran).
- **Step 7a:** duplicate `REBASE_OUTCOME` tail must not hide the relayed directive; wrapper non-zero exit must not reintroduce a dual macro gate alongside `CHECKPOINT_NEXT=`.
- **Skipped rebase:** skipped because already pushed or fresh still maps to `CHECKPOINT_NEXT=continue`.
- **Unexpected non-zero rc:** keep `ROUTE=bail`, `REBASE_ERROR=unexpected-rc-<n>`, and add `CHECKPOINT_NEXT=load-routing`.

### Failure modes

- If `CHECKPOINT_NEXT` is missing from direct probes, the orchestrator must load routing instead of silently continuing.
- If bootstrap drops the key on a probe path, Step 1.r may regress to prose-side route derivation.
- If `DEGRADED_PROMPT_REQUIRED=true` is not evaluated before missing `CHECKPOINT_NEXT`, a degraded halt may misclassify as rebase failure.
- If SKILL.md still tells call sites to parse rc plus `ROUTE` for skip logic, the four-site collapse is incomplete.
- If Step 7a prose still keys skip on `ROUTE=continue` or preserves exit-code-for-macro-routing language, macro and relay logic diverge at `7a.r`.
- If `rebase-checkpoint-routing.md` still instructs macro-boundary branching on wrapper process exit code, orchestrators may ignore `CHECKPOINT_NEXT` and re-derive skip from rc plus `ROUTE`.
- If tests only assert `ROUTE`, future changes may remove `CHECKPOINT_NEXT` without detection.

### Testing strategy

- Run `python3 -m pytest python/test_push.py -k checkpoint`.
- Run `python3 -m pytest python/test_bootstrap.py -k checkpoint`.
- Run `python3 -m pytest python/test_bootstrap.py -k degraded` for the no-`CHECKPOINT_NEXT` degraded path.
- Run `bash skills/implement/scripts/test-step-7a.sh`.
- Run `bash scripts/test-implement-rebase-macro.sh`.
- Run `make lint`.
- Because Python files change, also run `make py-lint` and `make py-test`.

## Acceptance

- `push checkpoint-probe` emits `CHECKPOINT_NEXT=continue` on success and `CHECKPOINT_NEXT=load-routing` on conflict/bail/unexpected.
- `bootstrap.py` relays `CHECKPOINT_NEXT` in the Step 0 envelope on probe paths; absent on degraded-skipped-probe paths.
- `skills/implement/SKILL.md` four call sites (~158, ~304, ~550, ~734, ~753) gate on `CHECKPOINT_NEXT`, not on process-rc plus `ROUTE` re-derivation.
- `skills/implement/references/rebase-checkpoint-routing.md` documents `CHECKPOINT_NEXT` and the degraded carve-out.
- All specified tests pass.

review_status: ok
rounds_completed: 3
diff_lines: 163
