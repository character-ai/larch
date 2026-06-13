# persist-retally-step3-env.sh

Refreshes both Step 3 result envs (`.step3-plan-review-result.env` and
`.step3-review-result.env`) after a `/design` MainAgent re-tally, routing
`SCOPE_ANCHOR_FILE` through `python/cli.py scope-anchor retally-handoff`.
On successful re-tally, it also merges current `accepted-plan-findings.md`
blocks into `accepted-plan-findings-all.md` and merges current
`oos-accepted-design.md` with `.oos-accepted-design.prev.md`, so cumulative
final-summary and filing accounting include MainAgent-adjudicated findings and
prior-round accepted OOS. The in-scope merge is exact-block idempotent; the OOS
merge uses normalized `Description` keys. Both merges are skipped on
`tally-error`; tally-error also clears partial current
`accepted-plan-findings.md`, removes any existing `round-meta.json` / `panel-manifest.ndjson` for the resolved round, and zeros accepted-count KVs in refreshed env files.

- **Argv**: `--design-tmpdir DIR --retally-stdout-file FILE
  --retally-input-anchor PATH-OR-EMPTY --tally-plan-review-status ok|tally-error
  --loop-status complete|...`.
- **Primary caller**: `skills/design/SKILL.md` Step 3 MainAgent re-tally
  branch (`main-agent-vote-required`).
- **Retally round refresh**: before env rewrite, the helper resolves the affected round from `.step3-plan-review-result.env`, preferring numeric `ROUND_NUM` and falling back to numeric `ROUNDS_COMPLETED`; it does not read `review-round-count.txt` to choose the metadata target. On `ok`, after cumulative accepted/OOS merges and env rewrites, it copies the fresh session-root `voting-tally.md` into `plan-review/round-N/` and runs `scripts/write-design-round-meta.sh --round-dir`. It deliberately does not copy session-root `findings-classification.tsv`; the retally path owns the round-local TSV. On `tally-error`, it skips snapshot refresh and removes stale round metadata when the round directory exists. The helper never appends timing rows.
- **Invariants**: persists `SCOPE_ANCHOR_FILE` only on permitted terminals —
  parsed re-tally stdout KV preferred, `--retally-input-anchor` fallback on
  `ok` when stdout omits the KV; omits the key on `tally-error`; never
  persists CR/LF or out-of-tmpdir paths (validators from
  `python/cli.py scope-anchor`). See `SECURITY.md` "Plan-review
  scope-anchor pipeline" — path-only handoff surface. The cumulative accepted
  merge reads only `### FINDING_N:` blocks from the current accepted file and
  appends blocks not already present byte-for-byte in the cumulative file; the
  OOS merge reads `### OOS_N:` blocks from the prior snapshot and current
  accepted-OOS file and writes the merged cumulative file back to
  `oos-accepted-design.md`.
- **Harness**: `skills/design/scripts/test-persist-retally-step3-env.sh`
  (Makefile target `test-persist-retally-step3-env`).
