### [Bug] /design terminal: failed-publish-tail at design-publish via publish-tail-failed (unrecoverable at publish)
<!-- larch-stall:signature=29d0be5e6eb019d66f2fe3abd79abcaf7ac1853c54e96b0f27078ac5c67ff046 -->
## Report metadata
- **Report kind**: `terminal-failure`
- **Failure class**: `unrecoverable`
- **Step**: `publish`
- **Bail reason**: `publish-tail-failed`
- **Run ID**: `A2AD61B7-CE33-4122-813F-900C4C83EC79`
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

