## Goal
Implement issue #5371: [IMPLEMENTING] [Bug] /implement escalation: Step 6 relevant-checks omit test-references-headers for changed reference docs, so a missing required header reached CI (step5:coder-main-agent-required).

## Implementation Plan
<!-- larch-stall:signature=d99a0d5d971f9371b31b0a32b942ad1019452d1d6a14e150c4829b4328a35e0b -->

## Report metadata
- **Report kind**: `escalation-success`
- **Failure class**: ``
- **Step**: `unknown`
- **Bail reason**: `redacted`
- **Run ID**: `FE13BA9E-D9B9-44E7-98DE-4E86EC4AB739`
- **Branch**: `unknown`
- **PR URL**: `https://github.com/character-ai/larch/pull/5370`

## Root-cause finding

verdict=larch-defect
confidence=medium
summary=Step 6 relevant-checks omit test-references-headers for changed reference docs, so a missing required header reached CI

The /implement run merged successfully but required Main Claude on two script-loop escalations recorded in stall-recovery-escalation-ledger.tsv.

1. site=step5 trigger=coder-main-agent-required (observation): the round-2 review-fix coders (Cursor then Codex) were exhausted, so Main Claude applied the accepted findings. This is the designed coder-to-main-agent fallback (environment: external implementers unavailable), not a defect.

2. site=ship-pr trigger=step8-shippr (observation): the first CI run failed in the test-harnesses job because test-references-headers.sh found the new reference skills/design/references/dialectic-clarifier.md lacked the required anchored When-to-load header from the Consumer/Contract/When-to-load triplet. The ship-pr CI auto-fixer classified it first-fixer-non-health and handed off; Main Claude added the header and re-shipped, after which CI passed and the PR merged.

Root cause (inference): the Step 6 relevant-checks make-target selection did not include test-references-headers even though a skills/*/references/*.md file was created and changed in the diff. The header omission was therefore invisible to local relevant-checks and surfaced only in CI, forcing a Main Claude CI-fix round-trip plus a full re-ship.

Suggested larch improvement: in the relevant-checks selection (python/checks.py), map changed or added skills/*/references/*.md paths to the test-references-headers harness so the Consumer/Contract/When-to-load triplet is enforced locally before push, matching how other changed-file harnesses are selected.



## Attempts

| Attempt | Class | Resume hint | Outcome | UTC |
|---|---|---|---|---|
| none | n/a | n/a | n/a | n/a |

## Escalation ledger

utc=2026-06-24T23:16:32.133746+00:00	site=step5	trigger=coder-main-agent-required	step=5	phase=review	dispatcher=run-step5-review	exit_code=0	failure_detail_log=round-2/review-and-fix.stderr
utc=2026-06-25T02:40:44.356819+00:00	site=ship-pr	trigger=step8-shippr	step=8	phase=ci-initial	dispatcher=ship-pr	exit_code=3	failure_detail_log=

## Test plan
(no test plan section in plan-file)
