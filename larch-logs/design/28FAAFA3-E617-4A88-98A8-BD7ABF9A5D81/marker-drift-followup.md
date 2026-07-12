### contract-unification [FEATURE] repoint marker-drift sites to issue_wire

## Problem

`python/larch/issue/issue_wire.py` owns `larch:plan` named-block marker composition and recognition (`compose_named_block` and friends), but three call sites bypass it and hand-compose or hand-check plan-block markers. This drift is the marker-side analogue of the plan-grammar duplication that #7000 consolidates. It was identified during #7000 design but kept out of that issue's scope to keep the grammar move focused.

Verified bypass sites:

- `python/larch/design/decompose.py:336-339` composes plan-block markers inline instead of calling `issue_wire.compose_named_block`.
- `python/larch/learn_from_bugs.py:57` uses a laxer case-insensitive marker regex instead of the shared marker recognizer.
- `python/larch/design_router.py:128` hand-checks marker literals instead of delegating to `issue_wire`.

## Goal

Repoint each bypass site to `issue_wire` for marker composition and recognition, so `issue_wire` is the single marker owner end to end. After this, a grep for private marker composition or literal marker checks outside `issue_wire` should be empty for these consumers.

## Non-goals

- Do not change `issue_wire`'s marker format or its ownership contract.
- Do not alter plan heading or trailer grammar; that ownership move is #7000.

## Size

~3 sites, small per-site edits plus regression tests pinning marker composition through `issue_wire`.

## Related

- Related to: #7000 (plan_grammar.py single plan-format owner). Independent work; tracked separately because #7000 stays focused on the grammar move.
