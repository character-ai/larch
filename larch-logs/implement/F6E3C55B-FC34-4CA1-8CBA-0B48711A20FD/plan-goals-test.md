## Goal
Implement issue #7477: [IMPLEMENTING] contract-unification [DEDUP] Finish shared KV codec adoption in orchestration flows.

## Implementation Plan
#### Problem

The shared KV codec baseline retains 17 sites across agent, bgjob, implement, and review orchestration modules. These paths parse high-value status and result envelopes, so local split loops can drift from the canonical duplicate-key and malformed-row policy.

#### Goal

Migrate the residual rows in `larch.agents`, `larch.bgjob`, `larch.implement`, and `larch.review`. Preserve each envelope's required-key checks and routing behavior. Use the shared codec for syntax only and keep domain validation at the boundary. Remove exactly the migrated baseline rows.

#### Exact scope

Use the committed baseline to migrate: `agents/_vendor.py`, `agents/collect_results.py`, `bgjob/adapt.py`, `bgjob/daemon.py`, `implement/checks_lint_fix.py`, `implement/dispatch_commit_route.py`, `implement/dispatch_manifest.py`, `implement/dispatch_ship.py`, `implement/step_7a.py`, `review/plan_review_loop.py`, `review/plan_review_normalize.py`, `review/review_pipeline_shared.py`, and `review/voting.py`.

#### Required implementation

- Characterize each envelope's identity and duplicate-key policy before replacement. Agent and bgjob status envelopes must remain fail-closed where they authorize continuation.
- Reuse canonical `read_kvs`, `read_kv`, or stream decoding APIs. Do not add a domain-local codec wrapper that merely renames the shared function.
- Preserve anchored whole-line matching, allowed-key filtering, required-key counts, redaction, output channels, and current error text where it is part of a caller contract.
- Keep semantic parsing, such as booleans, integers, status enums, or path validation, in the domain module after lexical decode.
- Retarget monkeypatches to the shared codec binding actually read by production code. Avoid re-exporting the codec through a facade.

#### Baseline and verification

The baseline must lose exactly 17 rows in the listed modules. Add table-driven malformed-envelope tests for every distinct parser policy, then run focused agent, bgjob, implement, review, codec-lint, ruff, and pyright checks.

#### Dependencies, size, acceptance

#7389 and #7390 have landed. Implement against their direct-owner imports and do not restore either facade. Expected change: 700-1,200 lines. Focused tests must cover every migrated envelope's malformed and duplicate-key behavior. No new KV baseline row may appear.

## Test plan
(no test plan section in plan-file)
