## Goal
Implement issue #7481: [IMPLEMENTING] contract-unification [CLEANUP] Delete the unreachable pre-Step-5c sanitizer surface.

## Implementation Plan
#### Problem

The `/design` skill explicitly forbids `design-step3b-sanitize.sh` before Step 5c because Step 5c owns candidate promotion, rejection, skip artifacts, and completion markers. The remaining positive surface is a registered CLI verb, a Python shell delegator, the 171-line script, its reference file, and script-specific structure pins. No live skill path calls it.

#### Goal

Delete the wrapper, reference file, CLI registration, delegator, and obsolete script-specific pins. Retain a general structural rule that no pre-Step-5c path performs authoritative sanitization or writes Step 5c artifacts. Record the retired script in the Python migration manifest if required. Do not change Step 5c sanitization behavior.

#### Required implementation

- Delete `skills/design/scripts/design-step3b-sanitize.sh` and `skills/design/scripts/design-step3b-sanitize.md`.
- Remove `("plan-review", "step3b-sanitize")` from `python/larch/cli.py` and remove `step3b_sanitize_main` plus its `_delegate_step3_script` call from `review/plan_review.py`.
- Remove launcher/session mappings, Make targets, manifest rows, and direct harness coverage that exist only for this wrapper. Add the retired path to `scripts/migrated-scripts.tsv` or the current no-shim retirement authority when required by `docs/python-migration.md`.
- Replace script-specific structure pins with behavior pins against the live Step 5b.5 and Step 5c surfaces: no pre-Step-5c promotion, rejection, candidate move/delete, `.completed/step-5b.5`, `architecture-diagram.md`, or `architecture-diagram.skipped` write.
- Update prose that names the dead command as a callable option. Historical logs and calibration fixtures may retain literal history.
- Search tracked nonhistorical surfaces for `step3b-sanitize` after deletion. Any surviving positive runtime reference is a failure.

#### Verification

Run design structure, CLI registry, module-manifest, retired-script, residual-Bash, Step 5c diagram, and relevant lint checks. A fresh process invoking the removed CLI verb must fail as unknown rather than silently succeeding.

#### Size and acceptance

Expected change: 250-500 lines with a net reduction. Tracked runtime and skill surfaces must contain no callable sanitizer wrapper. Historical logs and calibration fixtures are not migration targets. Design structure and Step 5c diagram tests must pass.

## Test plan
(no test plan section in plan-file)
