### [Bug] /design terminal: failed-publish-tail at design-publish via publish-tail-failed (unrecoverable at publish)
<!-- larch-stall:signature=bfcaeebdb41df9fea121665d4f9b31a8e4ac6281353ee5aea7de956834df3a31 -->

## Report metadata

- **Report kind**: `terminal-failure`
- **Failure class**: `unrecoverable`
- **Step**: `publish`
- **Bail reason**: `publish-tail-failed`
- **Run ID**: `unknown`
- **Branch**: `unknown`
- **PR URL**: `unknown`


## Root-cause finding

verdict=larch-defect
confidence=medium
summary=failed-publish-tail at design-publish via publish-tail-failed

The reporter used bounded /design state tokens and local ledger evidence only.


## Attempts

| Attempt | Class | Resume hint | Outcome | UTC |
|---|---|---|---|---|
| none | n/a | n/a | n/a | n/a |

## Validated failure-detail log

design-publish.sh failed (exit 5)

