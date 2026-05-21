## Goal
Pre-document the issue-anchored plan wire format and clarification round-trip

## Implementation Plan

### Goal
Create docs/issue-anchored-plan.md documenting the issue-anchored plan wire format and clarification round-trip, then add one-line link references from README.md and AGENTS.md.

### Files to modify
1. **NEW** `docs/issue-anchored-plan.md` — the main deliverable
2. **EDIT** `README.md` — add one-line link under Reference section
3. **EDIT** `AGENTS.md` — add one-line entry in Canonical sources list

### Implementation

#### 1. `docs/issue-anchored-plan.md`

The doc covers exactly what the issue specifies:

- **Plan block format** with `<!-- larch:plan:start -->` / `<!-- larch:plan:end -->` markers:
  - Exactly one start/end pair per issue body
  - Free-form markdown between markers
  - `## Plan` and `## Acceptance` sub-sections conventional but not parser-enforced
  - Malformed shapes rejected (missing matching marker, multiple pairs, start without end, end without start)

- **Clarification comment markers**:
  - Request: `<!-- larch:clarify-request id=<N> -->` posted by /implement on audit refusal
  - Response: `<!-- larch:clarify-response id=<N> -->` posted by /design after resolving
  - `id=<N>` monotonically increases per round-trip; each request paired with at most one response carrying the same id
  - Multiple round-trips stack as new id values

- **Label state machine**:
  - `needs-design-clarification` added when clarify-request posted (toggled on by /implement)
  - Same label removed when matching clarify-response posted (toggled off by /design)
  - `clarify-state.sh` derives `STATE=clean|awaiting-response|response-pending` from the latest pair

- **Lifecycle examples**: happy path, single-round clarification, multi-round clarification

- **Explicit non-scope**: the doc does NOT cover plan content quality, audit judgment, or design tier selection

#### 2. `README.md`

Add one line under the **Reference** section (after existing doc links, before Architecture section):
```
  - [Issue-Anchored Plan](docs/issue-anchored-plan.md) — wire format for the /design ↔ /implement plan handoff and clarification round-trip
```

#### 3. `AGENTS.md`

Add one line to the Canonical sources list (after `docs/run-logs.md` entry):
```
- `docs/issue-anchored-plan.md` — wire format for the /design ↔ /implement plan handoff and clarification round-trip
```


## Test plan
- `make lint` and `agent-lint` pass
- No code changes (pure docs addition)
