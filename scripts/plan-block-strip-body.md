# plan-block-strip-body.sh

Removes one embedded `<!-- larch:plan:start -->` … `<!-- larch:plan:end -->` block from issue/body text while preserving the exterior body. It is used by `/design` plan review before materializing the staged scope anchor.

## Contract

- Reads stdin or `--file <path>` and writes stdout or `--output <path>`.
- Reuses the plan marker regexes from `plan-block-read.sh`.
- Zero markers pass through unchanged.
- Malformed marker sets fail closed with `MALFORMED=<token>` and exit 1.

## Harness

`make test-plan-block-strip-body` runs `scripts/test-plan-block-strip-body.sh`.
