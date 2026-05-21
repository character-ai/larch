# Issue-Anchored Plan: Wire Format and Clarification Round-Trip

This document specifies the wire format that `/design` and `/implement` use
when exchanging a plan through a GitHub issue body, and the clarification
round-trip protocol that resolves audit rejections before implementation
proceeds.

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
  round-trip on the same issue.
- Each `larch:clarify-request` is paired with **at most one**
  `larch:clarify-response` carrying the same `id`.
- Multiple round-trips stack as successive `id` values (1, 2, 3, …).

## Label State Machine

The `needs-design-clarification` label tracks whether the plan is currently
awaiting a clarification response.

| Event | Label action |
|---|---|
| `/implement` posts a `larch:clarify-request` | Add `needs-design-clarification` |
| `/design` posts the matching `larch:clarify-response` | Remove `needs-design-clarification` |

`clarify-state.sh` (from the helpers PR) derives the current state from the
comment stream:

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

1. `/design` embeds the initial plan (id counter starts at 0; no clarify
   comments yet).
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

Those concerns live in the `/design` and `/implement` SKILL.md files.
