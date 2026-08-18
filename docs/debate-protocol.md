# Debate protocol

Normative wire contract for the pure debate protocol. Executable validation and
constants live in `crates/larch-core/src/debate/protocol.rs`. This document names the
owning exported symbol beside every published literal so each value stays
grep-discoverable from its single source of truth. Do not treat examples or
prose here as a second regex or parser authority.

## Ownership

- Executable owner: `crates/larch-core/src/debate/protocol.rs`
- Executable contract tests: the inline tests in
  `crates/larch-core/src/debate/protocol.rs` (run with `cargo test -p larch-core debate`)
- This file is development-only documentation. It has no plugin doc projection.

## Versions and bounds

| Symbol | Value |
| --- | --- |
| `PROTOCOL_VERSION` (`1`) | Protocol wire version |
| `FINGERPRINT_ALGORITHM_VERSION` (`1`) | Fingerprint domain-separation version |
| `FINGERPRINT_HEX_LENGTH` (`16`) | Lowercase hex fingerprint prefix length |
| `ROUND_LIMIT` (`2`) | Negotiation round cap |
| `POINT_ID_MIN` (`1`) | Inclusive minimum point number |
| `POINT_ID_MAX` (`9999`) | Inclusive maximum point number |
| `LIVE_PANEL_MINIMUM` (`2`) | Independent live-slot floor |
| `LIVE_PANEL_MAXIMUM` (`3`) | Live-slot ceiling; equals `len(SLOT_ORDER)` |

`SLOT_ORDER` (`("cursor", "codex", "claude")`) is the ascending panel order.
`SLOT_SET` is `frozenset(SLOT_ORDER)`.

Ledger tokens:

- `LEDGER_POINT_TOKEN` (`POINT`)
- `POINT_ID_PREFIX` (`POINT_`)
- `ACTION_AGREE` (`AGREE`), `ACTION_CONCEDE` (`CONCEDE`), `ACTION_HOLD` (`HOLD`)
- `ACTION_TOKENS` (`frozenset({"AGREE", "CONCEDE", "HOLD"})`)
- `ARTIFACT_CITATION_PREFIX` (`[[artifact:`)
- `ARTIFACT_CITATION_SUFFIX` (`]]`)

## Types and enums

Each type below is an exported symbol from `crates/larch-core/src/debate/protocol.rs`.

### `Participant`

Fixed panel slots: `cursor`, `codex`, `claude` (same membership as `SLOT_ORDER`).

### `Action`

Per-point ledger actions: `AGREE`, `CONCEDE`, `HOLD`.

### `ConcessionClassification`

- `cited`
- `fold`
- `non-concession` (enum member `non_concession`)

### `ParseRejectionReason`

Stable fail-closed tokens include: `empty-submission`, `blank-row`,
`forbidden-character`, `leading-or-trailing-whitespace`,
`repeated-separator-spaces`, `malformed-row`, `unknown-action`, `empty-reason`,
`malformed-point-id`, `point-id-out-of-range`, `duplicate-point-id`,
`forbidden-plan-content`, `invalid-slot`, `invalid-artifact-path`,
`invalid-protocol-version`, `invalid-fingerprint-version`, `invalid-fingerprint`,
`empty-replacement-needle`, `invalid-round-number`, `invalid-slot-ordering`,
`below-live-panel-floor`, `above-live-panel-ceiling`, `point-universe-mismatch`,
`fingerprint-mismatch`, `malformed-adjudication`,
`incomplete-adjudication-coverage`, `illegal-transition`,
`empty-point-universe`, `nonadjacent-rounds`, `invalid-run-local-values`,
`invalid-proposal-state`.

### `RoundNumber`

`ROUND_1` (`1`), `ROUND_2` (`2`). Membership equals `range(1, ROUND_LIMIT + 1)`.

### `PointResolution`

`AGREED`, `CONCEDED`, `HELD`, `FOLDED`.

### `NonterminalPhase`

`BLIND_ROUND_1`, `ROUND_2`, `AWAITING_ADJUDICATION`, `UNCONVERGED`.

### `TerminalOutcome`

`CONVERGED`, `STALEMATE`, `BOTH_VIABLE`, `ABORTED`.

### `AdjudicationDecision`

`SELECTED`, `SPLIT`.

### `StalemateDetectionStatus`

`COMPLETED`, `MEMBERSHIP_CHANGED`.

### `TransitionAction`

`SUBMIT_ROUND`, `DECLARE_STALEMATE`, `ADJUDICATE`, `ABORT`.

### Frozen value objects

- `PointId`: field `number: int`; property `token` renders `POINT_<n>`.
- `ReasonFingerprint`: field `value: str` (exactly `FINGERPRINT_HEX_LENGTH`
  lowercase hex characters).
- `LedgerRow`: `point_id`, `action`, `reason`, `concession`.
- `ParsedSlotLedger`: `rows: tuple[LedgerRow, ...]`.
- `SlotLedgerBinding`: `slot`, `ledger`, `fingerprints`; optional
  `run_local_values` init-only mapping verified at construction.
- `RoundState`: `round_number`, `bindings`; properties `live_slots`, `point_ids`.
- `Dispute`: `point_id`, `holding_slots` (at least `LIVE_PANEL_MINIMUM`,
  ascending).
- `SelectedAdjudication`: `point_id`, `selected_position`; `decision` is
  `SELECTED`.
- `SplitAdjudication`: `point_id`, `position_a`, `position_b` (must differ);
  `decision` is `SPLIT`.
- `StalemateDetection`: `status`, `disputes`.
- `ProposalState`: `point_universe`, `protocol_version`,
  `fingerprint_algorithm_version`, `run_local_values`, `phase`,
  `terminal_outcome`, `rounds`, `disputes`, `adjudications`.

`ProtocolRejection` is a `ValueError` carrying `reason: ParseRejectionReason`.

## Ledger grammar

Rows are LF-only. `parse_slot_ledger` splits on literal `\n`. A trailing newline
yields a final empty segment and rejects as `blank-row`.

Canonical row shape:

```text
POINT POINT_<n> <AGREE|CONCEDE|HOLD> <reason>
```

Structural separators are single spaces before the reason. Reason-internal
spacing, including doubled spaces, is preserved byte for byte.

### Positive examples

```text
POINT POINT_1 AGREE looks good
POINT POINT_1 CONCEDE see POINT POINT_2
POINT POINT_2 HOLD keep this position
POINT POINT_3 CONCEDE no citation here
POINT POINT_1 AGREE reason  with  spaces
```

### Negative examples

| Input class | Rejection |
| --- | --- |
| Empty submission | `empty-submission` |
| Blank row / trailing LF | `blank-row` |
| CR, tab, other controls | `forbidden-character` |
| Leading or trailing whitespace on the row or reason | `leading-or-trailing-whitespace` |
| Repeated spaces before the reason field | `repeated-separator-spaces` |
| Wrong token count / shape | `malformed-row` |
| Unknown action token | `unknown-action` |
| Empty reason | `empty-reason` |
| `POINT_0`, `POINT_01`, non-digits | `malformed-point-id` |
| `POINT_10000` | `point-id-out-of-range` |
| Duplicate point IDs in one submission | `duplicate-point-id` |
| Plan heading or whole-line `diff_lines:` trailer in the reason | `forbidden-plan-content` |

Forbidden plan content is delegated to `larch.design.plan_grammar` through
`reject_forbidden_plan_content`. Other trailer keys such as `difficulty:` are
not rejected as trailers.

## Citations and concessions

`classify_concession(action, reason)`:

- Non-`CONCEDE` actions always yield `non-concession`.
- `CONCEDE` is `cited` when the reason contains at least one complete bounded
  `POINT POINT_N` citation (valid point token) or an exact
  `[[artifact:RELATIVE_POSIX_PATH]]` citation with a valid relative POSIX path.
- Otherwise `CONCEDE` is `fold`. The original reason is retained.

Malformed near-misses (`POINT POINT_0`, glued tokens, absolute artifact paths,
parent traversal, missing brackets) do not invalidate an otherwise valid ledger
reason; they only leave a concession classified as `fold`.

Valid artifact paths are nonempty relative POSIX paths: no absolute prefix, no
backslashes, no empty / `.` / `..` segments, no `//`, no trailing `/`, and no
control characters. Spaces inside otherwise valid segments are permitted.

## Fingerprints

`normalize_reason_for_fingerprint` then `fingerprint_reason`:

1. NFKC-normalize the reason.
2. Collect replacement needles from an iterable of values or a mapping's values.
3. Reject empty needles (`empty-replacement-needle`).
4. Apply unique needles longest-first, then lexicographically, replacing each
   with a deterministic `<run-local:N>` placeholder so container order and
   overlapping values cannot change the digest.
5. Domain-separate with `FINGERPRINT_ALGORITHM_VERSION`, hash with SHA-256, and
   truncate to `FINGERPRINT_HEX_LENGTH` lowercase hex characters.

Ambient clocks, environment, filesystem paths, and run IDs are excluded unless
the caller supplies those substrings as replacement needles. Forged binding
fingerprints fail with `fingerprint-mismatch`.

## Round assembly

`RoundState` requires:

- `round_number` in `1..ROUND_LIMIT`
- live binding count in `[LIVE_PANEL_MINIMUM, LIVE_PANEL_MAXIMUM]`
- ascending unique slots per `SLOT_ORDER`
- identical ordered point universes across every live slot

One live slot always rejects with `below-live-panel-floor`, even though one
unchanged hold also fails the stalemate two-slot threshold. Mismatched point
order or membership rejects with `point-universe-mismatch`. Empty universes
reject with `empty-point-universe`.

`SlotLedgerBinding` verifies each row fingerprint under the supplied run-local
snapshot at construction. `ProposalState` re-verifies rounds against its frozen
run-local mapping.

## Point resolution

`slot_closes_point` is true for `AGREE` and for cited `CONCEDE`. Folded
concessions and `HOLD` never close.

`resolve_point` over every live slot's row for one point:

| Condition | `PointResolution` |
| --- | --- |
| Every slot closes, and all actions are `AGREE` | `AGREED` |
| Every slot closes, and at least one cited `CONCEDE` | `CONCEDED` |
| Not fully closed, and any slot `HOLD`s | `HELD` |
| Not fully closed, and no `HOLD` | `FOLDED` |

A round is fully resolved when every point is `AGREED` or `CONCEDED`. Point
universe order continues across bindings, rounds, and `ProposalState`.

## Stalemate detection

`detect_stalemate_disputes(proposal, earlier, later)`:

| Condition | Result |
| --- | --- |
| Nonadjacent round numbers | reject `nonadjacent-rounds` |
| Fingerprint revalidation fails | reject `fingerprint-mismatch` |
| Live-slot membership changed | `MEMBERSHIP_CHANGED` with empty disputes |
| Adjacent, stable membership, no qualifying holds | `COMPLETED` with empty disputes |
| At least two matching slots `HOLD` both rounds with unchanged recomputed fingerprints | `COMPLETED` with one `Dispute` per such point |

Qualifying disputes require unchanged `HOLD` fingerprints from at least
`LIVE_PANEL_MINIMUM` matching slots. Partial coverage (some unresolved points
qualify, others do not) still returns `COMPLETED` with only the qualifying
disputes. `MEMBERSHIP_CHANGED` is distinct from a completed empty result and
must not carry disputes.

## Adjudication

`validate_adjudication_set(unresolved, records)` requires:

- nonempty unresolved set without duplicates
- exactly one record per unresolved point, no foreign or duplicate points
- valid position text (nonempty, stripped, no newlines/controls, no forbidden
  plan content); split positions must differ

Returns `CONVERGED` when every record is selected, or `BOTH_VIABLE` when any
record is a split.

## Transition matrix

`NonterminalPhase` has four members and `TransitionAction` has four members, so
the full matrix has `4 × 4 = 16` pairs. The legal subset is the nine edges in
the pinned legal-edge table in `crates/larch-core/src/debate/protocol.rs`
(`LEGAL_EDGES`). The remaining seven pairs are illegal.

| Phase (`NonterminalPhase`) | Action (`TransitionAction`) | Legal? | Result / payload |
| --- | --- | --- | --- |
| `BLIND_ROUND_1` | `SUBMIT_ROUND` | yes | requires `round_state` for round 1; converges if fully resolved, else `ROUND_2` |
| `BLIND_ROUND_1` | `DECLARE_STALEMATE` | no | `illegal-transition` |
| `BLIND_ROUND_1` | `ADJUDICATE` | no | `illegal-transition` |
| `BLIND_ROUND_1` | `ABORT` | yes | no payload; `ABORTED` |
| `ROUND_2` | `SUBMIT_ROUND` | yes | requires `round_state` for round 2; may converge, await adjudication, or go `UNCONVERGED` |
| `ROUND_2` | `DECLARE_STALEMATE` | no | `illegal-transition` |
| `ROUND_2` | `ADJUDICATE` | no | `illegal-transition` |
| `ROUND_2` | `ABORT` | yes | no payload; `ABORTED` |
| `AWAITING_ADJUDICATION` | `SUBMIT_ROUND` | no | `illegal-transition` |
| `AWAITING_ADJUDICATION` | `DECLARE_STALEMATE` | yes | no payload; requires existing disputes; `STALEMATE` |
| `AWAITING_ADJUDICATION` | `ADJUDICATE` | yes | requires `adjudications`; `CONVERGED` or `BOTH_VIABLE` |
| `AWAITING_ADJUDICATION` | `ABORT` | yes | no payload; clears disputes; `ABORTED` |
| `UNCONVERGED` | `SUBMIT_ROUND` | no | `illegal-transition` |
| `UNCONVERGED` | `DECLARE_STALEMATE` | no | `illegal-transition` |
| `UNCONVERGED` | `ADJUDICATE` | yes | requires `adjudications`; `CONVERGED` or `BOTH_VIABLE` |
| `UNCONVERGED` | `ABORT` | yes | no payload; `ABORTED` |

Illegal edges reject before payload validation can mask the transition error.
Terminal proposals reject every further transition (`illegal-transition`).
Representative payload failures include missing/extra payloads, wrong round
numbers, forged fingerprints, and incomplete adjudication coverage.

After round 2 submission when the round is incomplete:

- membership change → `UNCONVERGED` (detection skipped)
- disputes covering every unresolved point → `AWAITING_ADJUDICATION`
- otherwise → `UNCONVERGED`
