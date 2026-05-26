## Architecture Diagram

```mermaid
flowchart TD
    Entry["run_implement_loop entry"] --> ValidateInt["validate STARTING_ROUND numeric"]
    ValidateInt --> ComputeEntry["compute entry_prior_deg<br/>entry_effective_cap = base_cap + entry_prior_deg"]
    ComputeEntry --> ValidateDeg{"entry_prior_deg numeric?"}
    ValidateDeg -->|no| ExitEnvErr["envelope: stall true env-write-failed<br/>exit 2"]
    ValidateDeg -->|yes| HoistCheck{"STARTING_ROUND > entry_effective_cap<br/>AND prior-artifact exists?"}
    HoistCheck -->|both true| Flush["flush_review_batches"]
    Flush --> HoistEmit["envelope: mav-resume-past-cap false<br/>STALL_TRACKING=false<br/>exit 0"]
    HoistCheck -->|either false| ArtifactProbe["step5_probe_prior_round_env<br/>try -f, sync best-effort, retry once"]
    ArtifactProbe --> ProbeResult{"found?"}
    ProbeResult -->|yes| Loop["enter while-loop<br/>existing per-iteration logic"]
    ProbeResult -->|no| Diag["larch_err diagnostic<br/>6 keys IMPLEMENT_TMPDIR..entry_effective_cap"]
    Diag --> StallNonTrack["envelope: stall false starting-round-invalid<br/>STALL_TRACKING=false<br/>exit 2"]
    Loop --> InLoop["round body, in-loop cap check<br/>existing mav-resume-past-cap path"]
    StallNonTrack -. orchestrator parses STALL_TRACKING from envelope .-> SKILL["SKILL.md Step 5 stall bullet<br/>RETAINS envelope STALL_TRACKING<br/>no [STALLED] rename"]
    HoistEmit -. .-> SKILL
```
