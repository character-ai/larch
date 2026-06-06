# persist-retally-step3-env.sh

Refreshes both Step 3 result envs (`.step3-plan-review-result.env` and
`.step3-review-result.env`) after a `/design` MainAgent re-tally, routing
`SCOPE_ANCHOR_FILE` through `larch_scope_anchor_retally_handoff_value`.

- **Argv**: `--design-tmpdir DIR --retally-stdout-file FILE
  --retally-input-anchor PATH-OR-EMPTY --tally-plan-review-status ok|tally-error
  --loop-status complete|...`.
- **Primary caller**: `skills/design/SKILL.md` Step 3 MainAgent re-tally
  branch (`main-agent-vote-required`).
- **Invariants**: persists `SCOPE_ANCHOR_FILE` only on permitted terminals —
  parsed re-tally stdout KV preferred, `--retally-input-anchor` fallback on
  `ok` when stdout omits the KV; omits the key on `tally-error`; never
  persists CR/LF or out-of-tmpdir paths (validators from
  `scripts/lib-scope-anchor-handoff.sh`). See `SECURITY.md` "Plan-review
  scope-anchor pipeline" — path-only handoff surface.
- **Harness**: `skills/design/scripts/test-persist-retally-step3-env.sh`
  (Makefile target `test-persist-retally-step3-env`).
