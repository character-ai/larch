# /implement Step 16–17 final-summary sentinel contract

**Consumer**: `/implement` Step 17 and Step 18 orchestrator; contributors extending the final-summary emission path.

**Contract**: Forbidden-forms list for NEVER #17 (free-form recap prohibition) and the `.step17-printed` / `.step17-emitted` sentinel ownership contract for the marker emission path.

**When to load**: When extending or debugging the Step 17 marker extraction or Step 18 re-emission. The operational directives live in the Step 17 and Step 18 SKILL.md prose; this file is supporting context.

## Forbidden forms (NEVER #17)

— including but not limited to a "Run complete." / "Implementation merged." prose line, a bullet list summarizing PR / Version / Changes / Code review / CI / Tracking issue, a parenthetical cost paraphrase (for example `~$10.46`, `~$X total`), or any natural-language replacement for the structured `## /implement run ... — <outcome>` block rendered into `summary-final.md` by `python/cli.py implement step-16-17` through `python/cli.py implement step-17 --no-print-stdout` and marker extraction.

## Sentinel ownership

`python/cli.py implement step-16-17` owns `.step17-printed` after marker printing; the orchestrator owns `.step17-emitted` only after top-chat emission.

The missing-marker warning is printed only when `EMIT_BODY=true` and `WFR_RC=0`.

The wrapper writes `.step17-emitted` before Step 18b when `--step17-emitted true`, and touches it before teardown when emitting markers.

Step 18 primary path uses wrapper marker stdout captured by the Bash tool; there is no Read fallback.

## Permitted post-summary orchestrator text

The only orchestrator-text addition permitted after the Bash summary is the verbatim full-body emission of the extracted marker body defined in Step 17 or the extracted marker body from captured `step-18.sh --phase finalize` stdout.

The authoritative always-loaded copy lives in the Step 17 SKILL.md body because `scripts/test-render-cost-line-callsites.sh` requires that sentence in `skills/implement/SKILL.md`.
