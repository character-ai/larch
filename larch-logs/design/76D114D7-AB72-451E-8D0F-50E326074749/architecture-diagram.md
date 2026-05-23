## Architecture Diagram

```mermaid
flowchart TD
    subgraph review_core[review-core.sh]
        RC1[invoke aggregate-findings.sh]
        RC2{REASON == validation-exhausted?}
        RC3[short-circuit: full panel-failed envelope, exit 2]
        RC4[dispatch voters, tally]
    end

    subgraph aggregate_findings[aggregate-findings.sh]
        AF1[INPUT_COUNT and disabled checks]
        AF2[outer phase loop: cursor, codex, claude]
        AF3[_attempt_aggregation_phase helper]
        AF4{phase succeeded?}
        AF5[emit_result with PHASES_ATTEMPTED and REASON=ok]
        AF6[next phase or exhaust]
        AF7[emit_result with REASON=validation-exhausted, single consolidated warning]
    end

    subgraph attempt_phase[_attempt_aggregation_phase]
        AP1[build single-slot NDJSON, presence flags scoped per call]
        AP2[dispatch-with-waterfall.sh -- unchanged]
        AP3[inspect ALL_OUTPUT_TOOLS for internal fallback mismatch]
        AP4[_attempt_attestation_repair: substring guard before synthesis]
        AP5[aggregate-validate.py main: substring guard]
        AP6{validator says preamble_finding_substring?}
        AP7[return outer-loop progression signal]
        AP8[return non-progression failure, keep REASON=validation-failed]
    end

    subgraph downstream[Downstream chain]
        D1[review-and-fix.sh: aggregator-validation-exhausted case]
        D2[review-implement-step5-loop.sh: STALL_REASON=aggregator-validation-exhausted]
        D3[/implement Step 5: stall in Tool Failures]
    end

    RC1 --> AF1
    AF1 --> AF2
    AF2 --> AF3
    AF3 --> AP1
    AP1 --> AP2
    AP2 --> AP3
    AP3 --> AP4
    AP4 --> AP5
    AP5 --> AP6
    AP6 -->|yes| AP7
    AP6 -->|other failure| AP8
    AP7 --> AF4
    AP8 --> AF4
    AF4 -->|ok| AF5
    AF4 -->|fail| AF6
    AF6 --> AF2
    AF6 -->|exhausted| AF7
    AF5 --> RC2
    AF7 --> RC2
    AF1 -.->|REASON=disabled or insufficient-input| RC2
    RC2 -->|yes| RC3
    RC2 -->|no| RC4
    RC3 --> D1
    D1 --> D2
    D2 --> D3
```
