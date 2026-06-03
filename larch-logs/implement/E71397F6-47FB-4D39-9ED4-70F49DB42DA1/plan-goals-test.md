## Goal
Implement issue #3326: [IMPLEMENTING] [OOS] Phase 5 Python: reconcile link_pr_closes with ship-pr Closes #N composition\n\n- **Description**: link_pr_closes lives in tracking_issue.py but Closes #N is composed in ship-pr pr-body assembly (scripts/ship-pr.sh:1535) and tracking-issue-write.sh has no Closes helper. Scenario: Duplicate or dead API surface in the 8-module bundle.

## Implementation Plan
## Plan

Reconcile the Python rework tree's two `Closes #N` composers into one source of
truth, fix the canonical helper's prefix-collision bug, and drop dead surface.
`tracking_issue.link_pr_closes` becomes the single canonical helper (string +
idempotency); `pr_body.compose_pr_body` delegates to it instead of inlining
`f"Closes #{issue_number}"`. Delete the unused `PrBodyParts` dataclass. No bash
changes, no fork/no-issue placeholder parity, no new `pr.ensure_pr` wiring.

SIMPLE-tier, `python/`-only cleanup (dev/CI tree, not wired to the live
`/implement` path until Phase 7).

### UPDATED: `python/pr_body.py`
- Add `import tracking_issue` to the import block. No circular import:
  `tracking_issue.py` imports only `config`, `gh`, `redact`, `errors`, `proc` —
  not `pr_body`.
- Delete the dead `PrBodyParts` dataclass (`@dataclass(frozen=True)` with fields
  `summary`, `mermaid_block`, `test_plan`, `closes_line`). Never instantiated in
  `python/`. Keep `from dataclasses import dataclass` — still used by
  `MermaidResult`.
- In `compose_pr_body`, build the body from `parts` first, then append `Closes #N`
  through the canonical helper:
  - Old: `if issue_number is not None: parts.extend(["", f"Closes #{issue_number}"])`
    before `body = "\n".join(parts) + "\n"`.
  - New: `body = "\n".join(parts) + "\n"`, then
    `if issue_number is not None: body = tracking_issue.link_pr_closes(body, issue_number)`.
  - Keep the post-build order: `sanitize_fragment(body, from_md=True)` and
    `redact.redact(...)` fail-closed still run on the final body.

### UPDATED: `python/tracking_issue.py`
- Make `link_pr_closes` prefix-collision-safe. Replace the substring guard with a
  digit-boundary regex so a longer issue number cannot mask a shorter one:
  - Old: `needle = f"Closes #{issue_number}"` then `if needle in body: return body`.
  - New: keep `needle = f"Closes #{issue_number}"` for the append; change the guard
    to `if re.search(rf"Closes #{issue_number}(?!\d)", body): return body`.
  - `re` is already imported. The append branch
    (`return body.rstrip() + f"\n\n{needle}\n"`) is unchanged.
  - Rationale (plan-review finding, Cursor-Edge): substring `needle in body` skips
    appending `Closes #4` when the body already contains `Closes #42`. The fix
    benefits both `compose_pr_body` and the existing `pr.ensure_pr` caller.

### UPDATED: `python/test_pr_body.py`
- Add `test_compose_pr_body_appends_closes`: `compose_pr_body(summary="- x",
  issue_number=42)` contains `Closes #42` exactly once.

### UPDATED: `python/test_tracking_issue.py`
- Keep `test_link_pr_closes_appends`.
- Add `test_link_pr_closes_idempotent`: a body already containing an exact
  `Closes #42` is returned unchanged.
- Add `test_link_pr_closes_no_prefix_collision`: a body containing `Closes #421`
  still gets `Closes #42` appended for `link_pr_closes(body, 42)`.

### Approach
- Single owner for the `Closes #N` string + idempotency:
  `tracking_issue.link_pr_closes`, now collision-safe. `compose_pr_body` and
  `pr.ensure_pr` both route through it. `pr.ensure_pr` call sites are unchanged and
  inherit the fix.
- The helper stays in `tracking_issue.py` (not moved to `pr_body.py`), keeping
  churn minimal at the cost of the bash-vs-Python module-placement difference.

### Edge cases
- `issue_number is None`: no `Closes` line; `link_pr_closes` not called.
- Body already has an exact `Closes #N`: no-op (idempotent).
- Prefix collision (`#4` vs `Closes #42`, or `#42` vs `Closes #421`): fixed by the
  digit-boundary guard. Leading side is already safe via the literal `Closes #`.
- Blank-line layout before `Closes #N` shifts from two blank lines to one (matches
  bash); no existing test pins the old layout.
- Mermaid sanitization and redaction still run on the final body.

### Failure modes
1. Future circular import if `tracking_issue` imports `pr_body` → `ImportError`.
   Keep the helper dependency-free.
2. Future use of removed `PrBodyParts` → `AttributeError`. Verified no current or
   planned uses.
3. Digit-boundary regex altering idempotency unexpectedly → `test_link_pr_closes_*`
   failure. The change only narrows "already present" detection (never produces
   duplicates); the regression tests lock append and no-append paths.

### Testing strategy
- Add the three tests above. Run `make py-lint` and `make py-test`; both stay
  green. No bash files touched.

## Acceptance

- `python/tracking_issue.py:link_pr_closes` uses the digit-boundary guard
  `re.search(rf"Closes #{issue_number}(?!\d)", body)`; calling it on a body that
  contains `Closes #421` with `issue_number=42` appends `Closes #42`, and a body
  already containing an exact `Closes #42` is returned unchanged.
- `python/pr_body.py:compose_pr_body` appends `Closes #N` via
  `tracking_issue.link_pr_closes` and no longer inlines `f"Closes #{issue_number}"`;
  `compose_pr_body(summary="- x", issue_number=42)` contains `Closes #42` exactly
  once.
- The `PrBodyParts` dataclass is removed from `python/pr_body.py`
  (`grep -n PrBodyParts python/` returns no matches). `from dataclasses import
  dataclass` remains (used by `MermaidResult`).
- `python/pr.py` `ensure_pr` call sites are unchanged.
- New tests exist and pass: `test_compose_pr_body_appends_closes`,
  `test_link_pr_closes_idempotent`, `test_link_pr_closes_no_prefix_collision`;
  `test_link_pr_closes_appends` still passes.
- `make py-lint` and `make py-test` both pass.
- No files outside `python/` are modified (no bash changes).

diff_lines: 33

## Test plan
(no test plan section in plan-file)
