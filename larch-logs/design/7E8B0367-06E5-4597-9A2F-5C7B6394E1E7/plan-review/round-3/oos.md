### OOS_1:
- **Description**: Top-level DRIFT shell defaults not named separately from _postplan_build_kvs. Scenario: Plan says extend _postplan_build_kvs defaults but not mirror HARD_TRIGGER_FIRED=false initialization at lines 126-132; if a parse arm is missed, set -u can trip before _postplan_finish_merged_plan_size
- **Reviewer**: Cursor-dyn-kv-chain-completeness
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/scripts/design-postplan-emit.sh:116-132
- **Phase**: design


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0 Result=exonerated

