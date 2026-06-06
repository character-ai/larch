# test-implement-structure.sh contract

Structural regression harness for `/implement` after the Step 0 bootstrap collapse.

It pins the core top-level headings, required reference files, larch-log and
tracking summary surfaces, and rejects references to removed anchor
infrastructure.

For Step 0, it pins the collapsed Session Setup subsection: foreground
`implement-bootstrap-invoke.sh --mode initial|resume` call sites (no direct
`implement-bootstrap.sh` in SKILL bash blocks), script-side `phase_coder_select`,
`scripts/parse-bootstrap-routing-envelope.sh` (file-first `bootstrap-routing.env` + stdout fallback), `set +e` / `set -e` wrapper fences, non-zero `_inv_rc` exit before parse
fences around wrapper substitution, absence of inline `_ib_*` helpers, absence
of the deleted prompt-side tracking, plan-materialization, and
implementer-waterfall headings, and the degraded-tools gate fence that
rehydrates all four presence/binary keys from `$IMPLEMENT_TMPDIR/session-env.sh`
with `read-session-env-key.sh --default "false"` before invoking the gate.

It also pins the finalize-state teardown contract: the SKILL.md NEVER bullet
for prompt-side writes, Step 18's restore-before-teardown invocation order, the
`restore-finalize-state.sh` executable plus sibling docs, and the shared
`lib-finalize-state-keys.sh` library plus source references from restore and
ship-pr.

It pins `write-final-report.sh --print-stdout` to Step **17** only; Step **18**
must call `write-final-report.sh` **without** `--print-stdout` (silent refresh).

Two assertions added for the orchestrator narrow-protocol-bounds rule (issue #2286):
`SKILL.md Exit 4 prose must direct orchestrator to 'Continue to Step 16'` (pins that
the documented recovery directive is present) and `ship-pr.sh must emit DO NOT improvise
diagnostic on STALL_STEP=12d exit 4 path` (guards against accidental removal of the
diagnostic message).

The harness also asserts set equality (both directions, order-insensitive) between the
`printf 'KEY=…'` emit keys inside `scripts/ship-pr.sh` `write_initial_state()` and the
backtick key identifiers in the `skills/implement/SKILL.md` “Required keys” bullet list
strictly between the HTML comment anchors `<!-- write-initial-state-keys:begin -->` and
`<!-- write-initial-state-keys:end -->`. Missing either marker or extracting fewer than
20 keys on either side fails closed so accidental parser or doc drift is caught early.

The harness pins the Python Step 8+ cutover contract: stdout JSON plus `finalize-state.sh` stall/PR reads, scoped `ship-pr-state.sh` reads for orchestrator-only keys, Exit 3 `needs_user_reason` / `failed_run_id` JSON dispatch, Exit 4 JSON-only fallback when `finalize-state.sh` is absent, Exit 0/OOS Python reinvocation without `--resume-phase`, the Python-fence `--no-logs-commit` parity flag, and `restore-finalize-state.sh` preservation when `ship-pr-state.sh` seeds `STALL_TRACKING=false`.

Python-default Step 8+ assertions now pin the default selector prose, the bash opt-in trailer, the standalone `^Invoke:$` awk window for Python argv pins (`python/ship.py`, `--state-file`, `needs_user_reason`, `oos-filing`), the bash-only exit-matrix gate bounded through the still-present `**Exit 6**` anchor, the active-driver `8-pre-ship` Phantom Probe registry text, and the `ship-pr-net-retries-python.count` retry counter. Empty or unset `LARCH_SHIP_PR_IMPL` is expected to follow the Python path; only literal `bash` selects the legacy fence.

Step 5 assertions pin the telemetry fence contract: it emits the four banner KVs (`DYNAMIC_ARCHETYPES_CAP`, `PRIOR_DEGRADED_ROUNDS`, `ROUND_CAP`, `EFFECTIVE_ROUND_CAP`), invokes `lib-implement-round-cap.sh --count-prior-degraded`, avoids the retired `dynamic_archetypes_value` tier, and resolves the dynamic-archetypes cap from session-env before ambient env. The harness executes the fence with a conflicting ambient value and verifies the banner cap matches the `run-step5-review.sh` forwarded CLI cap.
