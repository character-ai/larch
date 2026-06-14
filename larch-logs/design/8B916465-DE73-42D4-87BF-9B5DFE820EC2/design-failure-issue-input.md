### [Bug] /design terminal: failed-publish at design-publish via failed (unrecoverable at publish)
<!-- larch-stall:signature=39cd0c35fd223623cac2fe4c172729bc70717c9a282c4e0dec657ca283f43485 -->

## Report metadata

- **Report kind**: `terminal-failure`
- **Failure class**: `unrecoverable`
- **Step**: `publish`
- **Bail reason**: `publish-failed`
- **Run ID**: `unknown`
- **Branch**: `unknown`
- **PR URL**: `unknown`


## Root-cause finding

verdict=environment
confidence=medium
summary=failed-publish at design-publish via failed

The reporter used bounded /design state tokens and local ledger evidence only.


## Attempts

| Attempt | Class | Resume hint | Outcome | UTC |
|---|---|---|---|---|
| none | n/a | n/a | n/a | n/a |

## Validated failure-detail log

design-log-publish: unexpected file under plan-review (see python/plan_review.py): round-1/revise/cursor-output.txt.token-record

