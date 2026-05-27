## Decision 1: PR delivery strategy
- **Question**: How should the three fixes ship as PRs? (Combined / Item A first + B+C / three separate)
- **Resolution**: One combined PR. Items A, B, C land together; Item A's "important" severity does not justify splitting given total LOC < ~100.
- **Source**: user (Step 1c)

## Decision 2: Item B audit scope (which codex exec sites)
- **Question**: The OOS body says "Other codex exec sites still use combined 2>&1 without JSONL capture" — scope strictly to line 257 or audit broader?
- **Resolution**: Audit broader, but exclude one-shot probes. Three non-launcher coder/agent sites are in scope:
  1. `skills/review-and-fix/scripts/review-and-fix.sh:257` (review-and-fix coder dispatch)
  2. `scripts/lint-fix-loop.sh:223` (lint-fix coder run)
  3. `scripts/run-negotiation-round.sh:84` (negotiation round)
  Explicitly OUT of scope: `scripts/check-reviewers.sh:199` (one-shot reviewer health probe — no per-bucket telemetry consumer).
  Explicitly OUT of scope: launcher sites (already use `--json` + events.jsonl pattern): `launch-codex-implement.sh`, `launch-codex-ci.sh`, `launch-review.sh`.
- **Source**: user (Step 1c + Round 1 Q1)

## Decision 3: Item C scope
- **Question**: Item C — strict allowlist addition or broader audit?
- **Resolution**: Strict. Add only `scout-archetype-yield.tsv` to `round_artifact_included` in `scripts/larch-log.sh` (alongside `findings-classification.tsv`). No broader allowlist sweep.
- **Source**: user (Round 1 Q2)

## Decision 4: Item B wrapper.log backward compatibility
- **Question**: When Item B adds `--json` + JSONL telemetry, what happens to the currently-allowlisted `coder-codex.wrapper.log` (combined `2>&1` capture, published to committed run-logs)?
- **Resolution**: Keep `coder-codex.wrapper.log` (unchanged shape — preserves any downstream parsers). Add a new artifact `coder-codex.events.jsonl` (or analogous per-site name) carrying telemetry, and add that new artifact to `round_artifact_included` so it's published. No removal or rename of existing allowlisted artifacts.
- **Source**: user (Round 1 Q3)

## Decision 5: Test coverage policy
- **Question**: What regression-test coverage should land with each item?
- **Resolution**: Per-item tests in the same PR:
  - Item A: reproducer test in `scripts/test-get-issue-state.sh` (extend existing harness) — assert that `get-issue-state.sh --issue` (no value) terminates with exit 1 + FAILED envelope, not infinite loop.
  - Item B: extend existing per-site harnesses (`test-review-and-fix.sh`, `test-lint-fix-loop.sh`, `test-run-negotiation-round.sh`) — assert events.jsonl artifact created and telemetry recorded.
  - Item C: extend `scripts/test-larch-log.sh` — assert `round_artifact_included scout-archetype-yield.tsv` returns 0.
- **Source**: user (Step 1c) + codebase (existing harness paths)

## Decision 6: Item A backward compatibility (callers)
- **Question**: `get-issue-state.sh` is called by `/implement` Preflight tracking adoption. Does the Item A fix preserve the FAILED=true/ERROR=<msg>/exit 1 contract for callers?
- **Resolution**: Yes — Item A change extends the existing failure envelope with a new ERROR reason for missing-value argv. Same exit code (1), same KV envelope (`FAILED=true`, `ERROR=<single-line>`). No caller breakage expected. Implementer should NOT change `set -uo pipefail` to `set -euo pipefail` (separate concern; out of scope for this fix).
- **Source**: codebase (`get-issue-state.sh` lines 17-23 and call-site survey)

## Decision 7: Cursor parity (non-goal)
- **Question**: Item B touches Codex-specific telemetry. Should Cursor fallback paths in the same files also be adjusted?
- **Resolution**: No — explicit non-goal. The OOS concern is Codex JSONL telemetry parity with the launcher pattern; Cursor produces different output and is not part of the per-bucket telemetry gap. Cursor sites in `review-and-fix.sh`, `lint-fix-loop.sh`, `run-negotiation-round.sh` are explicitly UNTOUCHED by this PR.
- **Source**: codebase (OOS body wording — "codex exec sites")
