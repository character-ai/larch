# test-implement-structure.sh contract

Structural regression harness for `/implement` after the Step 0 bootstrap collapse.

It pins the core top-level headings, required reference files, larch-log and
tracking summary surfaces, and rejects references to removed anchor
infrastructure.

For Step 0, it pins the collapsed Session Setup subsection: foreground
`implement-bootstrap-invoke.sh --mode initial|resume` call sites (no direct
`implement-bootstrap.sh` in SKILL bash blocks), script-side `phase_coder_select`,
shared `bootstrap-routing.env` parse with stdout fallback, `set +e` / `set -e`
fences around wrapper substitution, absence of inline `_ib_*` helpers, and
absence of the deleted prompt-side tracking, plan-materialization, and
implementer-waterfall headings.

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
