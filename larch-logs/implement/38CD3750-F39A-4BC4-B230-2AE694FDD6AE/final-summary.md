## Review Phase Detail

No review rounds completed.

## Architectural invariants

This change only adds accounting and logging around the plan-review panel. It records reviewer slots the waterfall drops before collection, and aggregator rounds where too few reviewers survived, as per-item entries in the committed execution-issues log, embedding the redacted body of each diagnostic rather than a session-tmpdir pointer (the append-failure path reads the output file and embeds its scrubbed contents). It rejects symlinked or non-regular drop files before reading them, and it threads the pre-existing dropped-slots wire key from its producer through the panel to one new consumer introduced in the same commit. The excluded benign drops remain recorded in the dropped-slots sidecar the waterfall already writes. No changed line weakens a hard gate on data the gated entity authored, reuses a persisted step result without revalidating it against live inputs, commits a terminal outcome label for an in-flight run, or applies a pre-merge mutation to a merged or closed PR. The changed code holds every applicable invariant clean.

## Architectural guidelines

The change routes both degraded plan-review outcomes into the run's category-keyed execution-issues log: reviewer slots the waterfall drops before collection are surfaced as External Reviewer Issues, and rounds where too few reviewers reach the aggregator are surfaced as Warnings. A degraded panel that previously reported zero issues is now counted, and the degraded-versus-empty distinction is made explicit instead of inferring health from emptiness. The dropped-slots wire key already had a producer, and this commit adds the plan-review panel pass-through plus the single new consumer together, with offline tests that replay each degraded scenario and assert the resulting log calls. Status routing branches on explicit value-set membership rather than truthiness and preserves the prior snapshot behavior; drop files are rejected when symlinked or non-regular; appended bodies are redacted. The parallel code-review round already accounts for the same dropped-slots key through its reviewer-failure-threshold gate, a distinct pre-existing mechanism, so no same-shape sibling is left silently unhandled. The changed code holds every applicable guideline clean.

## /implement run 38CD3750-F39A-4BC4-B230-2AE694FDD6AE: shipping

- **Outcome**: shipping
- Force: true
- **Duration**: 00:54:13
- **Cost**: 💰 TOTAL ~$17.14: Claude $16.80, Codex-5.6 $0.00, Codex-mini $0.00, Cursor $0.00, Claude (subprocess) $0.34  |  Tokens: 17948k
- **Issue**: #7353: https://github.com/character-ai/larch/issues/7353
- **Plan review**: N/A
- **Plan coverage**: 0/0 firm headings; band: advisory; disposition: none; todos_left: 0
- **Difficulty**: predicted MODERATE; applied MODERATE
- **Dynamic archetypes**: N/A
- **Code review**: 0/1 accepted
- **Lines (PR diff)**: N/A
- **OOS filed**: 0
- **Exec issues**: 0
- **Warnings**: 0
- **Run logs**: `larch-logs/implement/38CD3750-F39A-4BC4-B230-2AE694FDD6AE/`
- **Main agent model**: claude-opus-4-8
- **Effort**: max
- **Larch version**: 53.1.5

<!-- larch:run-summary v=1 -->
