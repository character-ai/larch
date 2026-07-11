# Discussion Round 1 — #6835 (Step 8 assessment lane 2/4)

Partition piece 2 of 4 from #6801. Scope, hard constraints, and done criteria are
firmly specified in the issue acceptance criteria and the 4-piece partition text.
The operator-level decisions (once-per-run, bgjob lane not Agent-tool, mechanical
pre-filter) are already settled in #6801. Round 1 records the scope boundaries and
hard constraints resolved from the issue text + codebase, not architectural
preferences (those belong to Step 2b).

## Decision 1: Launcher boundary — Piece 2 owns the read-only Claude launch
- **Question**: Does this piece ship the concrete read-only Claude launcher, or only a launcher interface with the real subprocess deferred to Piece 3?
- **Resolution**: Piece 2 owns the read-only Claude launch. The coordinator performs the full flow (validate kinds → verify materialized inputs → pre-filter → launch Claude read-only → parse → validate → persist → fallback → idempotent re-entry), including the launch mechanism, with an injectable launcher so tests use fakes. Piece 3 (#6836) is purely the bgjob start/wait/rejoin shell that delegates to Piece 2's CLI; it is not the launcher.
- **Source**: codebase/issue — #6835 scope lists "read-only Claude launch"; #6836 scope lists only "bgjob adapter around the assessment CLI" and acceptance says "Delegate execution to Piece 2's CLI."

## Decision 2: Live Step 8 route unchanged in this piece
- **Question**: Does this piece wire the coordinator into the live /implement Step 8 route?
- **Resolution**: No. The live Step 8 route remains on the existing inline authoring path. Piece 4 (#6837) performs the activation (route assessments through the bgjob, remove inline authoring). Piece 2 delivers a standalone, machine-readable CLI + coordinator + agent prompt that Piece 3 later wraps and Piece 4 later activates.
- **Source**: issue acceptance ("The live Step 8 route remains unchanged") + firm-heading file set.

## Decision 3: Persistence targets Piece 1's existing durable artifacts
- **Question**: Where does the coordinator persist results so downstream consumption is unchanged?
- **Resolution**: Write to the exact durable note + ship-outcome paths Piece 1 defined (`durable_note_path` / `invariant_durable_note_path`, `guideline_ship_outcome_path` / `invariant_ship_outcome_path`, sidecar/diff/meta paths in `architectural_guidelines.py`), using Piece 1's note writers (`write_implement_note` / `write_invariant_implement_note`, `write_deterministic_clean_note`, `write_unavailable_note`) and schema-version-1 outcome validators. This keeps `ship_guidelines.py` consumption identical.
- **Source**: codebase — Piece 1 (#6834, DONE) foundation in `python/larch/core/architectural_guidelines.py`.

## Decision 4: Hard constraints (non-negotiable, from acceptance + Piece 1)
- **Question**: Which behaviors must not break?
- **Resolution**:
  - Invariant violations stay blocking; `unavailable` never erases a valid violation; `deterministic-clean` only for proven-safe inputs.
  - The CLI independently verifies materialized HEAD, base reference, fingerprint, frozen diff, and knowledge snapshots (do not trust launcher-supplied identity).
  - Parsing rejects extra prose, missing/duplicate kinds, unknown identifiers, invalid states, symlinks, non-regular files, and stale identities.
  - Timeout / launcher / schema failures → bounded, redacted `unavailable` result; no inline-prose request on failure.
  - Re-entry for an already-handled fingerprint + kind set does not launch twice (idempotent).
  - Supported kinds are exactly `guidelines` and `invariants` (config constants); the coordinator accepts a kind set, dedups, and rejects unknowns.
- **Source**: issue acceptance + config constants `ASSESSMENT_KIND_*`.

## Decision 5: Done criteria — tests use fake launchers, no network
- **Question**: What is the verification bar?
- **Resolution**: `python/tests/implement/test_architectural_assessment.py` and the `test_design_cli_ports.py` registration entry use fake launchers and require no network. The agent prompt (`architectural-assessment-agent.md`) is a read-only reference prompt, not executed in tests.
- **Source**: issue acceptance ("Tests use fake launchers and require no network access").

## Non-goals (explicit out-of-scope, owned by other pieces)
- bgjob start/wait/rejoin harness → Piece 3 (#6836).
- Activating the live Step 8 route / removing inline authoring → Piece 4 (#6837).
- New foundation state/identity/validator logic → Piece 1 (#6834, DONE); this piece consumes it.

1 decision branch resolved from codebase; < 2 genuine scope branches → short-circuit.
