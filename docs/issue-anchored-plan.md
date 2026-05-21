# Issue-Anchored Plan: Wire Format and Clarification Round-Trip

This document is the **target** normative wire format for exchanging a plan
through a GitHub **issue body** and completing a **clarification round-trip** in
issue **comments** before `/implement` proceeds. The markers and label
semantics here are a **specification to implement**—they are **not** yet parsed
or emitted by shipped `skills/` or `scripts/` in this repository; operators
should not assume matching runtime behavior until tooling lands in-tree.

## Disambiguation: issue-body `larch:plan:*` vs tracking-issue `<!-- larch:plan v1 … -->`

Do **not** confuse this document's paired **issue-body** HTML comment
delimiters (`<!-- larch:plan:start -->` … `<!-- larch:plan:end -->`) with the
**shipped** slim tracking-issue comment marker `<!-- larch:plan v1 runid=<R> -->`
used when `/implement` publishes plan-related digests on a run's tracking
issue. The former embeds a full plan in the **issue description body**; the
latter is a single-line marker prefix inside a **GitHub comment** on the
tracking issue. See `docs/run-logs.md` (tracking-issue comment contracts) and
`skills/implement/references/summary-comment-template.md`. The name family
overlaps (`larch:plan`); the **surface and syntax differ**.

## Plan Block Format

A plan block is embedded in an issue body between two HTML comment markers:

```
<!-- larch:plan:start -->
## Plan

... free-form markdown ...

## Acceptance
- ...
<!-- larch:plan:end -->
```

Rules:

- Exactly one `larch:plan:start` / `larch:plan:end` pair per issue body.
- Free-form markdown is permitted between the markers.
- The `## Plan` and `## Acceptance` sub-sections are **conventional** — parsers
  do not enforce their presence or heading level.
- Malformed shapes are **rejected**: missing matching marker, multiple pairs,
  `start` without `end`, or `end` without `start`.

## Clarification Comment Markers

When `/implement`'s audit step refuses to proceed, it posts a clarification
request as an issue comment. After `/design` resolves the questions and updates
the plan, it posts a matching response.

Each marker below is a **single** HTML comment line in an **issue comment
body**; there is **no** paired “end” marker bounding the markdown (unlike the
plan block's `larch:plan:start` / `larch:plan:end` pair).

### Clarification Request (posted by `/implement`)

```
<!-- larch:clarify-request id=<N> -->
## Clarifications needed
- Q1: ...
- Q2: ...
```

### Clarification Response (posted by `/design`)

```
<!-- larch:clarify-response id=<N> -->
## Resolved
- Q1: ... (plan updated)
- Q2: ... (plan updated)
```

Rules:

- `id=<N>` is a monotonically increasing integer, incremented for each new
  round-trip on the same issue. **No** `id=0` markers are used: when no prior
  `larch:clarify-request` exists, the first request uses `id=1`.
- Each `larch:clarify-request` is paired with **at most one**
  `larch:clarify-response` carrying the same `id`.
- If more than one `larch:clarify-response` appears with the same `id`, the
  thread is **ambiguous**; automation SHOULD refuse further progress until
  operators reconcile the comment stream so exactly one canonical response
  remains for that `id`.
- Multiple round-trips stack as successive `id` values (1, 2, 3, …).

## Label State Machine

The `needs-design-clarification` label tracks whether the plan is currently
awaiting a clarification response. **Label transitions are not enforced by
shipped `skills/` or `scripts/` in this repository**; they may be applied
manually or by automation outside this tree until in-repo hooks or helpers
exist.

| Event | Label action |
|---|---|
| `/implement` posts a `larch:clarify-request` | Add `needs-design-clarification` |
| `/design` posts the matching `larch:clarify-response` | Remove `needs-design-clarification` |

The `STATE` values below describe the **semantic** situation implied by markers
and labels. **Non-normative (tooling)**: a helper script to derive `STATE` from
the comment stream is not checked into this repository yet; operators derive
state manually or via external tooling until a named in-repo path ships.

| `STATE` value | Meaning |
|---|---|
| `clean` | No open clarification request; plan is current |
| `awaiting-response` | A `larch:clarify-request` exists with no matching response yet |
| `response-pending` | A matched response exists; `/implement` has not yet re-checked |

## Lifecycle Examples

### Happy Path

1. `/design` embeds a plan block in the issue body between the markers.
2. `/implement` reads the plan block, passes the audit check, and proceeds with
   implementation.
3. No clarification comments are posted.

### Single-Round Clarification

1. `/design` embeds the initial plan (no prior `larch:clarify-request` markers;
   the first request will use `id=1`).
2. `/implement` audits the plan, finds ambiguity, and posts:
   ```
   <!-- larch:clarify-request id=1 -->
   ## Clarifications needed
   - Q1: Which approach for X?
   ```
   Label `needs-design-clarification` is added.
3. `/design` updates the plan block in the issue body, then posts:
   ```
   <!-- larch:clarify-response id=1 -->
   ## Resolved
   - Q1: Approach A — plan updated.
   ```
   Label `needs-design-clarification` is removed.
4. `/implement` re-checks, the audit passes, implementation proceeds.

### Multi-Round Clarification

Same as above, but after step 4 the audit finds a second ambiguity:

5. `/implement` posts:
   ```
   <!-- larch:clarify-request id=2 -->
   ## Clarifications needed
   - Q2: Edge case for Y?
   ```
6. `/design` resolves and posts:
   ```
   <!-- larch:clarify-response id=2 -->
   ## Resolved
   - Q2: Handle Y by ... (plan updated).
   ```
7. `/implement` re-checks, the audit passes, implementation proceeds.

## Non-Scope

This document covers only the **wire format** (marker syntax, pairing rules,
id semantics) and the **label state machine**. The following are explicitly
out of scope:

- Plan content quality (what constitutes a good plan)
- Audit judgment (how `/implement` decides to reject a plan)
- Design tier selection (`--quick`, `--hard`, sketch topology)

Those concerns live in `skills/design/SKILL.md` and `skills/implement/SKILL.md`.
