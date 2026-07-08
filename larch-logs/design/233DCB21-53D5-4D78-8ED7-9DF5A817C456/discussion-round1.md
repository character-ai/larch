## Decision 1: Guard behavior on incomplete block extraction
- **Question**: When the extracted `_DESIGN_LIFECYCLE_STDOUT_KEYS` block is truncated or empty, should the guard self-heal, fail loudly, or both?
- **Resolution**: Bounded retry (re-extract up to 3x) to self-heal a transient truncation, then fail with a distinct `block extraction incomplete` diagnostic if every attempt is still incomplete. A truncated read must never be reported as a genuine "missing design <verb>" failure.
- **Source**: user

## Decision 2: Change scope
- **Question**: Should the fix also adjust `test-harnesses` CI shard resources, or stay confined to the harness script?
- **Resolution**: Harness script only (`scripts/test-design-structure.sh`). CI shard resource tuning is explicitly out-of-scope for this change and may be tracked separately.
- **Source**: user

## Decision 3: awk stop-pattern tightening
- **Question**: Should the loose awk stop pattern (`/^\)/`, which never matches the frozenset close `})`) be tightened?
- **Resolution**: Yes. Stop extraction exactly at the frozenset close (`})`) so the block is precisely the `_DESIGN_LIFECYCLE_STDOUT_KEYS` body and the terminal-sentinel completeness check is exact. Verified all looped verbs (ported/step2/render-gate/step6) live within the frozenset body, so tightening drops no verb.
- **Source**: user

## Decision 4: G-Fix-1 sibling scope (from codebase inspection)
- **Question**: Beyond the reported `stdout_keys_block`, are there same-class captured-once blocks whose truncation could masquerade as absent content (guideline G-Fix-1)?
- **Resolution**: The reported fix guards the single `stdout_keys_block` capture, which protects all four reuse sites (the issue's class). Inspection found one nearest same-class sibling — `shared_postplan_body` (capture ~line 442; presence assertion `grep -Fq … || fail` at ~443) — plus inverse absence-assertion blocks (`shared_postplan_body` ~444-445 and `_run_finalize_body` ~520-521, where truncation causes a spurious *pass*, not a spurious failure). Scope the robust retry+sentinel guard to `stdout_keys_block` (the high-exposure block that actually flaked: ~40 lines reused across loops over ~38 verbs, and it has a clean terminal sentinel). Per G-Fix-1's deviation clause, name `shared_postplan_body` and the absence-assertion blocks as intentionally-out-of-scope siblings in the plan and PR description (lower blast radius, never observed to flake, and no clean terminal sentinel to make an analogous guard non-brittle). The line-index captures at ~102-103 are a different single-value pattern and are not in this class.
- **Source**: codebase

## Hard constraints
- The harness must still pass deterministically on a correct tree (`EXIT=0`, `test-design-structure: ok`).
- Preserve `set -euo pipefail`; stay macOS Bash 3.2 compatible.
- A genuinely absent `("design", "<verb>")` entry must still fail with the existing per-verb "missing design <verb>" verdict.
- The single capture point feeds an in-memory variable reused at four sites; guarding the single capture protects all reuse sites (no re-capture occurs).

## Non-goals
- No CI workflow / shard resource changes.
- No refactor of unrelated once-captured blocks in the harness.
- No new meta-test framework for this harness.
