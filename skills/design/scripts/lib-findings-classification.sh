# shellcheck shell=bash

# shellcheck disable=SC2317
if [[ "${LARCH_FINDINGS_CLASSIFICATION_LIB_LOADED:-}" == "1" ]]; then
    return 0 2>/dev/null || exit 0
fi
LARCH_FINDINGS_CLASSIFICATION_LIB_LOADED=1

emit_findings_classification_header() {
    printf '%s\n' 'finding_id	finding_reviewers	voting_result	v1_vote	v1_correctness	v1_severity	v1_quality	v1_uncertain	v1_tool	v2_vote	v2_correctness	v2_severity	v2_quality	v2_uncertain	v2_tool	v3_vote	v3_correctness	v3_severity	v3_quality	v3_uncertain	v3_tool'
}
